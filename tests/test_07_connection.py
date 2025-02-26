"""Tests for the `lumagen.connection` module."""

import asyncio
from collections import deque
from unittest.mock import AsyncMock, MagicMock, patch

from lumagen.classes import TaskManager
from lumagen.connection import BaseHandler, ConnectionState
from lumagen.constants import ASCII_COMMAND_LIST, CMD_START, CMD_TERMINATOR
from lumagen.messages import Response
import pytest

# pylint: disable=protected-access
# pylint: disable=missing-function-docstring


def test_connection_state_initialization() -> None:
    """Test that ConnectionState initializes correctly."""
    state = ConnectionState()
    assert isinstance(state.buffer, deque)
    assert isinstance(state.command_queue, deque)
    assert isinstance(state.command_response_map, dict)
    assert state.last_command_byte == ""
    assert state.sending_command is False
    assert state.current_command is None


def test_append_to_buffer() -> None:
    """Test appending data to the buffer."""
    state = ConnectionState()
    state.append_to_buffer("test_data")
    assert list(state.buffer) == list("test_data")


def test_clear_buffer() -> None:
    """Test clearing the buffer."""
    state = ConnectionState()
    state.append_to_buffer("test_data")
    assert len(state.buffer) > 0
    state.clear_buffer()
    assert len(state.buffer) == 0


def test_has_pending_commands_empty() -> None:
    """Test has_pending_commands when queue is empty."""
    state = ConnectionState()
    assert not state.has_pending_commands()
    assert state.current_command is None


def test_has_pending_commands_non_empty() -> None:
    """Test has_pending_commands when queue has commands."""
    state = ConnectionState()
    state.command_queue.append("CMD1")
    assert state.has_pending_commands()
    assert state.current_command is None  # Should remain None until pop


def test_pop_next_command_with_command() -> None:
    """Test retrieving next command when queue has commands."""
    state = ConnectionState()
    state.command_queue.append("CMD1")
    state.command_queue.append("CMD2")

    # Mock logging to avoid unnecessary log output in tests
    state.log = MagicMock()

    cmd = state.pop_next_command()
    assert cmd == "CMD1"
    assert state.current_command == "CMD1"
    assert len(state.command_queue) == 1
    state.log.debug.assert_called_with("Commands remaining in queue: %d", 1)


def test_pop_next_command_empty_queue() -> None:
    """Test pop_next_command when queue is empty."""
    state = ConnectionState()

    # Mock logging to avoid unnecessary log output in tests
    state.log = MagicMock()

    cmd = state.pop_next_command()
    assert cmd is None
    assert state.current_command is None
    state.log.debug.assert_called_with("Queue is empty after pop attempt")


@pytest.mark.asyncio
async def test_base_handler_initialization() -> None:
    """Test BaseHandler initialization."""
    handler = BaseHandler()
    assert isinstance(handler._task_manager, TaskManager)  # noqa: SLF001
    assert isinstance(handler.connection_state, ConnectionState)
    assert isinstance(handler._state_lock, asyncio.Lock)  # noqa: SLF001
    assert handler.reader is None
    assert handler.writer is None


@pytest.mark.asyncio
async def test_process_stream() -> None:
    """Test process_stream starts without error and handles ValueError properly."""
    handler = BaseHandler()

    async def mock_read_single_byte(_):
        """Mock function to simulate reading a byte once."""
        if not hasattr(mock_read_single_byte, "called"):
            mock_read_single_byte.called = True
            return True
        return False

    handler._read_single_byte = AsyncMock(side_effect=mock_read_single_byte)  # noqa: SLF001
    handler._read_additional_data = AsyncMock(return_value="#ZQS00!S00,Ok\n")  # noqa: SLF001
    handler._dispatcher = MagicMock()  # noqa: SLF001
    handler._dispatcher.invoke_event = AsyncMock()  # noqa: SLF001
    handler._task_manager.get_task = MagicMock(return_value=None)  # noqa: SLF001
    handler.process_next_command = MagicMock()
    handler.log = MagicMock()

    # First test: process_stream should start & cancel normally
    task = asyncio.create_task(handler.process_stream())
    await asyncio.sleep(0.1)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    # Second test: Keep valid data, but make Response.factory fail
    if hasattr(mock_read_single_byte, "called"):
        del mock_read_single_byte.called

    with patch(
        "lumagen.messages.Response.factory",
        side_effect=ValueError("Invalid message format"),
    ):
        task = asyncio.create_task(handler.process_stream())
        await asyncio.sleep(0.1)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        assert Response.factory.call_count > 0, "? Response.factory was never called!"

        handler.log.error.assert_called()
        error_message = handler.log.error.call_args[0][0]
        assert isinstance(
            error_message, ValueError
        ), f"Unexpected log call argument type: {type(error_message)}"
        assert (
            str(error_message) == "Invalid message format"
        ), f"Unexpected log message: {error_message}"

    # Third test: Simulate empty buffer by setting _read_additional_data to return "r\n"
    if hasattr(mock_read_single_byte, "called"):
        del mock_read_single_byte.called

    handler.process_next_command.reset_mock()

    handler._read_additional_data = AsyncMock(  # noqa: SLF001
        return_value="\r\n"
    )  # Simulates an empty message

    task = asyncio.create_task(handler.process_stream())
    await asyncio.sleep(0.1)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    handler.process_next_command.assert_not_called()

    # Fourth test: Simulate buffer startswith ignored prefixes"
    if hasattr(mock_read_single_byte, "called"):
        del mock_read_single_byte.called

    handler.process_next_command.reset_mock()

    handler._read_additional_data = AsyncMock(  # noqa: SLF001
        return_value="#ZY520\r\n"
    )  # Simulates an ignored prefix

    task = asyncio.create_task(handler.process_stream())
    await asyncio.sleep(0.1)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    # Fifth test: Simulate buffer keypress"
    if hasattr(mock_read_single_byte, "called"):
        del mock_read_single_byte.called

    handler.process_next_command.reset_mock()

    handler._read_additional_data = AsyncMock(  # noqa: SLF001
        return_value="#X{"
    )  # Simulates a keypress

    with patch(
        "lumagen.connection.process_command_or_keypress",
        return_value=("KEY_X", "Exit", True),
    ) as mock_process_command:
        task = asyncio.create_task(handler.process_stream())
        await asyncio.sleep(0.1)
        task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    mock_process_command.assert_called_once_with("#X{", ASCII_COMMAND_LIST)

    expected_log_message = "Received Keypress Command: Exit"
    handler.log.debug.assert_called_with(expected_log_message)

    handler.process_next_command.assert_called()

    # Sixth test: Simulate buffer ends with terminator"
    if hasattr(mock_read_single_byte, "called"):
        del mock_read_single_byte.called

    handler.process_next_command.reset_mock()

    handler._read_additional_data = AsyncMock(  # noqa: SLF001
        return_value="Z\n"
    )

    task = asyncio.create_task(handler.process_stream())
    await asyncio.sleep(0.1)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    handler.process_next_command.assert_not_called()

    # Seventh test: simulate process stream cancel task"
    handler.process_next_command.reset_mock()

    async def mock_read_single_byte_wait(_):
        while True:
            await asyncio.sleep(1)  # Simulates a never-ending read

    handler._read_single_byte = AsyncMock(side_effect=mock_read_single_byte_wait)  # noqa: SLF001

    task = asyncio.create_task(handler.process_stream())
    await asyncio.sleep(0.1)  # Give time for the task to enter the infinite wait state

    task.cancel()  # Force cancel since `_read_single_byte` never returns

    with pytest.raises(asyncio.CancelledError):
        await task  # Ensure the task actually raises CancelledError

    handler.process_next_command.assert_not_called()


@pytest.mark.asyncio
async def test_read_single_byte() -> None:
    """Test reading a single byte from the stream."""
    handler = BaseHandler()
    handler.reader = AsyncMock()
    handler.reader.read = AsyncMock(return_value=b"A")

    buffer_manager = MagicMock()
    buffer_manager.append = MagicMock()

    result = await handler._read_single_byte(buffer_manager)  # noqa: SLF001
    assert result is True
    buffer_manager.append.assert_called_with("A")


@pytest.mark.asyncio
async def test_read_single_byte_stream_ended() -> None:
    """Test reading a single byte when the stream ends unexpectedly."""
    handler = BaseHandler()
    handler.reader = AsyncMock()
    handler.reader.read = AsyncMock(return_value=b"")
    handler.log = MagicMock()

    buffer_manager = MagicMock()

    result = await handler._read_single_byte(buffer_manager)  # noqa: SLF001
    assert result is False
    handler.log.warning.assert_called_with("Stream ended unexpectedly")


@pytest.mark.asyncio
async def test_read_additional_data() -> None:
    """Test reading additional data from the stream."""
    handler = BaseHandler()
    handler.reader = AsyncMock()
    handler.reader.readuntil = AsyncMock(return_value=b"DATA\n")
    handler.reader.read = AsyncMock(return_value=b"DATA")

    result = await handler._read_additional_data()  # noqa: SLF001
    assert result == "DATA\n"


@pytest.mark.asyncio
async def test_queue_command_valid() -> None:
    """Test queuing a valid command."""
    handler = BaseHandler()
    handler.process_next_command = MagicMock()
    handler.log = MagicMock()

    await handler.queue_command("CMD1")

    assert "CMD1" in handler.connection_state.command_queue
    assert len(handler.connection_state.command_queue) == 1
    handler.process_next_command.assert_called_once()


@pytest.mark.asyncio
async def test_queue_command_invalid() -> None:
    """Test queuing an invalid command."""
    handler = BaseHandler()
    handler.process_next_command = MagicMock()
    handler.log = MagicMock()

    await handler.queue_command("")
    handler.log.error.assert_called_with("No valid commands to queue.")


def test_should_exit_processing_sending_command_true() -> None:
    """Test that _should_exit_processing returns True when sending_command is True."""
    connection = BaseHandler()  # Create a real instance of the class
    connection.connection_state = MagicMock()
    connection.connection_state.sending_command = True
    connection.connection_state.has_pending_commands.return_value = True

    assert connection._should_exit_processing() is True  # noqa: SLF001


def test_should_exit_processing_no_pending_commands() -> None:
    """Test that _should_exit_processing returns True when there are no pending commands."""
    connection = BaseHandler()
    connection.connection_state = MagicMock()
    connection.connection_state.sending_command = False
    connection.connection_state.has_pending_commands.return_value = False

    assert connection._should_exit_processing() is True  # noqa: SLF001


def test_should_exit_processing_continue_processing() -> None:
    """Test that _should_exit_processing returns False when there are pending commands."""
    connection = BaseHandler()
    connection.connection_state = MagicMock()
    connection.connection_state.sending_command = False
    connection.connection_state.has_pending_commands.return_value = True

    assert connection._should_exit_processing() is False  # noqa: SLF001


@pytest.mark.asyncio
async def test_process_next_command_exits_on_should_exit() -> None:
    """Test that _process_next_command exits immediately if _should_exit_processing returns True."""
    connection = BaseHandler()
    connection._should_exit_processing = MagicMock(return_value=True)  # noqa: SLF001
    connection.connection_state = MagicMock()
    connection.connection_state.pop_next_command.return_value = None
    connection.send = AsyncMock()

    await connection._process_next_command()  # noqa: SLF001

    connection._should_exit_processing.assert_called_once()  # noqa: SLF001
    connection.send.assert_not_called()  # No command should be sent


@pytest.mark.asyncio
async def test_process_next_command_sends_command() -> None:
    """Test that _process_next_command sends a command when available."""
    connection = BaseHandler()
    connection._should_exit_processing = MagicMock(  # noqa: SLF001
        side_effect=[False, True]
    )  # Process one command, then exit
    connection.connection_state = MagicMock()
    connection.connection_state.pop_next_command.return_value = "TEST_CMD"
    connection.send = AsyncMock(return_value=True)

    await connection._process_next_command()  # noqa: SLF001

    connection.send.assert_called_once_with(CMD_START + b"TEST_CMD" + CMD_TERMINATOR)


@pytest.mark.asyncio
async def test_process_next_command_stops_when_send_fails() -> None:
    """Test that _process_next_command stops processing when send fails."""
    connection = BaseHandler()
    connection._should_exit_processing = MagicMock(  # noqa: SLF001
        side_effect=[False, True]
    )  # Process one command, then exit
    connection.connection_state = MagicMock()
    connection.connection_state.pop_next_command.return_value = "FAIL_CMD"
    connection.send = AsyncMock(return_value=False)  # Simulate send failure

    await connection._process_next_command()  # noqa: SLF001

    connection.send.assert_called_once_with(CMD_START + b"FAIL_CMD" + CMD_TERMINATOR)
    connection._should_exit_processing.assert_called_once()  # noqa: SLF001


@pytest.mark.asyncio
async def test_process_next_command_respects_max_iterations() -> None:
    """Test that _process_next_command stops after max_iterations."""
    connection = BaseHandler()
    connection._should_exit_processing = MagicMock(return_value=False)  # noqa: SLF001
    connection.connection_state = MagicMock()
    connection.connection_state.pop_next_command.return_value = "ITER_CMD"
    connection.send = AsyncMock(return_value=True)

    await connection._process_next_command(max_iterations=2)  # noqa: SLF001

    assert connection.send.call_count == 2  # Ensure it only runs twice


@pytest.mark.asyncio
async def test_process_next_command_skips_empty_command() -> None:
    """Test that _process_next_command skips processing when pop_next_command returns None or an empty string."""
    connection = BaseHandler()
    connection._should_exit_processing = MagicMock(  # noqa: SLF001
        side_effect=[False, False, False, True]
    )  # Ensure looping
    connection.connection_state = MagicMock()

    # First two calls return falsy values (None and empty string), third call returns a valid command
    connection.connection_state.pop_next_command.side_effect = [None, "", "VALID_CMD"]

    connection.send = AsyncMock(return_value=True)

    await connection._process_next_command(max_iterations=4)  # noqa: SLF001

    # Ensure send was called only once (for "VALID_CMD"), skipping None and ""
    connection.send.assert_called_once_with(CMD_START + b"VALID_CMD" + CMD_TERMINATOR)


def test_process_next_command_task_exists() -> None:
    """Test that process_next_command does not add a task if it already exists."""
    connection = BaseHandler()
    connection._task_manager = MagicMock()  # noqa: SLF001

    # Simulate that the task already exists
    connection._task_manager.get_task.return_value = True  # noqa: SLF001

    connection.process_next_command()

    # Ensure add_task is never called
    connection._task_manager.add_task.assert_not_called()  # noqa: SLF001


@pytest.mark.asyncio
async def test_process_next_command_task_not_exists() -> None:
    """Test that process_next_command properly schedules _process_next_command using the real task manager."""

    connection = BaseHandler()  # Use the real BaseHandler with its real task manager
    connection._process_next_command = AsyncMock()  # noqa: SLF001

    # Call process_next_command() and let the real task manager handle it
    connection.process_next_command()

    # Wait for the task manager to execute the task
    await asyncio.sleep(0.1)  # ? Allows time for the event loop to process tasks

    # Ensure `_process_next_command()` was actually called
    connection._process_next_command.assert_awaited_once()  # noqa: SLF001


@pytest.mark.asyncio
async def test_queue_command_invalid_type() -> None:
    """Test that queue_command logs an error and returns when given an invalid type."""
    connection = BaseHandler()
    connection.log = MagicMock()
    connection.connection_state = MagicMock()
    connection.connection_state.command_queue = []

    invalid_input = 123  # Invalid type (int)

    await connection.queue_command(invalid_input)

    # Ensure the log error was called with the expected message
    connection.log.error.assert_called_once_with("Invalid command type: %s", "int")

    # Ensure the command queue remains empty
    assert len(connection.connection_state.command_queue) == 0


@pytest.mark.asyncio
async def test_send_not_implemented() -> None:
    """Test that calling send() on BaseHandler raises NotImplementedError."""
    connection = BaseHandler()  # Assuming BaseHandler is the parent class

    with pytest.raises(
        NotImplementedError, match="send method must be implemented by subclasses"
    ):
        await connection.send(b"test data")


@pytest.mark.asyncio
async def test_read_additional_data_readuntil_success() -> None:
    """Test that _read_additional_data returns decoded data when readuntil() succeeds."""
    connection = BaseHandler()
    connection.reader = AsyncMock()

    # Simulate readuntil returning bytes with a newline
    connection.reader.readuntil.return_value = b"TEST DATA\n"

    result = await connection._read_additional_data()  # noqa: SLF001

    assert result.strip() == "TEST DATA"


@pytest.mark.asyncio
async def test_read_additional_data_fallback_to_read() -> None:
    """Test that _read_additional_data uses read(1024) when readuntil() times out."""
    connection = BaseHandler()
    connection.reader = AsyncMock()

    # Simulate readuntil timing out
    connection.reader.readuntil.side_effect = asyncio.exceptions.TimeoutError()

    # Simulate read(1024) succeeding
    connection.reader.read.return_value = b"FALLBACK DATA"

    result = await connection._read_additional_data()  # noqa: SLF001

    assert result == "FALLBACK DATA"


@pytest.mark.asyncio
async def test_read_additional_data_both_fail() -> None:
    """Test that _read_additional_data returns an empty string when both reads fail."""
    connection = BaseHandler()
    connection.reader = AsyncMock()

    # Simulate both read methods timing out
    connection.reader.readuntil.side_effect = asyncio.exceptions.TimeoutError()
    connection.reader.read.side_effect = asyncio.exceptions.TimeoutError()

    result = await connection._read_additional_data()  # noqa: SLF001

    assert result == ""


@pytest.mark.asyncio
async def test_process_stream_reads_data() -> None:
    """Test that process_stream reads and appends data to the buffer."""
    connection = BaseHandler()

    # Ensure _read_single_byte correctly handles buffer_manager argument
    connection._read_single_byte = AsyncMock(return_value=True)  # noqa: SLF001
    connection._read_additional_data = AsyncMock(return_value="TEST DATA")  # noqa: SLF001
    connection._dispatcher = MagicMock()  # noqa: SLF001
    connection.process_next_command = MagicMock()

    # Use asyncio timeout to limit execution instead of causing StopAsyncIteration
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(connection.process_stream(), timeout=0.1)

    # Ensure read functions were called
    connection._read_single_byte.assert_called()  # noqa: SLF001
    connection._read_additional_data.assert_called()  # noqa: SLF001


@pytest.mark.asyncio
async def test_close_normal() -> None:
    """Test that `close()` cancels tasks and logs closure message properly."""

    handler = BaseHandler()
    handler._task_manager = MagicMock()  # noqa: SLF001
    handler._task_manager.cancel_all_tasks = AsyncMock()  # noqa: SLF001
    handler._task_manager.wait_for_all_tasks = AsyncMock()  # noqa: SLF001
    handler.log = MagicMock()

    await handler.close()

    # Ensure tasks are cancelled
    handler._task_manager.cancel_all_tasks.assert_awaited_once()  # noqa: SLF001

    # Ensure it waits for tasks to complete
    handler._task_manager.wait_for_all_tasks.assert_awaited_once()  # noqa: SLF001

    # Check log message
    handler.log.info.assert_called_with("All tasks cancelled and connection closed.")


@pytest.mark.asyncio
async def test_close_cancelled_error() -> None:
    """Test `close()` when `cancel_all_tasks()` raises `CancelledError`."""

    handler = BaseHandler()
    handler._task_manager = MagicMock()  # noqa: SLF001

    # Mock `cancel_all_tasks()` to raise `CancelledError`
    handler._task_manager.cancel_all_tasks = AsyncMock(  # noqa: SLF001
        side_effect=asyncio.CancelledError
    )
    handler._task_manager.wait_for_all_tasks = AsyncMock()  # noqa: SLF001
    handler.log = MagicMock()

    await handler.close()

    # `cancel_all_tasks()` should be awaited once (and not crash)
    handler._task_manager.cancel_all_tasks.assert_awaited_once()  # noqa: SLF001

    # `wait_for_all_tasks()` should still run
    handler._task_manager.wait_for_all_tasks.assert_awaited_once()  # noqa: SLF001

    # Ensure log message is generated despite cancellation error
    handler.log.info.assert_called_with("All tasks cancelled and connection closed.")


@pytest.mark.asyncio
async def test_close_wait_for_tasks_exception() -> None:
    """Test `close()` when `wait_for_all_tasks()` raises an exception."""

    handler = BaseHandler()
    handler._task_manager = MagicMock()  # noqa: SLF001
    handler._task_manager.cancel_all_tasks = AsyncMock()  # noqa: SLF001

    # Mock `wait_for_all_tasks()` to raise an error
    handler._task_manager.wait_for_all_tasks = AsyncMock(  # noqa: SLF001
        side_effect=RuntimeError("Task failure")
    )
    handler.log = MagicMock()

    with pytest.raises(RuntimeError, match="Task failure"):
        await handler.close()

    # `cancel_all_tasks()` should still be awaited
    handler._task_manager.cancel_all_tasks.assert_awaited_once()  # noqa: SLF001

    # `wait_for_all_tasks()` should raise an exception
    handler._task_manager.wait_for_all_tasks.assert_awaited_once()  # noqa: SLF001

    # Ensure the log message was **not** generated (since `close()` crashed)
    handler.log.info.assert_not_called()
