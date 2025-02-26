"""Tests for the `lumagen.classes` module."""

import asyncio

from lumagen.classes import (
    CallbackManager,
    ConnectionConfig,
    ConnectionManager,
    DeviceContext,
    DeviceState,
)
from lumagen.constants import ConnectionStatus
from lumagen.dispatcher import Dispatcher
from lumagen.utils import TaskManager


def test_callback_manager() -> None:
    """Test CallbackManager default initialization."""
    callback_manager = CallbackManager()

    assert callback_manager.on_event is None
    assert callback_manager.pending_response is None


def test_connection_config() -> None:
    """Test ConnectionConfig default values."""
    config = ConnectionConfig()

    assert config.status == ConnectionStatus.DISCONNECTED
    assert config.reconnect_enabled is True
    assert config.connection_params == {}


def test_connection_manager() -> None:
    """Test ConnectionManager initialization."""
    manager = ConnectionManager()

    assert isinstance(manager.config, ConnectionConfig)
    assert manager.handler is None
    assert isinstance(manager.task_manager, TaskManager)
    assert isinstance(manager.dispatcher, Dispatcher)
    assert manager.executor is None
    assert manager.closing is False


def test_device_state() -> None:
    """Test DeviceState default initialization."""
    state = DeviceState()

    assert state.info is None
    assert state.last_data_received is None
    assert isinstance(state.alive_event, asyncio.Event)
    assert isinstance(state.device_event, asyncio.Event)


def test_device_context() -> None:
    """Test DeviceContext initialization and methods."""
    context = DeviceContext(reconnect=True)

    assert isinstance(context.connection, ConnectionManager)
    assert isinstance(context.device_state, DeviceState)
    assert context.connection.config.reconnect_enabled is True
    assert isinstance(
        context.system_state, object
    )  # Ensures SystemState is initialized

    # Test get_connection_status
    assert context.get_connection_status() == str(ConnectionStatus.DISCONNECTED)

    # Test __repr__
    repr_output = repr(context)
    assert "DeviceContext" in repr_output
    assert "ConnectionManager" in repr_output
    assert "DeviceState" in repr_output
