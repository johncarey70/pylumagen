"""Tests for the `lumagen.utils` module."""

import asyncio
import contextlib
import logging

from lumagen.constants import DeviceStatus
from lumagen.utils import (
    BufferManager,
    LoggingMixin,
    LogProxy,
    TaskManager,
    custom_log_pprint,
    flatten_dictionary,
    process_command_or_keypress,
)
import pytest


@pytest.fixture
def buffer_manager() -> BufferManager:
    """Fixture for BufferManager instance."""
    return BufferManager(terminator="\n", ignored_prefixes=("DEBUG",))


def test_buffer_manager_append_extract(buffer_manager: BufferManager) -> None:
    """Test appending and extracting messages in BufferManager."""
    buffer_manager.append("Hello World\n")
    assert buffer_manager.extract_message() == "Hello World"
    assert buffer_manager.is_empty()


def test_buffer_manager_multiple_messages(buffer_manager: BufferManager) -> None:
    """Test handling multiple messages in BufferManager."""
    buffer_manager.append("Message 1\nMessage 2\n")
    assert buffer_manager.extract_message() == "Message 1"
    assert buffer_manager.extract_message() == "Message 2"
    assert buffer_manager.is_empty()


def test_buffer_manager_clear(buffer_manager: BufferManager) -> None:
    """Test clearing the buffer in BufferManager."""
    buffer_manager.append("Temporary Data\n")
    buffer_manager.clear()
    assert buffer_manager.is_empty()


def test_buffer_manager_starts_with(buffer_manager: BufferManager) -> None:
    """Test starts_with method in BufferManager."""
    buffer_manager.append("ERROR: Something went wrong")
    assert buffer_manager.starts_with(("ERROR", "WARN"))


def test_buffer_manager_ends_with_terminator(buffer_manager: BufferManager) -> None:
    """Test ends_with_terminator method in BufferManager."""
    buffer_manager.append("Hello\n")
    assert buffer_manager.ends_with_terminator()


def test_buffer_manager_extract_message_no_terminator() -> None:
    """Test extract_message when buffer lacks a terminator."""

    buffer_manager = BufferManager(terminator="\n")

    buffer_manager.buffer = "Partial message without terminator"
    extracted = buffer_manager.extract_message()
    assert extracted == ""
    assert buffer_manager.buffer == "Partial message without terminator"


def test_buffer_adjust_buffer() -> None:
    """Test adjusting buffer based on keyword matching."""
    buffer_manager = BufferManager()

    # Test: Adjust buffer to start from first detected keyword
    buffer_manager.append("Random text before KEYWORD important data")
    buffer_manager.adjust_buffer(["keyword"])  # Case insensitive match
    assert buffer_manager.buffer == "KEYWORD important data"

    # Test: Multiple keywords, should match the first occurrence
    buffer_manager.clear()
    buffer_manager.append("Prefix IGNORE this KEY and data")
    buffer_manager.adjust_buffer(["key", "data"])
    assert buffer_manager.buffer == "KEY and data"

    # Test: No match should keep the buffer unchanged
    buffer_manager.clear()
    buffer_manager.append("Nothing matches here")
    buffer_manager.adjust_buffer(["keyword"])
    assert buffer_manager.buffer == "Nothing matches here"

    # Test: Special case where buffer is exactly "#!"
    buffer_manager.clear()
    buffer_manager.append("#!")
    buffer_manager.adjust_buffer(["!"])
    assert buffer_manager.buffer == "#!"  # Should remain unchanged

    # Test: Case-insensitive match
    buffer_manager.clear()
    buffer_manager.append("random start KEYword middle")
    buffer_manager.adjust_buffer(["keyword"])
    assert buffer_manager.buffer == "KEYword middle"


def test_process_command_or_keypress() -> None:
    """Test processing command or keypress."""
    my_dict = {"start": "Begin Execution", "stop": "End Execution"}
    assert process_command_or_keypress("#start", my_dict) == (
        "start",
        "Begin Execution",
        False,
    )
    assert process_command_or_keypress("stop", my_dict) == (
        "stop",
        "End Execution",
        True,
    )
    assert process_command_or_keypress("unknown", my_dict) == (None, None, False)


def test_flatten_dictionary() -> None:
    """Test flattening nested dictionaries."""
    nested_dict = {"a": 1, "b": {"c": 2, "d": {"e": 3}}}
    assert flatten_dictionary(nested_dict) == {"a": 1, "c": 2, "e": 3}

    nested_enum_dict = {
        "status": DeviceStatus.STANDBY,
        "config": {"mode": DeviceStatus.ACTIVE},
    }
    expected_output = {"status": "DeviceStatus.STANDBY", "mode": "DeviceStatus.ACTIVE"}

    assert flatten_dictionary(nested_enum_dict) == expected_output


@pytest.fixture
def task_manager() -> TaskManager:
    """Fixture for TaskManager instance."""
    return TaskManager()


@pytest.mark.asyncio
async def test_task_manager_add_and_get_task(task_manager: TaskManager) -> None:
    """Test adding and retrieving a task from TaskManager."""

    async def sample_task():
        await asyncio.sleep(0.1)
        return "Task Done"

    task = task_manager.add_task(sample_task(), "test_task")
    assert task_manager.get_task("test_task") == task

    await asyncio.sleep(0.2)  # Allow task to complete
    assert task_manager.get_task("test_task") is None  # Task should be removed


@pytest.mark.asyncio
async def test_task_manager_add_task_duplicate(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test add_task() when a task with the same name is already running."""

    task_manager = TaskManager()

    async def sample_task():
        await asyncio.sleep(1)  # Simulate a running task

    # Add the first task
    first_task = task_manager.add_task(sample_task(), "duplicate_task")
    await asyncio.sleep(0.1)

    # Try adding the same task name again
    with caplog.at_level("WARNING"):
        duplicate_task = asyncio.ensure_future(
            sample_task()
        )  # Schedule a second instance
        second_task = task_manager.add_task(duplicate_task, "duplicate_task")

    # Verify that the second task is the same as the first one
    assert first_task is second_task

    # Verify the warning message was logged
    assert (
        "Task 'duplicate_task' is already running. Skipping duplicate." in caplog.text
    )

    # Cleanup: Cancel both tasks to avoid garbage collection warnings
    first_task.cancel()
    duplicate_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await first_task

    with pytest.raises(asyncio.CancelledError):
        await duplicate_task


@pytest.mark.asyncio
async def test_task_manager_add_task_invalid_name() -> None:
    """Test add_task() when the task name is not a string."""

    task_manager = TaskManager()

    async def sample_task():
        await asyncio.sleep(0.1)

    invalid_names = [None, 123, 3.14, [], {}, object()]  # Various invalid types

    for invalid_name in invalid_names:
        coro = sample_task()  # Create coroutine object
        task = asyncio.create_task(coro)  # Schedule task execution
        await asyncio.sleep(0.1)

        with pytest.raises(TypeError, match="Task name must be a string"):
            task_manager.add_task(task, invalid_name)  # Pass running task

        # Ensure task is properly cleaned up to avoid warnings
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_task_manager_cancel_task() -> None:
    """Test that task_manager.cancel_task() properly cancels a running task."""

    task_manager = TaskManager()

    async def sample_task():
        while True:
            await asyncio.sleep(1)

    # Add a long-running task
    task_manager.add_task(sample_task(), "long_task")
    await asyncio.sleep(0.1)  # Ensure task starts before cancellation

    # Cancel the task
    with pytest.raises(asyncio.CancelledError):
        await task_manager.cancel_task("long_task")

    # Wait briefly to ensure cancellation is processed
    await asyncio.sleep(0.1)

    # Verify the task is no longer active
    assert (
        task_manager.get_task("long_task") is None
    ), "The task was not properly removed after cancellation!"


@pytest.mark.asyncio
async def test_task_manager_cancel_all_tasks(task_manager: TaskManager) -> None:
    """Test that `task_manager.cancel_all_tasks()` properly cancels all running tasks."""

    async def sample_task():
        while True:
            await asyncio.sleep(1)

    # Add long-running tasks
    task_manager.add_task(sample_task(), "task1")
    task_manager.add_task(sample_task(), "task2")

    await asyncio.sleep(0.1)  # Ensure tasks start before cancellation

    # Cancel all tasks and ensure `CancelledError` is raised
    with pytest.raises(asyncio.CancelledError):
        await task_manager.cancel_all_tasks()

    # Wait briefly to ensure cancellation is fully processed
    await asyncio.sleep(0.1)

    # Verify all tasks are removed
    assert (
        not task_manager.active_tasks
    ), "Not all tasks were properly removed after cancellation!"


@pytest.mark.asyncio
async def test_task_manager_cancel_nonexistent_task(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test cancel_task() when trying to cancel a task that doesn't exist."""

    task_manager = TaskManager()

    # Attempt to cancel a task that was never added
    await task_manager.cancel_task("nonexistent_task")

    # Since the task does not exist, no warnings or errors should be logged
    assert "Cancelling task" not in caplog.text  # Ensure no log entry for cancellation


@pytest.mark.asyncio
async def test_task_manager_cancel_task_timeout_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test TaskManager.cancel_task() handling asyncio.TimeoutError."""

    task_manager = TaskManager()

    async def sample_task():
        try:
            await asyncio.sleep(2)  # Simulate a long-running task
        except asyncio.CancelledError as e:
            raise asyncio.exceptions.TimeoutError(
                "Simulated TimeoutError"
            ) from e  # Preserve original exception as __cause__

    # Add a task named "long_task"
    task_manager.add_task(sample_task(), "long_task")

    await asyncio.sleep(0.1)  # Allow task to start

    # Expect TimeoutError to be raised
    with pytest.raises(
        asyncio.TimeoutError, match="Simulated TimeoutError"
    ) as exc_info:
        await task_manager.cancel_task("long_task")

    # Ensure the original cause is CancelledError
    assert isinstance(
        exc_info.value.__cause__, asyncio.CancelledError
    ), "`__cause__` is not `CancelledError`!"

    # Use the actual log message in the assertion
    assert "Task 'long_task' raised an exception: Simulated TimeoutError" in caplog.text


@pytest.mark.asyncio
async def test_task_manager_cancel_task_runtime_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test TaskManager.cancel_task() handling RuntimeError."""

    task_manager = TaskManager()

    async def sample_task():
        try:
            await asyncio.sleep(2)  # Simulate a long-running task
        except asyncio.CancelledError as e:
            raise RuntimeError(
                "Simulated RuntimeError"
            ) from e  # Preserve `CancelledError` as `__cause__`

    # Add a task named "runtime_task"
    task_manager.add_task(sample_task(), "runtime_task")

    await asyncio.sleep(0.1)  # Allow task to start

    # Expect RuntimeError to be raised
    with pytest.raises(RuntimeError, match="Simulated RuntimeError") as exc_info:
        await task_manager.cancel_task("runtime_task")

    # Ensure the original cause is CancelledError
    assert isinstance(
        exc_info.value.__cause__, asyncio.CancelledError
    ), "`__cause__` is not `CancelledError`!"

    # Use the actual log message in the assertion
    assert (
        "Task 'runtime_task' raised an exception: Simulated RuntimeError" in caplog.text
    )


@pytest.mark.asyncio
async def test_task_manager_wait_for_all_tasks() -> None:
    """Test TaskManager.wait_for_all_tasks() to ensure it waits for all tasks to complete."""

    task_manager = TaskManager()
    completed_tasks = []

    async def sample_task(task_name: str):
        await asyncio.sleep(0.1)
        completed_tasks.append(task_name)

    # Add multiple tasks
    task_manager.add_task(sample_task("task1"), "task1")
    task_manager.add_task(sample_task("task2"), "task2")
    task_manager.add_task(sample_task("task3"), "task3")

    # Ensure tasks are in the manager
    assert len(task_manager.active_tasks) == 3

    # Wait for all tasks to complete
    await task_manager.wait_for_all_tasks()

    # Verify that all tasks completed
    assert len(completed_tasks) == 3
    assert "task1" in completed_tasks
    assert "task2" in completed_tasks
    assert "task3" in completed_tasks

    # Ensure TaskManager no longer tracks completed tasks
    assert len(task_manager.active_tasks) == 0


@pytest.mark.asyncio
async def test_task_manager_handle_task_completion_with_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test _handle_task_completion() when a task raises an exception."""

    task_manager = TaskManager()

    async def failing_task():
        raise ValueError("Simulated task failure")

    # Add the task and manually trigger _handle_task_completion
    task = asyncio.create_task(failing_task())
    task_manager.active_tasks["failing_task"] = task

    # Wait for the task to fail
    await asyncio.sleep(0.1)

    # Manually call _handle_task_completion as TaskManager would
    task_manager._handle_task_completion(task, "failing_task")  # noqa: SLF001

    # Verify the log message for the raised exception
    assert (
        "Task 'failing_task' raised an exception: Simulated task failure" in caplog.text
    )


def test_logging_mixin(caplog: pytest.LogCaptureFixture) -> None:
    """Test LoggingMixin functionality, including LogProxy integration."""

    class TestLogger(LoggingMixin):
        """Test class inheriting from LoggingMixin."""

        def __init__(self) -> None:
            super().__init__()
            self.logger = logging.getLogger("test_logger")

    test_logger = TestLogger()

    # Enable debug logging and test log methods
    test_logger.enable_debug_logging()
    test_logger.log_debug("This is a debug message")
    test_logger.log_info("This is an info message")
    test_logger.log_warning("This is a warning message")
    test_logger.log_error("This is an error message")
    test_logger.log_critical("This is a critical message")

    assert not test_logger._disable_debug_logging  # noqa: SLF001

    # Disable debug logging and verify the flag
    test_logger.disable_debug_logging()
    assert test_logger._disable_debug_logging  # noqa: SLF001

    # Ensure 'log' property exists and returns a LogProxy
    assert hasattr(test_logger, "log")
    assert test_logger.log is not None
    assert isinstance(test_logger.log, LogProxy)

    # Ensure invalid attribute access raises AttributeError
    with pytest.raises(
        AttributeError, match="'TestLogger' object has no attribute 'invalid_attr'"
    ):
        _ = test_logger.invalid_attr

    # ---- LogProxy Tests ----
    log_proxy = test_logger.log  # LogProxy instance

    # Test valid log levels using LogProxy
    with caplog.at_level(logging.DEBUG):
        log_proxy.debug("Debug message")
        log_proxy.info("Info message")
        log_proxy.warning("Warning message")
        log_proxy.error("Error message")
        log_proxy.critical("Critical message")

    log_messages = [record.message for record in caplog.records]
    assert "Debug message" in log_messages
    assert "Info message" in log_messages
    assert "Warning message" in log_messages
    assert "Error message" in log_messages
    assert "Critical message" in log_messages

    # Ensure LogProxy dynamically maps valid log methods
    assert callable(log_proxy.debug)
    assert callable(log_proxy.info)
    assert callable(log_proxy.warning)
    assert callable(log_proxy.error)
    assert callable(log_proxy.critical)

    # Ensure accessing an invalid log method raises AttributeError
    with pytest.raises(AttributeError, match="No log method for level 'invalid'"):
        log_proxy.invalid("This should fail")

    # Ensure LogProxy correctly maps to the base LoggingMixin instance
    assert log_proxy.base_instance == test_logger

    class NoLoggingMethods:
        """A test class with no log methods to trigger the hasattr check failure."""

    no_logger_instance = NoLoggingMethods()
    _ = LogProxy(no_logger_instance)

    # Ensure trying to access an invalid log level raises AttributeError
    with pytest.raises(AttributeError, match="No log method for level 'invalid'"):
        log_proxy.invalid("This should fail")


def test_custom_log_pprint(caplog: pytest.LogCaptureFixture) -> None:
    """Test custom log pprint function."""
    data = {"key1": "value1", "key2": {"subkey": "subvalue"}}

    with caplog.at_level(logging.INFO):
        custom_log_pprint(data, logging.getLogger().info)

    assert "key1" in caplog.text
    assert "subkey" in caplog.text

    list_data = [
        "item1",
        {"nested_dict": "value"},
        ["nested_list_item1", "nested_list_item2"],
    ]

    with caplog.at_level(logging.INFO):
        custom_log_pprint(list_data, logging.getLogger().info)

    assert "item1" in caplog.text
    assert "nested_dict" in caplog.text
    assert "nested_list_item1" in caplog.text
    assert "nested_list_item2" in caplog.text

    mixed_data = {
        "int_value": 42,
        "float_value": 3.14159,
        "bool_true": True,
        "bool_false": False,
        "none_value": None,
    }

    with caplog.at_level(logging.INFO):
        custom_log_pprint(mixed_data, logging.getLogger().info)

    assert "42" in caplog.text  # Checking int
    assert "3.14159" in caplog.text  # Checking float
    assert "True" in caplog.text  # Checking boolean True
    assert "False" in caplog.text  # Checking boolean False
    assert "None" in caplog.text  # Checking None
