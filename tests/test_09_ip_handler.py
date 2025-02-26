"""Tests for the `lumagen.connection.ip_handler`."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from lumagen.connection import ConnectionStatus, EventType, IPHandler
import pytest

pytestmark = pytest.mark.filterwarnings(
    "ignore:coroutine 'AsyncMockMixin._execute_mock_call' was never awaited"
)


@pytest.fixture
def mock_dispatcher() -> Mock:
    """Fixture for a mock event dispatcher."""
    mock_dispatcher = Mock()
    mock_dispatcher.invoke_event = AsyncMock()
    return mock_dispatcher


@pytest.fixture
def ip_handler(mock_dispatcher) -> IPHandler:
    """Fixture for an IPHandler instance with a mock dispatcher."""
    return IPHandler(dispatcher=mock_dispatcher)


@pytest.fixture
def mock_streams() -> tuple[AsyncMock, Mock]:
    """Fixture for mock asyncio reader and writer streams."""
    reader = AsyncMock()
    writer = Mock()  # `write()` is not async, so use Mock instead of AsyncMock
    writer.drain = AsyncMock()  # `drain()` is async, so keep it as AsyncMock
    writer.wait_closed = AsyncMock()
    return reader, writer


@pytest.mark.asyncio
async def test_open_connection(mocker, ip_handler, mock_streams) -> None:
    """Test opening an IP connection."""
    mock_open_connection = mocker.patch(
        "asyncio.open_connection", new_callable=AsyncMock
    )
    mock_open_connection.return_value = mock_streams

    await ip_handler.open_connection("127.0.0.1", 8080)

    assert ip_handler.reader is mock_streams[0]
    assert ip_handler.writer is mock_streams[1]

    mock_open_connection.assert_called_once_with("127.0.0.1", 8080)
    ip_handler._dispatcher.invoke_event.assert_called_with(  # noqa: SLF001
        EventType.CONNECTION_STATE,
        state=ConnectionStatus.CONNECTED,
        message="Connected to 127.0.0.1:8080",
    )


@pytest.mark.asyncio
async def test_send(ip_handler, mock_streams, mocker) -> None:
    """Ensure send writes data when connected."""
    mock_open_connection = mocker.patch(
        "asyncio.open_connection", new_callable=AsyncMock
    )
    mock_open_connection.return_value = mock_streams

    await ip_handler.open_connection("127.0.0.1", 8080)  # Ensure writer is set

    await ip_handler.send(b"test data")

    ip_handler.writer.write.assert_called_once_with(b"test data")
    await ip_handler.writer.drain()


@pytest.mark.asyncio
async def test_send_no_connection(ip_handler, caplog: pytest.LogCaptureFixture) -> None:
    """Test attempting to send data with no active connection."""
    await ip_handler.send(b"test data")

    assert "No IP connection available to send data" in caplog.text
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_close_normal() -> None:
    """Test `IPHandler.close()` when the writer closes successfully."""

    handler = IPHandler()
    handler._task_manager = MagicMock()  # noqa: SLF001
    handler._task_manager.cancel_all_tasks = AsyncMock()  # noqa: SLF001
    handler._task_manager.wait_for_all_tasks = AsyncMock()  # noqa: SLF001
    handler.writer = MagicMock()
    handler.writer.wait_closed = AsyncMock()
    handler.log = MagicMock()

    with patch(
        "lumagen.connection.BaseHandler.close", new_callable=AsyncMock
    ) as mock_super_close:
        await handler.close()

    mock_super_close.assert_awaited_once()
    handler.writer.close.assert_called_once()
    handler.writer.wait_closed.assert_awaited_once()
    handler.log.warning.assert_not_called()


@pytest.mark.asyncio
async def test_close_writer_timeout() -> None:
    """Test closing IPHandler when writer times out."""

    handler = IPHandler()
    handler._task_manager = MagicMock()  # noqa: SLF001
    handler._task_manager.cancel_all_tasks = AsyncMock()  # noqa: SLF001
    handler._task_manager.wait_for_all_tasks = AsyncMock()  # noqa: SLF001
    handler.writer = MagicMock()

    # Mock `wait_closed()` to raise `TimeoutError`
    handler.writer.wait_closed = AsyncMock(side_effect=asyncio.TimeoutError)
    handler.log = MagicMock()

    with patch(
        "lumagen.connection.BaseHandler.close", new_callable=AsyncMock
    ) as mock_super_close:
        await handler.close()

    mock_super_close.assert_awaited_once()
    handler.writer.close.assert_called_once()
    handler.writer.wait_closed.assert_awaited_once()
    handler.log.warning.assert_called_with("Timeout while waiting for writer to close.")


@pytest.mark.asyncio
async def test_close_no_writer() -> None:
    """Test closing IPHandler when no writer is available."""

    handler = IPHandler()
    handler._task_manager = MagicMock()  # noqa: SLF001
    handler._task_manager.cancel_all_tasks = AsyncMock()  # noqa: SLF001
    handler._task_manager.wait_for_all_tasks = AsyncMock()  # noqa: SLF001
    handler.writer = None  # Simulates no writer being available
    handler.log = MagicMock()

    with patch(
        "lumagen.connection.BaseHandler.close", new_callable=AsyncMock
    ) as mock_super_close:
        await handler.close()

    mock_super_close.assert_awaited_once()
    handler.log.warning.assert_not_called()  # No warnings should be logged
