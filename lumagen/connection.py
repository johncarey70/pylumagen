"""Handles serial and IP communication using asyncio.

This module provides common functionality for serial and IP connections
with shared methods for opening, closing, sending, and receiving data.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Awaitable, Callable
import contextlib
from dataclasses import dataclass
from typing import Any

import serial_asyncio_fast as serial_asyncio

from .constants import (
    ASCII_COMMAND_LIST,
    CMD_START,
    CMD_TERMINATOR,
    ConnectionStatus,
    EventType,
)
from .dispatcher import Dispatcher
from .messages import Response
from .utils import (
    BufferManager,
    LoggingMixin,
    TaskManager,
    custom_log_pprint,
    process_command_or_keypress,
)

INITIAL_READ_SIZE = 4
DEFAULT_READ_BYTES = 8
READ_TIMEOUT = 4

EventCallbackType = (
    Callable[[str, str | None], None] | Callable[[str, str | None], Awaitable[None]]
)


@dataclass
class SerialConfig:
    """Configuration for serial connections."""

    max_buffer_size: int = 2048
    max_incomplete_duration: int = 10
    timeout: float = 5.0


class ConnectionState(LoggingMixin):
    """Encapsulates the state of the connection for serial and IP communication.

    Provides utility methods for managing the connection state, including
    buffering data, managing command queues, and tracking responses.
    """

    def __init__(self) -> None:
        """Initialize a new ConnectionState instance.

        Attributes:
            buffer (deque[str]): Stores incoming data.
            command_queue (deque): Holds commands to be sent.
            command_response_map (dict[str, str]): Maps commands to their expected responses.
            last_command_byte (str): Stores the last byte of the last command sent.
            sending_command (bool): Tracks whether a command is currently being sent.
            current_command (Optional[str]): Stores the current command being processed.

        """
        super().__init__()
        self.buffer: deque[str] = deque()
        self.command_queue = deque()
        self.command_response_map: dict[str, str] = {}
        self.last_command_byte: str = ""
        self.sending_command: bool = False
        self.current_command: str | None = None

    def append_to_buffer(self, data: str) -> None:
        """Append data to the buffer.

        Args:
            data (str): The data to append to the buffer.

        """
        self.buffer.extend(data)

    def clear_buffer(self) -> None:
        """Clear the communication buffer."""
        self.buffer.clear()

    def has_pending_commands(self) -> bool:
        """Check if there are commands in the queue.

        Returns:
            bool: True if the command queue is not empty, False otherwise.

        """
        if not self.command_queue:
            self.current_command = None
        return bool(self.command_queue)

    def pop_next_command(self) -> str | None:
        """Retrieve the next command from the queue and update the current command."""
        if self.command_queue:
            self.current_command = self.command_queue.popleft()
            self.log.debug("Commands remaining in queue: %d", len(self.command_queue))
            return self.current_command
        self.log.debug("Queue is empty after pop attempt")
        self.current_command = None
        return None


class BaseHandler(LoggingMixin):
    """Base handler for managing shared connection logic."""

    def __init__(self, dispatcher: Dispatcher | None = None) -> None:
        """Initialize with common configuration and event callback."""
        super().__init__()
        self._dispatcher: Dispatcher = dispatcher
        self._task_manager = TaskManager()
        self.connection_state = ConnectionState()
        self._state_lock = asyncio.Lock()
        self.reader: asyncio.StreamReader = None
        self.writer: asyncio.StreamWriter = None

    async def process_stream(self):
        """Process incoming data stream."""
        buffer_manager = BufferManager(terminator="\n", ignored_prefixes=("#ZT", "#ZY"))

        async def process_message() -> None:
            """Process a single message from the buffer."""
            message = buffer_manager.extract_message()
            if message:
                self.log.debug("Processing Message: %s", message)
                try:
                    response = Response.factory(message)
                    await self._dispatcher.invoke_event(
                        EventType.DATA_RECEIVED,
                        response=response,
                        message=response.name,
                    )
                except ValueError as ex:
                    self.log.error(ex)
            self.process_next_command()

        async def process_buffer() -> bool:
            """Process the buffer and return whether to continue the loop."""
            if buffer_manager.is_empty():
                buffer_manager.clear()
                return False

            self.log.debug("Buffer updated: %s", buffer_manager.buffer.encode())

            # Filter and adjust the buffer
            buffer_manager.adjust_buffer(["power", "#ZQS1", "!", "#"])

            if buffer_manager.starts_with(buffer_manager.ignored_prefixes):
                buffer_manager.clear()
                await process_message()
                return False

            if (
                buffer_manager.starts_with(("power", "#", "!"))
                and buffer_manager.ends_with_terminator()
            ):
                await process_message()
                return False

            if buffer_manager.ends_with_terminator():
                buffer_manager.clear()
                return False

            key, value, is_keypress = process_command_or_keypress(
                buffer_manager.buffer, ASCII_COMMAND_LIST
            )
            if key:
                log_message = (
                    f"Received Keypress Command: {value}"
                    if is_keypress
                    else f"Received Remote Command: {value}"
                )
                self.log.debug(log_message)
                buffer_manager.clear()

            await process_message()
            return True

        while True:
            await asyncio.sleep(0)  # allow cancel task
            try:
                if not await self._read_single_byte(buffer_manager):
                    continue

                data = await self._read_additional_data()
                if data:
                    buffer_manager.append(data)

                if not await process_buffer():
                    continue

            except asyncio.CancelledError:
                self.log.debug("Task process_message cancelled.")
                raise

    async def _read_single_byte(self, buffer_manager: BufferManager):
        """Read a single byte and append it to the buffer."""
        single_byte = await self.reader.read(1)
        if not single_byte:
            self.log.warning("Stream ended unexpectedly")
            await asyncio.sleep(0.1)
            return False

        buffer_manager.append(single_byte.decode("utf-8"))
        return True

    async def _read_additional_data(self) -> str:
        """Read additional data from the stream with timeout."""
        for read_func in [
            lambda: self.reader.readuntil(separator=b"\n"),
            lambda: self.reader.read(1024),
        ]:
            try:
                data: bytes = await asyncio.wait_for(read_func(), timeout=0.2)
                return data.decode("utf-8") if data else ""
            except asyncio.exceptions.TimeoutError:
                continue
        return ""

    async def send(self, data: bytes):
        """Abstract method for sending data over the connection."""
        raise NotImplementedError("send method must be implemented by subclasses")

    async def queue_command(self, command: str | list[str]):
        """Queue a command or multiple commands to be sent over an active connection."""

        if isinstance(command, str):
            command = [command]  # Convert single command to a list

        if isinstance(command, list):
            valid_commands = [
                cmd.strip() for cmd in command if isinstance(cmd, str) and cmd.strip()
            ]
            if not valid_commands:
                self.log.error("No valid commands to queue.")
                return

            # Append new commands to the queue
            self.connection_state.command_queue.extend(valid_commands)
            self.log.debug(
                "Queued %d commands. Commands remaining: %d",
                len(valid_commands),
                len(self.connection_state.command_queue),
            )

        else:
            self.log.error("Invalid command type: %s", type(command).__name__)
            return

        self.process_next_command()

    def process_next_command(self):
        """Trigger processing of the next command in the queue."""
        if not self._task_manager.get_task("process_next_command"):
            self._task_manager.add_task(
                self._process_next_command(),
                "process_next_command",
            )

    async def _process_next_command(self, max_iterations: int | None = None):
        """Process the next command in the queue if no command is currently being sent.

        Args:
            max_iterations (int | None): Maximum iterations for processing commands,
                                        primarily for testing or debugging. If None,
                                        processes until conditions are met.

        """
        iteration_count = 0

        while True:
            if max_iterations and iteration_count >= max_iterations:
                break
            iteration_count += 1

            async with self._state_lock:
                if self._should_exit_processing():
                    self.log.debug("No more commands in the queue. Exiting loop")
                    break

                command: str = self.connection_state.pop_next_command()
                if not command:
                    continue

                data: bytes = CMD_START + command.encode("utf-8") + CMD_TERMINATOR

            if not await self.send(data):
                break

    def _should_exit_processing(self) -> bool:
        """Check conditions to exit the processing loop."""
        if self.connection_state.sending_command:
            return True

        if not self.connection_state.has_pending_commands():
            return True

        return False

    async def close(self):
        """Clean up tasks and close the connection."""
        with contextlib.suppress(asyncio.CancelledError):
            await self._task_manager.cancel_all_tasks()

        await self._task_manager.wait_for_all_tasks()
        self.log.info("All tasks cancelled and connection closed.")


class SerialHandler(BaseHandler, asyncio.Protocol):
    """Handles serial communication using asyncio."""

    def __init__(
        self,
        dispatcher: Dispatcher | None = None,
    ) -> None:
        """Initialize."""
        super().__init__(dispatcher)

        self.transport: asyncio.Transport | None = None
        self.config = SerialConfig()
        self._state_lock = asyncio.Lock()

    def connection_made(self, transport: serial_asyncio.SerialTransport) -> None:
        """Made Connection."""
        self.transport = transport
        self.reader = asyncio.StreamReader()
        self.log.info("Serial connection established")

        transport.serial.reset_input_buffer()
        transport.serial.reset_output_buffer()

        self._task_manager.add_task(
            self._dispatcher.invoke_event(
                EventType.CONNECTION_STATE,
                state=ConnectionStatus.CONNECTED,
                message=f"Connected to {transport.serial.port}",
            ),
            "invoke_event",
        )

        self._task_manager.add_task(self.process_stream(), "process_stream")

    async def connection_lost(self, exc) -> None:
        """Lost Connection."""
        self.transport = None
        self.log.warning("Serial connection lost")

        await self._dispatcher.invoke_event(
            EventType.CONNECTION_STATE,
            state=ConnectionStatus.DISCONNECTED,
            message=str(exc),
        )

    def data_received(self, data) -> None:
        """Call automatically when data is received."""

        self.reader.feed_data(data)

    @staticmethod
    def extract_serial_transport_details(
        transport: serial_asyncio.SerialTransport,
    ) -> dict[str, Any] | dict[str, str] | None:
        """Extract details from the SerialTransport object and format as a dictionary.

        Returns:
            - A dictionary of extracted transport details if available.
            - {"error": "Could not extract transport details"} if an AttributeError occurs.
            - None if all attributes are None.

        """
        try:
            serial = transport.serial
            if serial:
                details = {
                    "port": serial.port,
                    "baudrate": serial.baudrate,
                    "bytesize": serial.bytesize,
                    "parity": serial.parity,
                    "stopbits": serial.stopbits,
                    "timeout": serial.timeout,
                    "xonxoff": serial.xonxoff,
                    "rtscts": serial.rtscts,
                    "dsrdtr": serial.dsrdtr,
                }
                # Return None if all values are None
                return (
                    None
                    if all(value is None for value in details.values())
                    else details
                )
        except AttributeError:
            return {"error": "Could not extract transport details"}

    @classmethod
    async def open_connection(
        cls, port: str, baudrate: int, dispatcher=None
    ) -> SerialHandler:
        """Open an asynchronous serial connection."""

        # Create an instance temporarily to access the instance-level logger
        temp_instance = cls(dispatcher)

        loop = asyncio.get_running_loop()

        result = await serial_asyncio.create_serial_connection(
            loop, lambda: cls(dispatcher), port, baudrate
        )

        if isinstance(result, tuple) and len(result) == 2:
            transport, protocol = result
            transport_details = cls.extract_serial_transport_details(transport)

            temp_instance.log.debug("Transport Details:")
            custom_log_pprint(transport_details, temp_instance.log.debug)

            return protocol

        raise TypeError(
            "Expected (transport, protocol) tuple from create_serial_connection, "
            f"but got {type(result).__name__}: {result}"
        )

    async def send(self, data: bytes) -> None:
        """Send data over the serial connection."""
        if not self.transport:
            self.log.error("Cannot send data: No active connection.")
            return
        self.transport.write(data)
        self.log.debug("Command sent: %s", data)


class IPHandler(BaseHandler):
    """Handles IP (TCP) communication."""

    async def open_connection(self, host: str, port: int) -> IPHandler:
        """Open an asynchronous ip connection."""
        self.reader, self.writer = await asyncio.open_connection(host, port)
        self.log.info("IP connection established to %s:%d", host, port)

        self._task_manager.add_task(
            self._dispatcher.invoke_event(
                EventType.CONNECTION_STATE,
                state=ConnectionStatus.CONNECTED,
                message=f"Connected to {host}:{port}",
            ),
            "invoke_event",
        )

        self._task_manager.add_task(self.process_stream(), "process_stream")

    async def send(self, data: bytes) -> None:
        """Send data over the IP connection."""
        if self.writer:
            self.writer.write(data)
            await self.writer.drain()
            self.log.debug("Command sent: %s", data)
        else:
            self.log.error("No IP connection available to send data")

    async def close(self) -> None:
        """Close."""
        await super().close()
        if self.writer:
            self.writer.close()
            try:
                await asyncio.wait_for(self.writer.wait_closed(), timeout=5.0)
            except asyncio.exceptions.TimeoutError:
                self.log.warning("Timeout while waiting for writer to close.")
