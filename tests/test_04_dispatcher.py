"""Tests for the `lumagen.dispatcher` module."""

from unittest.mock import AsyncMock, Mock

from lumagen.constants import EventType
from lumagen.dispatcher import Dispatcher
import pytest


@pytest.mark.asyncio
async def test_register_listener_and_invoke_event() -> None:
    """Test that a listener is registered and invoked correctly."""
    dispatcher = Dispatcher()
    mock_callback = Mock()

    dispatcher.register_listener(EventType.CONNECTION_STATE, mock_callback)
    await dispatcher.invoke_event(EventType.CONNECTION_STATE, state="connected")

    mock_callback.assert_called_once_with(
        EventType.CONNECTION_STATE, {"state": "connected"}
    )


@pytest.mark.asyncio
async def test_register_async_listener_and_invoke() -> None:
    """Test that an async listener is registered and invoked correctly."""
    dispatcher = Dispatcher()
    mock_callback = AsyncMock()

    dispatcher.register_listener(EventType.DATA_RECEIVED, mock_callback)
    await dispatcher.invoke_event(EventType.DATA_RECEIVED, data="test")

    mock_callback.assert_awaited_once_with(EventType.DATA_RECEIVED, {"data": "test"})


@pytest.mark.asyncio
async def test_remove_listener() -> None:
    """Test that a listener is removed properly."""
    dispatcher = Dispatcher()
    mock_callback = Mock()

    dispatcher.register_listener(EventType.DATA_RECEIVED, mock_callback)
    dispatcher.remove_listener(EventType.DATA_RECEIVED, mock_callback)

    await dispatcher.invoke_event(EventType.DATA_RECEIVED, message="error")
    mock_callback.assert_not_called()


@pytest.mark.asyncio
async def test_clear_listeners() -> None:
    """Test that all listeners are cleared correctly."""
    dispatcher = Dispatcher()
    mock_callback_1 = Mock()
    mock_callback_2 = Mock()

    dispatcher.register_listener(EventType.DATA_RECEIVED, mock_callback_1)
    dispatcher.register_listener(EventType.DATA_RECEIVED, mock_callback_2)

    dispatcher.clear_listeners(EventType.DATA_RECEIVED)
    await dispatcher.invoke_event(EventType.DATA_RECEIVED, data="test")

    mock_callback_1.assert_not_called()
    mock_callback_2.assert_not_called()


@pytest.mark.asyncio
async def test_clear_all_listeners() -> None:
    """Test that all event listeners are cleared correctly."""
    dispatcher = Dispatcher()
    mock_callback_1 = Mock()
    mock_callback_2 = Mock()

    dispatcher.register_listener(EventType.CONNECTION_STATE, mock_callback_1)
    dispatcher.register_listener(EventType.DATA_RECEIVED, mock_callback_2)

    dispatcher.clear_listeners()  # Remove all listeners
    await dispatcher.invoke_event(EventType.CONNECTION_STATE, state="connected")
    await dispatcher.invoke_event(EventType.DATA_RECEIVED, data="test")

    mock_callback_1.assert_not_called()
    mock_callback_2.assert_not_called()
