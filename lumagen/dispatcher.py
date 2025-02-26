"""Module: Dispatcher.

This module provides an asynchronous `Dispatcher` class for handling event-driven
communication between different components in a system. It enables registering, emitting,
and removing event listeners dynamically, supporting both synchronous and asynchronous
callback functions.

To ensure type safety and prevent invalid event names, the module defines an `EventType`
enum for all valid event types.

Usage Example:
--------------
from dispatcher import Dispatcher, EventType

async def handle_connection(event_type, event_data):
    print(f"Handling {event_type}: {event_data}")

dispatcher = Dispatcher()
dispatcher.register_listener(EventType.CONNECTION_STATE, handle_connection)
asyncio.run(dispatcher.invoke_event(EventType.CONNECTION_STATE, state="connected"))

Methods:
-------
- register_listener(event_type, callback): Registers an event listener.
- invoke_event(event_type, **event_data): Triggers an event and calls registered listeners.
- remove_listener(event_type, callback): Removes a specific listener.
- clear_listeners(event_type=None): Clears listeners for a given event type or all events.

"""

import asyncio
from collections.abc import Callable, Coroutine

from .constants import EventType


class Dispatcher:
    """A dispatcher for managing event-driven communication between components."""

    def __init__(self) -> None:
        """Initialize the Dispatcher with an empty event registry."""
        self._listeners: dict[EventType, list[Callable | Coroutine]] = {}

    def register_listener(
        self, event_type: EventType, callback: Callable | Coroutine
    ) -> None:
        """Register a callback function for a specific event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    async def invoke_event(self, event_type: EventType, **event_data) -> None:
        """Invoke an event and call all registered listeners asynchronously."""
        if event_type in self._listeners:
            tasks = []
            for callback in self._listeners[event_type]:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(callback(event_type, event_data))  # Collect coroutine
                else:
                    callback(event_type, event_data)  # Run sync function immediately

            if tasks:
                await asyncio.gather(*tasks)  # Execute all async handlers concurrently

    def remove_listener(
        self, event_type: EventType, callback: Callable | Coroutine
    ) -> None:
        """Remove a specific listener for an event type."""
        if event_type in self._listeners:
            self._listeners[event_type].remove(callback)
            if not self._listeners[event_type]:
                del self._listeners[event_type]

    def clear_listeners(self, event_type: EventType | None = None) -> None:
        """Remove all listeners for a specific event type or all events."""
        if event_type:
            self._listeners.pop(event_type, None)
        else:
            self._listeners.clear()
