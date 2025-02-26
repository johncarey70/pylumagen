"""Utility Classes for Logging, Task Management, and Buffer Handling.

This module consolidates commonly used utilities, including logging mixins,
task management for asynchronous execution, and buffer handling for data streams.

Main Components:
----------------
- `LoggingMixin`: Provides structured logging with dynamic class-based identifiers.
- `TaskManager`: Manages asyncio tasks safely, allowing for controlled execution.
- `BufferManager`: Handles efficient message buffering and extraction.
- `custom_log_pprint`: Formats structured logging for nested data structures.

Dependencies:
-------------
- Uses `asyncio` for non-blocking task execution.
- Implements `logging` for unified application-wide logging.
"""

import asyncio
from collections.abc import Coroutine
from enum import Enum
import inspect
import logging
from typing import Any, Protocol


class BufferManager:
    """Manage a data buffer in a streaming context.

    This class provides utility methods for handling a buffer, extracting messages,
    and checking for specific conditions like prefixes or terminators.
    """

    def __init__(self, terminator: str = "\n", ignored_prefixes: tuple = ()) -> None:
        r"""Initialize the buffer manager with a terminator and ignored prefixes.

        Args:
            terminator (str): The character or string that marks the end of a message.
                              Defaults to "\n".
            ignored_prefixes (tuple): A tuple of prefixes to ignore in the buffer.
                                      Defaults to an empty tuple.

        """
        self.terminator = terminator
        self.ignored_prefixes = ignored_prefixes
        self.buffer = ""

    def append(self, data: str) -> None:
        """Append data to the buffer.

        Args:
            data (str): The data to append to the buffer.

        """
        self.buffer += data

    def extract_message(self) -> str:
        """Extract a complete message from the buffer and update the buffer.

        Removes the message if it ends with the terminator.

        Returns:
            str: The extracted message with leading and trailing whitespace stripped.
                 Returns an empty string if no complete message is available.

        """
        end_idx = self.buffer.find(self.terminator) + len(self.terminator)
        if end_idx > 0:
            message = self.buffer[:end_idx]
            self.buffer = self.buffer[end_idx:]
            return message.strip()
        return ""

    def clear(self) -> None:
        """Clear the buffer by removing all its contents."""
        self.buffer = ""

    def starts_with(self, prefixes: tuple) -> bool:
        """Check if the buffer starts with any of the specified prefixes.

        Args:
            prefixes (tuple): A tuple of prefixes to check.

        Returns:
            bool: True if the buffer starts with one of the prefixes, False otherwise.

        """
        return self.buffer.lower().startswith(
            tuple(prefix.lower() for prefix in prefixes)
        )

    def ends_with_terminator(self) -> bool:
        """Check if the buffer ends with the terminator.

        Returns:
            bool: True if the buffer ends with the terminator, False otherwise.

        """
        return self.buffer.endswith(self.terminator)

    def is_empty(self) -> bool:
        """Check if the buffer is empty or contains only whitespace.

        Returns:
            bool: True if the buffer is empty or contains only whitespace, False otherwise.

        """
        return not self.buffer.strip()

    def adjust_buffer(self, keywords: list[str]) -> None:
        """Modify the buffer to start from the first detected keyword."""
        buffer_lower = self.buffer.lower()
        for keyword in keywords:
            start_idx = buffer_lower.find(keyword.lower())

            if start_idx != -1:
                # Special case: If buffer is exactly "#!", do not modify it
                if (
                    keyword == "!"
                    and start_idx == 1
                    and self.buffer[start_idx - 1] == "#"
                    and len(self.buffer) == 2
                ):
                    return

                # Adjust the buffer to start from the keyword
                self.buffer = self.buffer[start_idx:]
                return


class LogProtocol(Protocol):
    """Protocol defining standard logging methods for structured logging."""

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message.

        Used for detailed debugging information useful during development.
        """

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an informational message.

        Used for general application events that highlight progress or state changes.
        """

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message.

        Used to indicate potential issues or unexpected behavior that isn't critical.
        """

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an error message.

        Used for serious issues that might affect the application's execution.
        """

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a critical error message.

        Used for severe errors that may lead to application failure.
        """


class LoggingMixin:
    """Mixin class providing dynamic logging with classname."""

    _disable_debug_logging = False

    log: LogProtocol

    def __init__(self) -> None:
        """Initialize the logger for the current module."""
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__module__)

    def log_debug(self, message: str, *args: Any) -> None:
        """Log a debug message only if debug logging is enabled."""
        if not LoggingMixin._disable_debug_logging:
            self.logger.debug(
                message,
                *args,
                extra={"classname": self.__class__.__name__},
                stacklevel=3,
            )

    def log_info(self, message: str, *args: Any) -> None:
        """Log an info message."""
        self.logger.info(
            message, *args, extra={"classname": self.__class__.__name__}, stacklevel=3
        )

    def log_warning(self, message: str, *args: Any) -> None:
        """Log a warning message."""
        self.logger.warning(
            message, *args, extra={"classname": self.__class__.__name__}, stacklevel=3
        )

    def log_error(self, message: str, *args: Any) -> None:
        """Log an error message."""
        self.logger.error(
            message, *args, extra={"classname": self.__class__.__name__}, stacklevel=3
        )

    def log_critical(self, message: str, *args: Any) -> None:
        """Log a critical message."""
        self.logger.critical(
            message, *args, extra={"classname": self.__class__.__name__}, stacklevel=3
        )

    @classmethod
    def disable_debug_logging(cls) -> None:
        """Disable all debug logs globally."""
        cls._disable_debug_logging = True

    @classmethod
    def enable_debug_logging(cls) -> None:
        """Enable debug logging globally."""
        cls._disable_debug_logging = False

    def __getattr__(self, name: str) -> Any:
        """Provide dynamic access to the log property."""
        if name == "log":
            return LogProxy(self)
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )


class LogProxy:
    """Proxy to dynamically map log levels to LoggingMixin methods."""

    def __init__(self, base_instance: Any) -> None:
        """Initialize the log proxy with the given base instance."""
        self.base_instance = base_instance

    def __getattr__(self, log_level: str) -> Any:
        """Dynamically map log levels to corresponding methods in LoggingMixin."""
        log_method_name = f"log_{log_level}"
        try:
            return getattr(self.base_instance, log_method_name)
        except AttributeError as e:
            raise AttributeError(f"No log method for level '{log_level}'") from e

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message."""
        getattr(self.base_instance, "log_debug")(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an informational message."""
        getattr(self.base_instance, "log_info")(msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message."""
        getattr(self.base_instance, "log_warning")(msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an error message."""
        getattr(self.base_instance, "log_error")(msg, *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a critical message."""
        getattr(self.base_instance, "log_critical")(msg, *args, **kwargs)


class TaskManager(LoggingMixin):
    """Manage and track multiple asyncio tasks safely."""

    def __init__(self) -> None:
        """Initialize the task manager with an empty dictionary of tasks."""
        super().__init__()
        self.active_tasks: dict[str, asyncio.Task] = {}

    def add_task(self, coro: Coroutine[None, None, None], name: str) -> asyncio.Task:
        """Add a coroutine as a task with a name. Ignore if the task already exists."""
        if not isinstance(name, str):
            raise TypeError(f"Task name must be a string, got {type(name).__name__}")

        if name in self.active_tasks:
            self.log_warning("Task '%s' is already running. Skipping duplicate.", name)
            return self.active_tasks[name]

        task = asyncio.create_task(coro, name=name)

        task.add_done_callback(lambda t: self._handle_task_completion(t, name))
        self.active_tasks[name] = task
        return task

    def _handle_task_completion(self, task: asyncio.Task, name: str) -> None:
        """Remove completed tasks and log any errors or cancellations."""
        self.active_tasks.pop(name, None)

        if task.cancelled():
            self.log.info("Task '%s' was cancelled.", name)
        elif task.exception():
            self.log.error("Task '%s' raised an exception: %s", name, task.exception())

    async def cancel_task(self, name: str) -> None:
        """Cancel a specific task by name."""
        task = self.active_tasks.pop(name, None)

        if not task:
            return

        self.log.info("Cancelling task: %s", name)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            self.log.info("Task '%s' was successfully cancelled.", name)
            raise

    async def cancel_all_tasks(self) -> None:
        """Cancel all tasks managed by the TaskManager."""

        # Log the caller module, class, and function.
        stack = inspect.stack()[1]
        caller_module = inspect.getmodule(stack.frame).__name__.split(".")[1]
        caller_class = (
            stack.frame.f_locals["self"].__class__.__name__
            if "self" in stack.frame.f_locals
            else "Unknown"
        )

        caller_function = stack.function

        self.log.info(
            "TaskManager.cancel_all_tasks() called by: %s.%s.%s",
            caller_module,
            caller_class,
            caller_function,
        )

        for task in self.active_tasks.values():
            task.cancel()

        results = await asyncio.gather(
            *self.active_tasks.values(), return_exceptions=True
        )

        self.active_tasks.clear()

        self.log.info("All tasks have been cancelled and cleared.")

        for result in results:
            if isinstance(result, asyncio.CancelledError):
                raise result

    async def wait_for_all_tasks(self) -> None:
        """Wait for the completion of all managed tasks."""
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks.values(), return_exceptions=True)

    def get_task(self, name: str) -> asyncio.Task | None:
        """Check if a task with a given name is currently running."""
        return self.active_tasks.get(name)


def custom_log_pprint(
    data: dict | list | str, log_method: callable, indent: int = 0
) -> None:
    """Pretty-print dictionaries and lists using the specified logging method."""

    def format_data(value: dict | list | str | float | bool, level: int) -> str:
        """Format nested data (dicts, lists, and other types) with proper indentation."""
        if isinstance(value, dict):
            return format_nested_dict(value, level)

        if isinstance(value, list):
            return format_list(value, level)

        if isinstance(value, str):
            return f"'{value}'"

        return str(value)

    def format_nested_dict(d: dict, level: int = 0) -> str:
        """Recursively format nested dictionaries with indentation."""
        spaces = "    " * level
        formatted = f"{spaces}{{\n"
        for key, value in d.items():
            formatted += f"{spaces}    '{key}': {format_data(value, level + 1)},\n"
        formatted += f"{spaces}}}"
        return formatted

    def format_list(lst: list, level: int = 0) -> str:
        """Recursively format lists with correct indentation (exactly 4 spaces per item)."""
        spaces = "    " * level
        item_indent = "    " * (level + 1)

        formatted = f"{spaces}[\n"
        for item in lst:
            formatted += f"{item_indent}{format_data(item, 0)},\n"
        formatted += f"{spaces}]"
        return formatted

    formatted_output = (
        format_list(data, indent)
        if isinstance(data, list)
        else format_data(data, indent)
    )

    log_method("\n" + formatted_output)


def process_command_or_keypress(
    buffer: str, my_dict: dict[str, str]
) -> tuple[str | None, str | None, bool]:
    """Check if the buffer matches a command or keypress in the dictionary.

    Args:
        buffer (str): The current buffer to check.
        my_dict (dict): The dictionary of commands or keypress mappings.

    Returns:
        tuple: (key, value, is_keypress) where:
            - key (str or None): The matched command/key.
            - value (str or None): The associated value for the matched command/key.
            - is_keypress (bool): True if it's a keypress, False otherwise.

    """
    for key, value in my_dict.items():
        if buffer.startswith("#" + key):  # Command starts with "#" + key
            return key, value, False
        if buffer.startswith(key):  # Keypress starts directly with key
            return key, value, True
    return None, None, False


def flatten_dictionary(d: dict, merged=None) -> dict:
    """Recursively flattens a nested dictionary, merging all values into a single dictionary.

    Args:
        d (dict): The dictionary to flatten.
        merged (dict, optional): The dictionary to store merged values. Defaults to a new dict.

    Returns:
        dict: A sorted flattened dictionary with all nested values merged.

    """
    if merged is None:
        merged = {}

    for key, value in d.items():
        if isinstance(value, dict):
            flatten_dictionary(value, merged)
            continue

        # Convert all Enum instances to their string representation
        if isinstance(value, Enum):
            value = str(value)  # Uses the `__str__()` method of the Enum

        if key not in merged and value is not None:
            merged[key] = value

    return dict(sorted(merged.items()))
