"""Module: DeviceManager.

Manage the high-level operations of the device, including connection management,
state tracking, and command execution.

Usage Example:
--------------
from device_manager import DeviceManager

device = DeviceManager(connection_type="ip", reconnect=True)
await device.open()
await device.executor.power_on()
await device.close()

Methods:
-------
- open(): Establish a connection to the device.
- close(): Close the connection and clean up resources.
- send_command(command): Send a command to the device via the CommandExecutor.
- get_status(): Get the current status of the device.

"""

import asyncio
from collections.abc import Callable, Coroutine
import contextlib
from datetime import UTC, datetime
import errno
from functools import partial
import os
from typing import Any

from propcache import cached_property
from pydantic import BaseModel

from .classes import DeviceContext, DeviceInfo
from .command_executor import CommandExecutor
from .connection import IPHandler, SerialHandler
from .constants import (
    CMD_DEVICE_START,
    DEFAULT_HEALTH_CHECK_INTERVAL,
    DEFAULT_IP_PORT,
    STATUS_ALIVE,
    STATUS_ID,
    STATUS_POWER,
    ConnectionStatus,
    DeviceStatus,
    EventType,
)
from .dispatcher import Dispatcher
from .messages import (
    AutoAspect,
    FullInfoV1,
    FullInfoV2,
    FullInfoV3,
    FullInfoV4,
    GameMode,
    InputBasicInfo,
    InputVideo,
    LabelQuery,
    OutputBasicInfo,
    OutputColorFormat,
    OutputMode,
    PowerState,
    Response,
    StatusAlive,
    StatusID,
)
from .models import BaseDeviceId, BaseFullInfo, BaseOperationalState
from .utils import LoggingMixin, custom_log_pprint


class DeviceManager(LoggingMixin):
    """Manage the device's connection, state, and command execution."""

    def __init__(self, connection_type: str, reconnect: bool = True) -> None:
        """Initialize the Device instance.

        Args:
            connection_type (str): Type of connection ("serial" or "ip").
            reconnect (bool): Whether to enable automatic reconnection on disconnection.

        """
        super().__init__()
        self.connection_type: str = connection_type.lower()

        self.context = DeviceContext(reconnect)
        self.context.system_state.set_update_callback(self._device_info_callback)

        self.context.connection.dispatcher.register_listener(
            EventType.CONNECTION_STATE, self._async_event_handler
        )
        self.context.connection.dispatcher.register_listener(
            EventType.DATA_RECEIVED, self._async_event_handler
        )

        self.cms_list: list[str] = []
        self.labels: dict[str, str] = {}
        self.source_list: list[str] = []
        self.style_list: list[str] = []

        self.context.connection.task_manager.add_task(
            self._run_once_at_startup(), name="run_once_at_startup"
        )

    @cached_property
    def dispatcher(self) -> Dispatcher:
        """Dispatcher."""
        return self.context.connection.dispatcher

    @cached_property
    def executor(self) -> CommandExecutor:
        """Expose the CommandExecutor instance."""
        if self.context.connection.executor is None:
            raise RuntimeError(
                "CommandExecutor is not initialized. Ensure `open()` is called first."
            )
        return self.context.connection.executor

    @property
    def device_id(self) -> BaseDeviceId:
        """Shortcut to access device_id."""
        return self.context.system_state.device_id

    @property
    def device_info(self) -> DeviceInfo:
        """Get the DeviceInfo class."""
        return self.context.device_state.info

    @property
    def device_status(self) -> DeviceStatus:
        """Get the current state of the device (Active/Standby)."""
        return self.context.system_state.operational_state.device_status

    @property
    def is_alive(self) -> bool:
        """Check if the device is alive and responding."""
        return self.context.system_state.operational_state.is_alive

    @property
    def is_connected(self) -> bool:
        """Check if there is an active connection."""
        return self.context.connection.config.status == ConnectionStatus.CONNECTED

    async def open(self, **kwargs) -> None:
        """Open a connection based on the connection type.

        For serial:
            kwargs: port (str), baudrate (int)
        For IP:
            kwargs: host (str), port (int)
        """
        try:
            self.context.connection.config.connection_params = kwargs.copy()

            self.context.connection.handler = await self._initialize_handler(**kwargs)
            self.context.connection.executor = CommandExecutor(
                self.context.connection.handler, self
            )
            self.log.info("Connection opened successfully")

        except ValueError as e:
            self.log.error("Failed to open connection: %s", e)
            raise

    async def close(self) -> None:
        """Close the connection and cancel all managed tasks safely."""

        if self.context.connection.closing:
            self.log_warning("Close operation already in progress.")
            return

        self.context.connection.closing = True
        self.log.info("Closing device connection...")

        if self.context.connection.handler:
            try:
                await self.context.connection.handler.close()
            except (ConnectionError, asyncio.exceptions.TimeoutError, OSError) as e:
                self.log_error("Error while closing connection handler: %s", e)
            finally:
                self.context.connection.handler = None

        with contextlib.suppress(asyncio.CancelledError):
            await self.context.connection.task_manager.cancel_all_tasks()

        self.context.connection.config.status = ConnectionStatus.DISCONNECTED
        self.context.system_state.reset_state()

    async def send_command(self, command: str | list[str]) -> None:
        """Send a command to the device via the CommandExecutor."""
        return await self.context.connection.executor.send_command(command)

    def enable_reconnect(self, enable: bool) -> None:
        """Enable or disable automatic reconnection.

        Args:
            enable (bool): True to enable auto-reconnect, False to disable.

        """
        if not isinstance(enable, bool):
            raise TypeError("enable must be a boolean (True or False)")

        if self.context.connection.config.reconnect_enabled == enable:
            self.log.debug(
                "Auto-reconnect is already %s.", "enabled" if enable else "disabled"
            )
            return

        self.context.connection.config.reconnect_enabled = enable
        self.log.info("Auto-reconnect is now %s.", "enabled" if enable else "disabled")

    async def _initialize_handler(self, **kwargs) -> SerialHandler | IPHandler:
        """Initialize the appropriate connection handler."""
        handlers = {
            "serial": self._init_serial_handler,
            "ip": self._init_ip_handler,
        }

        if self.connection_type in handlers:
            return await handlers[self.connection_type](**kwargs)

        raise ValueError(f"Unsupported connection type: {self.connection_type}")

    async def _init_serial_handler(self, port: str, baudrate: int) -> SerialHandler:
        """Initialize a serial connection with the provided port and baudrate."""

        if not port:
            raise ValueError("Port must be provided for serial connection")

        if not isinstance(baudrate, int) or baudrate <= 0:
            raise ValueError("Baudrate must be a positive integer")

        self.log.info("Opening serial connection to %s at %d baud", port, baudrate)

        return await SerialHandler.open_connection(
            port, baudrate, self.context.connection.dispatcher
        )

    async def _init_ip_handler(self, host: str, port: int | None = None) -> IPHandler:
        """Initialize an IP connection with a default port if none is provided."""

        if not host:
            raise ValueError("Host must be provided for IP connection")

        if port is None:
            port = DEFAULT_IP_PORT

        self.log.info("Opening IP connection to %s:%d", host, port)

        ip_handler = IPHandler(self.context.connection.dispatcher)
        await ip_handler.open_connection(host, port)

        return ip_handler

    async def _run_once_at_startup(self) -> None:
        """Run get_all once at startup if active."""

        while self.is_alive is False or self.device_status is None:
            await asyncio.sleep(0.5)

        if self.device_status == DeviceStatus.ACTIVE:
            await self.executor.get_all()

    async def _health_check(
        self, interval: int = DEFAULT_HEALTH_CHECK_INTERVAL
    ) -> None:
        """Periodically check if the device is alive.

        This method runs a health check at regular intervals, defined by
        `DEFAULT_HEALTH_CHECK_INTERVAL`. Debug logs are temporarily
        suppressed during the check to reduce noise.
        """

        while self.is_connected and self.is_alive:
            await asyncio.sleep(interval)

            now = datetime.now(UTC)

            if self.context.device_state.last_data_received:
                elapsed_time: float = (
                    now - self.context.device_state.last_data_received
                ).total_seconds()

                if elapsed_time < interval:
                    continue

            LoggingMixin.disable_debug_logging()
            try:
                if not await self._check_device_alive():
                    await self._handle_disconnection()
                    break
            finally:
                await asyncio.sleep(0.1)
                LoggingMixin.enable_debug_logging()

    async def _check_device_alive(self, timeout: float = 5.0) -> bool:
        """Perform a device alive check."""
        if not self.is_connected:
            self.log.error("No active connection to perform alive check")
            return False

        self.context.device_state.alive_event.clear()
        try:
            await self.send_command(CMD_DEVICE_START + STATUS_ALIVE)

            await asyncio.wait_for(
                self.context.device_state.alive_event.wait(), timeout=timeout
            )
            self.log.debug("Device responded to alive check.")
        except asyncio.exceptions.TimeoutError:
            self.log.error("Alive check timed out - device may be disconnected")
            return False
        except ConnectionError as e:
            self.log.error("Failed to send alive message: %s", e)
            await self._handle_disconnection()
            return False

        if self.device_id.model_name is None:
            await self.send_command(
                [CMD_DEVICE_START + STATUS_POWER, CMD_DEVICE_START + STATUS_ID]
            )
            self.context.connection.task_manager.add_task(
                self._health_check(), name="periodic_alive_check"
            )
        return self.is_alive

    async def _handle_disconnection(self) -> None:
        """Handle network disconnection, cleanup tasks, and trigger reconnection if enabled."""

        if not self.is_connected:
            self.log_info("Device is already disconnected. Skipping redundant cleanup.")
            return

        self.log_warning("Handling disconnection...")

        if self.context.connection.handler:
            self.log_info("Closing connection handler...")
            try:
                await self.context.connection.handler.close()
            except (ConnectionError, asyncio.exceptions.TimeoutError, OSError) as e:
                self.log_error("Error while closing handler: %s", e)
            finally:
                self.context.connection.handler = None

        await self.context.connection.dispatcher.invoke_event(
            EventType.CONNECTION_STATE,
            state=ConnectionStatus.DISCONNECTED,
            message="Connection lost",
        )

    async def _retry_alive_check(
        self, interval: int = DEFAULT_HEALTH_CHECK_INTERVAL
    ) -> None:
        """Retry the alive check every 30 seconds if it initially fails."""
        while not self.is_alive:
            if not self.is_connected:
                self.log.warning("Connection lost during retry loop.")
                break

            if await self._check_device_alive():
                break

            self.log.warning(
                "Device is not responding. Retrying alive check in %i seconds...",
                interval,
            )
            await asyncio.sleep(interval)

    async def _reconnect_loop(self, max_retries: int | None = None) -> None:
        """Attempt to reconnect periodically, with detailed error logging."""

        retry_delay = 30
        max_retries = max_retries or (24 * 60 * 60) // retry_delay
        attempts = 0

        while not self.is_connected and attempts < max_retries:
            if self.context.connection.closing:
                self.log.info("Reconnection disabled due to manual close.")
                return

            if not self.context.connection.config.reconnect_enabled:
                self.log.info("Reconnection is disabled. Not attempting reconnect.")
                return

            self.log.warning(
                "Attempting to reconnect in %d seconds... (Attempt %d/%d)",
                retry_delay,
                attempts + 1,
                max_retries,
            )

            try:
                await self.open(**self.context.connection.config.connection_params)

                if self.is_connected:
                    self.log.info("Reconnection successful.")
                    return

            except asyncio.CancelledError:
                self.log.info("Reconnect loop cancelled.")
                raise

            except asyncio.exceptions.TimeoutError:
                self.log.error("Reconnection attempt timed out. Retrying...")

            except OSError as e:
                error_code = e.errno if e.errno is not None else -1
                error_name = errno.errorcode.get(error_code, "UNKNOWN_ERRNO")

                try:
                    error_message = os.strerror(error_code)
                except ValueError:
                    error_message = "Unknown error"

                self.log.error(
                    "Reconnection failed due to network error (Errno %d - %s): %s",
                    error_code,
                    error_name,
                    error_message,
                )

            if not self.is_connected:
                await asyncio.sleep(retry_delay)

            attempts += 1

        if attempts >= max_retries:
            self.log.error(
                "Max reconnection attempts (%d) reached. Stopping retries.", max_retries
            )

    async def _async_event_handler(
        self, event_type: EventType, event_data: dict
    ) -> None:
        """Handle events from the connection handler using TaskGroup for safe async execution."""

        if not isinstance(event_type, EventType):
            self.log.error("Invalid event type received: %s", event_type)
            return

        event_messages = {
            EventType.CONNECTION_STATE: "Received connection state event: %s",
            EventType.DATA_RECEIVED: "Data received: %s",
        }

        self.log.debug(
            event_messages.get(event_type, "Unknown event: %s"),
            event_data.get("message", "No message provided"),
        )

        match event_type:
            case EventType.CONNECTION_STATE:
                state = event_data.get("state")

                if state is None:
                    self.log.error("Missing 'state' key in event_data: %s", event_data)
                    return

                try:
                    self.context.connection.config.status = ConnectionStatus(state)
                    self.log.info(
                        "Updated connection status: %s",
                        self.context.connection.config.status.name,
                    )
                except ValueError:
                    self.log.error(
                        "Invalid connection state received: %s. Defaulting to DISCONNECTED.",
                        state,
                    )
                    self.context.connection.config.status = (
                        ConnectionStatus.DISCONNECTED
                    )

                if self.context.connection.config.status == ConnectionStatus.CONNECTED:
                    self.log.info("Device connected. Performing initial alive check.")

                    await self.context.connection.task_manager.cancel_task(
                        "reconnect_loop"
                    )

                    self.context.connection.task_manager.add_task(
                        self._retry_alive_check(),
                        name="retry_alive_check",
                    )

                elif (
                    self.context.connection.config.status
                    == ConnectionStatus.DISCONNECTED
                ):
                    self.context.device_state.info = None
                    self.context.connection.handler = None
                    # self.context.device_state.is_alive = False
                    self.context.system_state.operational_state.is_alive = False
                    self.log.warning("Connection lost. is_connected set to False.")

                    if self.context.connection.config.reconnect_enabled:
                        self.context.connection.task_manager.add_task(
                            self._reconnect_loop(), name="reconnect_loop"
                        )

            case EventType.DATA_RECEIVED:
                response = event_data.get("response")

                if response is None:
                    self.log.error(
                        "Missing 'response' key in event_data: %s", event_data
                    )
                    return

                self.context.device_state.last_data_received = datetime.now(UTC)

                self.context.connection.task_manager.add_task(
                    self._handle_data_received(response), name="handle_data_received"
                )

    def _device_info_callback(self, updated_device_info: DeviceInfo) -> None:
        """Update the stored device information if changes are detected."""

        if not isinstance(updated_device_info, DeviceInfo):
            self.log.error(
                "Invalid device info update: Expected DeviceInfo, got %s",
                type(updated_device_info).__name__,
            )
            return

        if self.context.device_state.info == updated_device_info:
            self.log.debug("No changes detected in DeviceInfo, skipping update.")
            return

        self.context.device_state.info = updated_device_info
        self.log.info("Device Info updated successfully.")

        custom_log_pprint(self.device_info.model_dump(), self.log.debug)

    async def _handle_data_received(self, response: Any) -> None:
        """Handle responses received from the hardware."""

        response_type = type(response).__name__

        self.log_debug("Handling received response: %s", response_type)

        try:
            handler = self._get_message_handler(type(response))

            if not handler:
                self.log_warning(
                    "No handler found for response type: %s", response_type
                )
                return

            if not isinstance(handler, (Callable, Coroutine)):
                self.log_error(
                    "Invalid handler returned for type %s: %s", response_type, handler
                )
                return

            if asyncio.iscoroutinefunction(handler):
                await handler(response)  # Ensure async handlers are awaited
            else:
                handler(response)  # Call sync handlers normally

        except Exception as e:
            self.log_critical(
                "Error while handling response of type %s: %s", response_type, e
            )
            raise  # Let the exception propagate

    def _get_message_handler(self, response_type: type) -> Callable[[Any], Any] | None:
        """Retrieve the appropriate handler for a given response type."""

        if not isinstance(response_type, type):
            self.log.error(
                "Invalid response_type passed to _get_message_handler: %s",
                response_type,
            )
            return None

        handlers: dict[type, Callable[[Any], Any]] = {
            AutoAspect: self._handle_operational_state,
            GameMode: self._handle_operational_state,
            OutputColorFormat: self._handle_operational_state,
            PowerState: self._handle_operational_state,
            StatusAlive: self._handle_operational_state,
            FullInfoV1: partial(self._handle_full_info, version="V1"),
            FullInfoV2: partial(self._handle_full_info, version="V2"),
            FullInfoV3: partial(self._handle_full_info, version="V3"),
            FullInfoV4: partial(self._handle_full_info, version="V4"),
            InputBasicInfo: partial(
                self._handle_system_state, state_attr="basic_input_info"
            ),
            InputVideo: partial(self._handle_system_state, state_attr="input_video"),
            OutputBasicInfo: partial(
                self._handle_system_state, state_attr="basic_output_info"
            ),
            OutputMode: partial(self._handle_system_state, state_attr="output_mode"),
            StatusID: partial(self._handle_system_state, state_attr="device_id"),
            LabelQuery: self._handle_label_query,
        }

        handler = handlers.get(response_type)

        if handler is None:
            self.log.warning(
                "No handler found for response type: %s", response_type.__name__
            )

        return handler

    def _handle_operational_state(self, response: Response) -> None:
        """Handle state updates based on response fields.

        Extract the relevant field from the response, update the system state,
        and log the result.

        Args:
            response (Response): The response object.

        """

        field_names = [attr for attr in dir(response) if attr.startswith("field_")]

        if not field_names:
            self.log.warning("No expected field found in response: %s", response)
            return

        field_name = field_names[0]
        state_value = getattr(response, field_name, None)

        if state_value is None:
            self.log.warning("Missing '%s' in response: %s", field_name, response)
            return

        state_key = field_name.replace("field_", "")
        if state_key == "is_alive":
            self.context.device_state.alive_event.set()

        # Force validation through BaseOperationalState before updating
        operational_state = self.context.system_state.operational_state
        updated_data = operational_state.model_dump()  # Get existing values as a dict
        updated_data[state_key] = state_value  # Apply new value

        # Create a new instance of BaseScreenConfig to enforce validation
        new_config = BaseOperationalState(**updated_data)

        # Update state with the validated model
        if self.context.system_state.update_state(operational_state=new_config):
            self.log.debug(
                "operational_state[%s] updated: %s",
                state_key,
                getattr(new_config, state_key),
            )
            custom_log_pprint(
                self.context.system_state.operational_state.model_dump(),
                self.log.debug,
            )
        else:
            self.log.debug("Operational State unchanged, no update needed.")

    def _handle_system_state(self, response: BaseModel, state_attr: str) -> None:
        """Update the specified state attribute in system_state."""

        updated = self.context.system_state.update_state(**{state_attr: response})
        state_value: BaseModel = getattr(self.context.system_state, state_attr)

        if updated:
            self.log.debug("%s Updated", state_attr.replace("_", " ").title())
            custom_log_pprint(state_value.model_dump(), self.log.debug)
        else:
            self.log.debug(
                "%s unchanged, no update needed.", state_attr.replace("_", " ").title()
            )

    async def _handle_full_info(self, response: BaseFullInfo, version: str) -> None:
        """Handle updates for full device information asynchronously.

        This method processes and updates full device information while ensuring
        efficiency and proper event management.
        """

        if not isinstance(response, BaseFullInfo):
            self.log.error(
                "Invalid response type for full info update: %s",
                type(response).__name__,
            )
            return

        if self.context.system_state.update_full_info(response):
            self.log.info("Full Info %s Updated", version)
            custom_log_pprint(
                self.context.system_state.full_info.model_dump(),
                self.log.debug,
            )

            if self.context.device_state.device_event.is_set():
                self.log.debug("Clearing device event flag.")
                self.context.device_state.device_event.clear()
            elif self.device_status == DeviceStatus.ACTIVE:
                self.log.debug("Triggering full system state refresh.")
                try:
                    await self.context.connection.executor.get_all(exclude_status=True)
                except (TimeoutError, ConnectionError, OSError) as e:
                    self.log.error(
                        "System state refresh failed due to network issue: %s", e
                    )
        else:
            self.log.debug("Full Info unchanged, no update needed.")

    async def _handle_label_query(self, response: LabelQuery) -> None:
        """Handle label query response asynchronously and update label mapping."""

        if not hasattr(response, "field_label_index") or not hasattr(
            response, "field_label_name"
        ):
            self.log.warning("Malformed LabelQuery response received: %s", response)
            return

        if response.field_label_index is None or response.field_label_name is None:
            self.log.warning("Invalid label data in response: %s", response)
            return

        self.labels[response.field_label_index] = response.field_label_name
        self.log.debug(
            "Label Updated: Index %s -> Name '%s'",
            response.field_label_index,
            response.field_label_name,
        )

        if len(self.labels) == 64:
            self.log.debug("All 64 labels received, triggering label display.")
            await self.show_labels()

    async def show_all(self) -> None:
        """Show all system state info."""

        custom_log_pprint(self.context.system_state.to_dict(), self.log.info)

    async def show_info(self) -> None:
        """Log all device information."""

        if not self.device_info:
            self.log.warning("No device information available.")
            return

        self.log.info("Displaying device information:")
        custom_log_pprint(self.device_info.model_dump(), self.log.info)

    async def show_labels(self) -> None:
        """Show device port labels, sorted and categorized into lists."""

        if not self.labels:
            self.log.warning("No labels available to display.")
            return

        # Custom sorting function: Sort alphabetically, but numeric keys come last
        def custom_sort(key: str) -> tuple[bool, str]:
            return (key[0].isdigit(), key)

        # Sort labels dictionary
        sorted_labels = {
            key: self.labels[key] for key in sorted(self.labels.keys(), key=custom_sort)
        }

        self.log.info("Displaying sorted port labels:")
        custom_log_pprint(sorted_labels, self.log.info)

        # Categorize labels based on key prefixes
        self.source_list = [v for k, v in sorted_labels.items() if k.startswith("A")]
        self.cms_list = [v for k, v in sorted_labels.items() if k.startswith("2")]
        self.style_list = [v for k, v in sorted_labels.items() if k.startswith("3")]

        self.log.info("Source List: %s", self.source_list)
        self.log.info("CMS List: %s", self.cms_list)
        self.log.info("Style List: %s", self.style_list)

    async def show_source_list(self) -> None:
        """Log the current source list information."""

        if not self.source_list:
            self.log.warning("Source list is empty or not initialized.")
            return

        self.log.debug("Displaying source list:")
        custom_log_pprint(self.source_list, self.log.debug)

    async def show_power_state(self) -> None:
        """Show Device Power State."""

        self.log.info("Power State = %s", str(self.device_status))
