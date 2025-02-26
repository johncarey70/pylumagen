"""Core Classes for Device and Connection Management.

This module defines essential classes that manage device state, connections,
and system-wide event handling.

Main Components:
----------------
- `DeviceContext`: Encapsulates device state and connection management.
- `DeviceState`: Represents the current operational state of the device.
- `ConnectionManager`: Handles connection states and communication handlers.
- `CallbackManager`: Manages asynchronous event callbacks.

Dependencies:
-------------
- Relies on `models.py` for `DeviceInfo` structure.
- Uses `utils.py` for task management and logging.
- Interfaces with `state_manager.py` for system state updates.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from . import DeviceInfo
from .command_executor import CommandExecutor
from .connection import IPHandler, SerialHandler
from .constants import ConnectionStatus
from .dispatcher import Dispatcher
from .state_manager import SystemState
from .utils import TaskManager


@dataclass
class CallbackManager:
    """Manages event callbacks and pending responses."""

    on_event: Callable | None = None
    pending_response: asyncio.Future | None = None


@dataclass
class ConnectionConfig:
    """Holds connection settings and parameters."""

    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    reconnect_enabled: bool = True
    connection_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionManager:
    """Manages the connection state and communication handlers for the device."""

    config: ConnectionConfig = field(default_factory=ConnectionConfig)
    handler: SerialHandler | IPHandler = None
    task_manager: TaskManager = TaskManager()
    dispatcher: Dispatcher = Dispatcher()
    executor: CommandExecutor = None
    closing: bool = False


@dataclass
class DeviceState:
    """Represents the current state and status of the device.

    Attributes:
        info (DeviceInfo): Stores device-specific information.
        last_data_received (float): Timestamp of the last received data from the device.
        alive_event (asyncio.Event): Event to track the alive status of the device.
        device_event (asyncio.Event): Event for general device state changes.

    """

    info: DeviceInfo = None
    last_data_received: datetime = None
    alive_event: asyncio.Event = asyncio.Event()
    device_event: asyncio.Event = asyncio.Event()


class DeviceContext:
    """Encapsulate device state and connection management."""

    def __init__(self, reconnect: bool) -> None:
        """Initialize the DeviceContext instance."""
        self.connection = ConnectionManager(
            config=ConnectionConfig(reconnect_enabled=reconnect)
        )
        self.device_state = DeviceState()
        self.system_state = SystemState()

    def get_connection_status(self) -> str:
        """Return the current connection status."""
        return str(self.connection.config.status)

    def __repr__(self) -> str:
        """Return a string representation of the DeviceContext."""
        return (
            f"DeviceContext(connection={self.connection}, "
            f"device_state={self.device_state}, system_state={self.system_state})"
        )
