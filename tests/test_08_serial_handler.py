"""Tests for the `lumagen.connection.serial_handler`."""

import asyncio
import contextlib
from unittest.mock import AsyncMock, Mock

from lumagen.connection import EventType, SerialHandler
from lumagen.constants import ConnectionStatus
import pytest
from serial_asyncio_fast import SerialTransport


@pytest.fixture
def mock_dispatcher() -> AsyncMock:
    """Fixture for creating a mock dispatcher."""
    return AsyncMock()


@pytest.fixture
def serial_handler(mock_dispatcher) -> SerialHandler:
    """Fixture for initializing a SerialHandler instance with a mock dispatcher."""
    return SerialHandler(dispatcher=mock_dispatcher)


@pytest.fixture
def mock_transport() -> Mock:
    """Fixture for creating a mock serial transport with predefined attributes."""
    transport = Mock(spec=SerialTransport)
    transport.serial.port = "COM3"
    transport.serial.baudrate = 9600
    transport.serial.reset_input_buffer = Mock()
    transport.serial.reset_output_buffer = Mock()
    return transport


@pytest.mark.asyncio
async def test_open_connection(mocker: Mock) -> None:  # noqa: D103
    mock_create_connection = AsyncMock(spec=AsyncMock)
    mocker.patch(
        "serial_asyncio_fast.create_serial_connection", new=mock_create_connection
    )
    mock_transport = Mock()
    mock_protocol = Mock()
    mock_create_connection.return_value = (mock_transport, mock_protocol)

    protocol = await SerialHandler.open_connection("COM3", 9600)

    assert protocol is mock_protocol
    mock_create_connection.assert_called_once()


@pytest.mark.asyncio
async def test_connection_made(serial_handler, mock_transport) -> None:  # noqa: D103
    serial_handler.connection_made(mock_transport)

    # Ensure transport is correctly set
    assert serial_handler.transport == mock_transport
    mock_transport.serial.reset_input_buffer.assert_called_once()
    mock_transport.serial.reset_output_buffer.assert_called_once()

    serial_handler._dispatcher.invoke_event.assert_called_with(  # noqa: SLF001
        EventType.CONNECTION_STATE,
        state=ConnectionStatus.CONNECTED,
        message="Connected to COM3",
    )

    # Ensure any created tasks are properly cleaned up
    await asyncio.sleep(0)  # Yield control so async tasks execute
    for task in asyncio.all_tasks():
        if task is not asyncio.current_task():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


@pytest.mark.asyncio
async def test_connection_lost(serial_handler) -> None:  # noqa: D103
    await serial_handler.connection_lost(Exception("Test error"))
    serial_handler._dispatcher.invoke_event.assert_awaited()  # noqa: SLF001
    assert serial_handler.transport is None
    serial_handler._dispatcher.invoke_event.assert_called_with(  # noqa: SLF001
        EventType.CONNECTION_STATE,
        state=ConnectionStatus.DISCONNECTED,
        message="Test error",
    )


@pytest.mark.asyncio
async def test_data_received(serial_handler) -> None:  # noqa: D103
    serial_handler.reader = Mock()
    serial_handler.data_received(b"test data")
    serial_handler.reader.feed_data.assert_called_once_with(b"test data")


@pytest.mark.asyncio
async def test_send(serial_handler, mock_transport) -> None:  # noqa: D103
    serial_handler.transport = mock_transport
    await serial_handler.send(b"test")
    mock_transport.write.assert_called_once_with(b"test")


@pytest.mark.asyncio
async def test_send_no_transport(
    serial_handler, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that send logs an error when transport is None and does not write data."""
    serial_handler.transport = None

    await serial_handler.send(b"test command")

    assert "Cannot send data: No active connection." in caplog.text


@pytest.mark.asyncio
async def test_open_connection_type_error(mocker) -> None:
    """Test that open_connection raises a TypeError when an invalid result is returned."""
    mocker.patch(
        "serial_asyncio_fast.create_serial_connection",
        return_value="invalid result",  # Simulate an unexpected return value
    )

    with pytest.raises(TypeError, match="Expected \\(transport, protocol\\) tuple"):
        await SerialHandler.open_connection(port="COM3", baudrate=9600)


def test_extract_serial_transport_details_attribute_error() -> None:
    """Test that extract_serial_transport_details handles missing attributes gracefully."""

    class MockTransport:
        """Mock transport object without a 'serial' attribute to trigger AttributeError."""

    transport = MockTransport()

    details = SerialHandler.extract_serial_transport_details(transport)

    assert details == {"error": "Could not extract transport details"}


def test_extract_serial_transport_details_returns_none() -> None:
    """Test that extract_serial_transport_details returns None when serial exists but has no valid attributes."""

    class MockSerial:
        """Mock serial object with no valid attributes but does not raise an AttributeError."""

        port = None
        baudrate = None
        bytesize = None
        parity = None
        stopbits = None
        timeout = None
        xonxoff = None
        rtscts = None
        dsrdtr = None

    class MockTransport:
        serial = MockSerial()  # Serial exists but has no useful attributes

    transport = MockTransport()

    details = SerialHandler.extract_serial_transport_details(transport)

    assert details is None
