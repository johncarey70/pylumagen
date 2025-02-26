"""Tests for the `lumagen.device_manager`."""

import asyncio
import contextlib
from datetime import UTC, datetime, timedelta
from functools import partial
import logging
from typing import Any as TypingAny
from unittest.mock import ANY, AsyncMock, MagicMock, PropertyMock, patch
from zoneinfo import ZoneInfo

from lumagen.classes import DeviceContext
from lumagen.command_executor import CommandExecutor
from lumagen.constants import ConnectionStatus, DeviceStatus, EventType
from lumagen.device_manager import DeviceManager
from lumagen.messages import (
    AutoAspect,
    FullInfoV1,
    FullInfoV2,
    FullInfoV3,
    FullInfoV4,
    GameMode,
    InputBasicInfo,
    InputVideo,
    LabelQuery,
    MessageParser,
    OutputBasicInfo,
    OutputColorFormat,
    OutputMode,
    PowerState,
    Response,
    StatusAlive,
    StatusID,
)
from lumagen.models import BaseOperationalState, DeviceInfo
import pytest
import pytest_asyncio

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest_asyncio.fixture(params=["ip", "serial"])
async def device_manager(request: pytest.FixtureRequest) -> tuple[DeviceManager, str]:
    """Fixture to create a DeviceManager instance with parameterized connection type."""
    connection_type = request.param  # Extract the param correctly
    with patch.object(DeviceManager, "_run_once_at_startup", new_callable=AsyncMock):
        dm = DeviceManager(connection_type=connection_type, reconnect=True)
        dm.context.connection.executor = AsyncMock(spec=CommandExecutor)
        return dm, connection_type  # Return both the instance and the connection type


@pytest.mark.asyncio
async def test_open_connection(device_manager: tuple[DeviceManager, str]) -> None:
    """Test if the device opens a connection successfully for both IP and Serial."""
    dm, connection_type = device_manager  # Unpack the fixture return values
    with patch.object(dm, "_initialize_handler", new_callable=AsyncMock) as mock_init:
        mock_init.return_value = MagicMock()
        if connection_type == "ip":
            await dm.open(host="192.168.1.1", port=1234)
        else:
            await dm.open(port="COM3", baudrate=9600)
        assert dm.context.connection.executor is not None


@pytest.mark.asyncio
async def test_open_raises_value_error(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test if the open method raises ValueError on invalid connection parameters."""
    dm, _ = device_manager

    error_message = "Invalid connection parameters"

    # Mock `_initialize_handler` to raise ValueError
    with (
        patch.object(dm, "_initialize_handler", side_effect=ValueError(error_message)),
        patch.object(dm, "log") as mock_log,
    ):
        with pytest.raises(ValueError, match=error_message):
            await dm.open(
                invalid_param="bad_value"
            )  # Invalid params trigger ValueError

        # Ensure logging was called with the expected error message
        mock_log.error.assert_called_with("Failed to open connection: %s", ANY)


@pytest.mark.asyncio
async def test_dispatcher_property(device_manager: tuple[DeviceManager, str]) -> None:
    """Test if the dispatcher cached_property returns the correct dispatcher instance."""
    dm, _ = device_manager
    with patch.object(
        dm.context.connection, "dispatcher", new_callable=MagicMock
    ) as mock_dispatcher:
        assert dm.dispatcher == mock_dispatcher


@pytest.mark.asyncio
async def test_executor_property(device_manager: tuple[DeviceManager, str]) -> None:
    """Test if the executor cached_property behaves correctly."""
    dm, _ = device_manager

    # Case 1: Executor is initialized correctly
    with patch.object(
        dm.context.connection, "executor", new_callable=MagicMock
    ) as mock_executor:
        assert dm.executor == mock_executor

    # Case 2: Executor is None, should raise RuntimeError
    if "executor" in dm.__dict__:
        del dm.__dict__["executor"]

    with patch.object(dm, "context", new_callable=MagicMock) as mock_context:
        mock_context.connection.executor = None  # Explicitly set to None

        with pytest.raises(
            RuntimeError,
            match=r"CommandExecutor is not initialized. Ensure `open\(\)` is called first.",
        ):
            _ = dm.executor


@pytest.mark.asyncio
async def test_device_id_property(device_manager: tuple[DeviceManager, str]) -> None:
    """Test if the device_id property behaves correctly."""
    dm, _ = device_manager

    # Case 1: device_id is correctly retrieved
    with patch.object(
        type(dm.context.system_state), "device_id", new_callable=MagicMock
    ) as mock_device_id:
        assert dm.device_id == mock_device_id

    # Case 2: Ensure `device_id` raises `AttributeError` when `system_state` is None
    with patch.object(dm, "context", new_callable=MagicMock) as mock_context:
        mock_context.system_state = None

        with pytest.raises(AttributeError):
            _ = dm.device_id


@pytest.mark.asyncio
async def test_device_info_property(device_manager: tuple[DeviceManager, str]) -> None:
    """Test if the device_info property behaves correctly."""
    dm, _ = device_manager

    # Case 1: device_info is correctly retrieved
    with patch.object(
        dm.context.device_state, "info", new_callable=MagicMock
    ) as mock_device_info:
        assert dm.device_info == mock_device_info

    # Case 2: Ensure `device_info` raises `AttributeError` when `device_state` is None
    with patch.object(dm, "context", new_callable=MagicMock) as mock_context:
        mock_context.device_state = None
        with pytest.raises(AttributeError):
            _ = dm.device_info


@pytest.mark.asyncio
async def test_device_status_property(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test if the device_status property behaves correctly."""
    dm, _ = device_manager

    # Case 1: device_status is correctly retrieved
    with patch.object(
        dm.context.system_state.operational_state,
        "device_status",
        new_callable=MagicMock,
    ) as mock_device_status:
        assert dm.device_status == mock_device_status

    # Case 2: Ensure `device_status` raises `AttributeError` when `operational_state` is None
    with patch.object(dm, "context", new_callable=MagicMock) as mock_context:
        mock_context.system_state.operational_state = (
            None  # Set `operational_state` to None
        )

        with pytest.raises(AttributeError):
            _ = (
                dm.device_status
            )  # Accessing device_status should now raise AttributeError


@pytest.mark.asyncio
async def test_is_alive_property(device_manager: tuple[DeviceManager, str]) -> None:
    """Test if the is_alive property behaves correctly."""
    dm, _ = device_manager

    # Case 1: is_alive is correctly retrieved
    with patch.object(
        dm.context.system_state.operational_state, "is_alive", new_callable=MagicMock
    ) as mock_is_alive:
        assert dm.is_alive == mock_is_alive

    # Case 2: Ensure `is_alive` raises `AttributeError` when `operational_state` is None
    with patch.object(dm, "context", new_callable=MagicMock) as mock_context:
        mock_context.system_state.operational_state = None
        with pytest.raises(AttributeError):
            _ = dm.is_alive  # Should raise AttributeError


@pytest.mark.asyncio
async def test_is_connected_property(device_manager: tuple[DeviceManager, str]) -> None:
    """Test if the is_connected property behaves correctly."""
    dm, _ = device_manager

    # Case 1: is_connected is correctly retrieved
    with patch.object(
        dm.context.connection.config, "status", new_callable=MagicMock
    ) as mock_status:
        assert dm.is_connected == (mock_status == ConnectionStatus.CONNECTED)

    # Case 2: Ensure `is_connected` raises `AttributeError` when `config` is None
    with (
        patch.object(dm.context.connection, "config", None),
        pytest.raises(AttributeError),
    ):
        _ = dm.is_connected  # Should raise AttributeError


@pytest.mark.asyncio
async def test_close(device_manager: tuple[DeviceManager, str]) -> None:
    """Test if the close method properly handles connection closure."""
    dm, _ = device_manager

    # Mock necessary attributes
    dm.context.connection.closing = False
    dm.context.connection.handler = AsyncMock()
    dm.context.connection.task_manager = AsyncMock()
    dm.context.connection.config = MagicMock()
    dm.context.system_state = MagicMock()

    # Capture the handler before calling `close()`
    handler_mock = dm.context.connection.handler

    # Case 1: Normal closing process
    with patch.object(dm, "log") as mock_log:
        await dm.close()

        # Ensure log messages are recorded
        mock_log.info.assert_any_call("Closing device connection...")

        # Ensure handler is closed before it is set to None
        handler_mock.close.assert_awaited_once()

        # Ensure handler is now None
        assert dm.context.connection.handler is None

        # Ensure all tasks are canceled
        dm.context.connection.task_manager.cancel_all_tasks.assert_awaited_once()

        # Ensure status is set to DISCONNECTED
        assert dm.context.connection.config.status == ConnectionStatus.DISCONNECTED

        # Ensure system state is reset
        dm.context.system_state.reset_state.assert_called_once()

    # Case 2: If closing is already in progress, function should return early
    dm.context.connection.closing = True
    with patch.object(dm, "log_warning") as mock_log_warning:
        await dm.close()
        mock_log_warning.assert_called_with("Close operation already in progress.")

    # Case 3: Error while closing the connection handler
    dm.context.connection.closing = False
    dm.context.connection.handler = AsyncMock()
    dm.context.connection.handler.close.side_effect = ConnectionError("Close error")

    with patch.object(dm, "log_error") as mock_log_error:
        await dm.close()

        # Ensure the log message is correctly triggered, allowing any exception object
        mock_log_error.assert_called_with(
            "Error while closing connection handler: %s", ANY
        )


@pytest.mark.asyncio
async def test_send_command(device_manager: tuple[DeviceManager, str]) -> None:
    """Test if the send_command method correctly delegates to the CommandExecutor."""
    dm, _ = device_manager

    # Mock executor's send_command method
    dm.context.connection.executor = AsyncMock()

    # Case 1: Sending a single command
    command = "TEST_COMMAND"
    await dm.send_command(command)
    dm.context.connection.executor.send_command.assert_awaited_once_with(command)

    # Reset mock for next test case
    dm.context.connection.executor.send_command.reset_mock()

    # Case 2: Sending a list of commands
    command_list = ["CMD_1", "CMD_2"]
    await dm.send_command(command_list)
    dm.context.connection.executor.send_command.assert_awaited_once_with(command_list)

    # Case 3: Ensure `AttributeError` is raised when executor is None
    dm.context.connection.executor = None
    with pytest.raises(AttributeError):
        await dm.send_command("SHOULD_FAIL")


@pytest.mark.asyncio
async def test_enable_reconnect(device_manager: tuple[DeviceManager, str]) -> None:
    """Test if the enable_reconnect method updates the setting and logs correctly."""
    dm, _ = device_manager

    # Mock necessary attributes
    dm.context.connection.config = MagicMock()

    # Case 1: Enable auto-reconnect when it is currently disabled
    dm.context.connection.config.reconnect_enabled = False
    with patch.object(dm, "log") as mock_log:
        dm.enable_reconnect(True)

        # Verify reconnect_enabled was updated
        assert dm.context.connection.config.reconnect_enabled is True

        # Verify log message
        mock_log.info.assert_called_with("Auto-reconnect is now %s.", "enabled")

    # Case 2: Disable auto-reconnect when it is currently enabled
    dm.context.connection.config.reconnect_enabled = True
    with patch.object(dm, "log") as mock_log:
        dm.enable_reconnect(False)

        # Verify reconnect_enabled was updated
        assert dm.context.connection.config.reconnect_enabled is False

        # Verify log message
        mock_log.info.assert_called_with("Auto-reconnect is now %s.", "disabled")

    # Case 3: Calling with the same value should log a debug message but not update
    dm.context.connection.config.reconnect_enabled = True
    with patch.object(dm, "log") as mock_log:
        dm.enable_reconnect(True)

        # Ensure reconnect_enabled was NOT changed
        assert dm.context.connection.config.reconnect_enabled is True

        # Ensure debug log was called instead of info log
        mock_log.debug.assert_called_with("Auto-reconnect is already %s.", "enabled")

    # Case 4: Passing a non-boolean value should raise TypeError
    with pytest.raises(TypeError, match="enable must be a boolean \\(True or False\\)"):
        dm.enable_reconnect("not_a_bool")  # Invalid type


@pytest.mark.asyncio
async def test_initialize_handler(device_manager: tuple[DeviceManager, str]) -> None:
    """Test if _initialize_handler correctly initializes the appropriate handler."""
    dm, _ = device_manager

    # Mock handler initialization methods
    dm._init_serial_handler = AsyncMock(return_value="SerialHandlerMock")  # noqa: SLF001
    dm._init_ip_handler = AsyncMock(return_value="IPHandlerMock")  # noqa: SLF001

    # Case 1: Initialize serial handler
    dm.connection_type = "serial"
    handler = await dm._initialize_handler(port="COM3", baudrate=9600)  # noqa: SLF001
    dm._init_serial_handler.assert_awaited_once_with(port="COM3", baudrate=9600)  # noqa: SLF001
    assert handler == "SerialHandlerMock"

    # Reset mock for next test case
    dm._init_serial_handler.reset_mock()  # noqa: SLF001

    # Case 2: Initialize IP handler
    dm.connection_type = "ip"
    handler = await dm._initialize_handler(host="192.168.1.1", port=1234)  # noqa: SLF001
    dm._init_ip_handler.assert_awaited_once_with(host="192.168.1.1", port=1234)  # noqa: SLF001
    assert handler == "IPHandlerMock"

    # Case 3: Unsupported connection type raises ValueError
    dm.connection_type = "unsupported_type"
    with pytest.raises(
        ValueError, match="Unsupported connection type: unsupported_type"
    ):
        await dm._initialize_handler()  # noqa: SLF001


@pytest.mark.asyncio
async def test_init_serial_handler(device_manager: tuple[DeviceManager, str]) -> None:
    """Test if _init_serial_handler correctly initializes a serial connection."""
    dm, _ = device_manager

    # Mock SerialHandler
    with (
        patch(
            "lumagen.device_manager.SerialHandler.open_connection",
            new_callable=AsyncMock,
        ) as mock_open_connection,
        patch.object(dm, "log") as mock_log,
    ):
        # Case 1: Valid serial parameters
        mock_open_connection.return_value = "SerialHandlerMock"
        handler = await dm._init_serial_handler("COM3", 9600)  # noqa: SLF001
        mock_open_connection.assert_awaited_once_with(
            "COM3", 9600, dm.context.connection.dispatcher
        )  # noqa: SLF001
        mock_log.info.assert_called_with(
            "Opening serial connection to %s at %d baud", "COM3", 9600
        )  # noqa: SLF001
        assert handler == "SerialHandlerMock"

    # Case 2: Missing port should raise ValueError
    with pytest.raises(ValueError, match="Port must be provided for serial connection"):
        await dm._init_serial_handler("", 9600)  # noqa: SLF001

    # Case 3: Invalid baudrate should raise ValueError
    with pytest.raises(ValueError, match="Baudrate must be a positive integer"):
        await dm._init_serial_handler("COM3", -115200)  # noqa: SLF001

    with pytest.raises(ValueError, match="Baudrate must be a positive integer"):
        await dm._init_serial_handler("COM3", "invalid")  # noqa: SLF001


@pytest.mark.asyncio
async def test_init_ip_handler(device_manager: tuple[DeviceManager, str]) -> None:
    """Test if _init_ip_handler correctly initializes an IP connection."""
    dm, _ = device_manager

    # Mock IPHandler
    with (
        patch(
            "lumagen.device_manager.IPHandler", autospec=True
        ) as mock_ip_handler_class,
        patch.object(dm, "log") as mock_log,
    ):
        mock_ip_handler_instance = mock_ip_handler_class.return_value
        mock_ip_handler_instance.open_connection = AsyncMock()

        # Case 1: Valid IP parameters
        handler = await dm._init_ip_handler("192.168.1.10", 8080)  # noqa: SLF001
        mock_log.info.assert_called_with(
            "Opening IP connection to %s:%d", "192.168.1.10", 8080
        )
        mock_ip_handler_instance.open_connection.assert_awaited_once_with(
            "192.168.1.10", 8080
        )
        assert handler == mock_ip_handler_instance

    # Case 2: No port provided, should use `DEFAULT_IP_PORT`
    with (
        patch("lumagen.device_manager.DEFAULT_IP_PORT", 12345),
        patch(
            "lumagen.device_manager.IPHandler", autospec=True
        ) as mock_ip_handler_class,
        patch.object(dm, "log") as mock_log,
    ):
        mock_ip_handler_instance = mock_ip_handler_class.return_value
        mock_ip_handler_instance.open_connection = AsyncMock()

        handler = await dm._init_ip_handler("192.168.1.20")  # noqa: SLF001
        mock_log.info.assert_called_with(
            "Opening IP connection to %s:%d", "192.168.1.20", 12345
        )
        mock_ip_handler_instance.open_connection.assert_awaited_once_with(
            "192.168.1.20", 12345
        )
        assert handler == mock_ip_handler_instance

    # Case 3: Missing host should raise ValueError
    with pytest.raises(ValueError, match="Host must be provided for IP connection"):
        await dm._init_ip_handler("", 8080)  # noqa: SLF001


@pytest.mark.asyncio
async def test_run_once_at_startup(device_manager: tuple[DeviceManager, str]) -> None:
    """Test if _run_once_at_startup waits and calls get_all when conditions are met."""
    dm, _ = device_manager

    # Mock necessary attributes
    dm.executor = AsyncMock()

    # Mock `asyncio.sleep` to avoid real delays
    with (
        patch.object(type(dm), "is_alive", new_callable=PropertyMock) as mock_is_alive,
        patch.object(
            type(dm), "device_status", new_callable=PropertyMock
        ) as mock_device_status,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        # Simulated `is_alive` behavior: starts as False, then becomes True
        is_alive_values = [False, False, True]  # Simulate changes over time
        mock_is_alive.side_effect = (
            lambda: is_alive_values.pop(0) if is_alive_values else True
        )

        # Simulated `device_status` behavior: starts as None, then becomes ACTIVE
        device_status_values = [None, None, DeviceStatus.ACTIVE]  # Simulate changes
        mock_device_status.side_effect = (
            lambda: device_status_values.pop(0)
            if device_status_values
            else DeviceStatus.ACTIVE
        )

        # Run the function (this should loop until conditions are met)
        await dm._run_once_at_startup()  # noqa: SLF001

        # Ensure `get_all` was called once `device_status == ACTIVE`
        dm.executor.get_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_check(device_manager: tuple[DeviceManager, str]) -> None:
    """Test if _health_check correctly handles `last_data_received`, elapsed_time calculation, and `continue` condition."""

    dm, _ = device_manager

    with (
        patch.object(type(dm), "is_connected", return_value=True),
        patch.object(type(dm), "is_alive", return_value=True),
        patch.object(
            dm, "_check_device_alive", new_callable=AsyncMock
        ) as mock_check_alive,
        patch.object(dm, "_handle_disconnection", new_callable=AsyncMock),
        patch("lumagen.device_manager.LoggingMixin.disable_debug_logging"),
        patch("lumagen.device_manager.LoggingMixin.enable_debug_logging"),
    ):
        # Case 1: Ensure `_health_check()` enters `continue` condition multiple times
        dm.context.device_state.last_data_received = datetime.now(UTC) - timedelta(
            seconds=1
        )  # Recent data
        interval = 3  # Set interval longer than elapsed_time

        # Fix the mock to always ensure `elapsed_time < interval`
        with patch("lumagen.device_manager.datetime") as mock_datetime:
            mock_datetime.now.side_effect = lambda *args, **kwargs: (
                datetime.now(UTC) - timedelta(seconds=interval - 1)
            )  # Forces `elapsed_time` to always be less than `interval`

            health_check_task = asyncio.create_task(dm._health_check(interval=interval))  # noqa: SLF001

            await asyncio.sleep(
                5
            )  # Ensure multiple iterations where `_health_check()` must execute `continue`

            health_check_task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await health_check_task

        # `_check_device_alive()` should NOT have been called, meaning `continue` executed
        assert (
            mock_check_alive.await_count == 0
        ), "Expected `_check_device_alive()` to NOT be called when `elapsed_time < interval`."


@pytest.mark.asyncio
async def test_health_check_handles_disconnection(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test if `_health_check()` correctly calls `_handle_disconnection()` when `_check_device_alive()` fails."""

    dm, _ = device_manager

    with (
        patch.object(type(dm), "is_connected", return_value=True),
        patch.object(type(dm), "is_alive", return_value=True),
        patch.object(
            dm, "_check_device_alive", new_callable=AsyncMock, return_value=False
        ),
        patch.object(
            dm, "_handle_disconnection", new_callable=AsyncMock
        ) as mock_handle_disconnect,
        patch("lumagen.device_manager.LoggingMixin.disable_debug_logging"),
        patch("lumagen.device_manager.LoggingMixin.enable_debug_logging"),
    ):
        dm.context.device_state.last_data_received = datetime.now(UTC) - timedelta(
            seconds=5
        )
        interval = 3  # Set interval shorter than elapsed time
        health_check_task = asyncio.create_task(dm._health_check(interval=interval))  # noqa: SLF001

        # Wait **long enough** to guarantee `_check_device_alive()` is called
        await asyncio.sleep(
            interval + 1
        )  # Give `_health_check()` time to detect failure

        health_check_task.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await health_check_task

    # ? `_handle_disconnection()` should have been awaited **once**
    (
        mock_handle_disconnect.assert_awaited_once(),
        "Expected `_handle_disconnection()` to be called when `_check_device_alive()` fails.",
    )


@pytest.mark.asyncio
async def test_check_device_alive_no_connection(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_check_device_alive()` when there is no active connection."""
    dm, _ = device_manager
    dm.context.device_state.alive_event = asyncio.Event()

    with (
        patch.object(
            type(dm), "is_connected", new_callable=PropertyMock, return_value=False
        ),
        patch.object(dm, "log") as mock_log,
    ):
        result = await dm._check_device_alive()  # noqa: SLF001
        assert result is False
        mock_log.error.assert_any_call("No active connection to perform alive check")


@pytest.mark.asyncio
async def test_check_device_alive_success(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_check_device_alive()` when the device responds successfully."""
    dm, _ = device_manager
    dm.context.device_state.alive_event = asyncio.Event()

    with (
        patch.object(
            type(dm), "is_connected", new_callable=PropertyMock, return_value=True
        ),
        patch.object(
            type(dm), "is_alive", new_callable=PropertyMock, return_value=True
        ),  # ? Fix: Mock `is_alive`
        patch.object(dm, "send_command", new_callable=AsyncMock),
        patch.object(
            dm.context.device_state.alive_event,
            "wait",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch.object(dm, "log") as mock_log,
    ):
        result = await dm._check_device_alive()  # noqa: SLF001
        assert (
            result is True
        ), "Expected `_check_device_alive()` to return `True`, but it returned `False`."
        mock_log.debug.assert_any_call("Device responded to alive check.")


@pytest.mark.asyncio
async def test_check_device_alive_timeout(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_check_device_alive()` when the alive check times out."""
    dm, _ = device_manager
    dm.context.device_state.alive_event = asyncio.Event()

    with (
        patch.object(
            type(dm), "is_connected", new_callable=PropertyMock, return_value=True
        ),
        patch.object(dm, "send_command", new_callable=AsyncMock),
        patch.object(
            dm.context.device_state.alive_event,
            "wait",
            side_effect=asyncio.exceptions.TimeoutError(),
        ),
        patch.object(dm, "log") as mock_log,
    ):
        result = await dm._check_device_alive()  # noqa: SLF001
        assert (
            result is False
        ), "Expected `_check_device_alive()` to return `False` on timeout."
        mock_log.error.assert_called_with(
            "Alive check timed out - device may be disconnected"
        )


@pytest.mark.asyncio
async def test_check_device_alive_connection_error(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_check_device_alive()` when a connection error occurs."""
    dm, _ = device_manager
    dm.context.device_state.alive_event = asyncio.Event()

    with (
        patch.object(
            type(dm), "is_connected", new_callable=PropertyMock, return_value=True
        ),
        patch.object(
            dm,
            "send_command",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Mocked connection failure"),
        ),
        patch.object(dm, "_handle_disconnection", new_callable=AsyncMock),
        patch.object(dm, "log") as mock_log,
    ):
        result = await dm._check_device_alive()  # noqa: SLF001
        assert (
            result is False
        ), "Expected `_check_device_alive()` to return `False` on ConnectionError."

        # ? Fix: Match the actual log call format
        mock_log.error.assert_any_call("Failed to send alive message: %s", ANY)


@pytest.mark.asyncio
async def test_check_device_alive_triggers_health_check(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_check_device_alive()` triggering the `_health_check()` when `device_id.model_name` is None."""
    dm, _ = device_manager
    dm.context.device_state.alive_event = asyncio.Event()

    with (
        patch.object(
            type(dm), "is_connected", new_callable=PropertyMock, return_value=True
        ),
        patch.object(dm, "send_command", new_callable=AsyncMock),
        patch.object(
            dm.context.device_state.alive_event, "wait", new_callable=AsyncMock
        ) as mock_wait,
        patch.object(dm, "log"),
        patch.object(dm.context.system_state.device_id, "model_name", new=None),
        patch.object(dm.context.connection.task_manager, "add_task") as mock_add_task,
        patch.object(
            type(dm), "is_alive", new_callable=PropertyMock, return_value=True
        ),
        patch.object(dm, "_health_check", new_callable=AsyncMock) as mock_health_check,
    ):
        mock_wait.return_value = True
        result = await dm._check_device_alive()  # noqa: SLF001

        assert (
            result is True
        ), "Expected `_check_device_alive()` to return `True` when the device responds."

        mock_add_task.assert_called_once()

        args, kwargs = mock_add_task.call_args
        await args[0]
        assert "name" in kwargs, "Expected task name in `add_task()`"
        assert (
            kwargs["name"] == "periodic_alive_check"
        ), "Expected task name to be 'periodic_alive_check'"

        (
            mock_health_check.assert_called_once(),
            "Expected `_health_check()` to be called at least once",
        )


@pytest.mark.asyncio
async def test_handle_disconnection_already_disconnected(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_handle_disconnection()` when the device is already disconnected."""
    dm, _ = device_manager

    with (
        patch.object(
            type(dm), "is_connected", new_callable=PropertyMock, return_value=False
        ),
        patch.object(dm, "log_info") as mock_log_info,
    ):
        await dm._handle_disconnection()  # noqa: SLF001

        mock_log_info.assert_called_once_with(
            "Device is already disconnected. Skipping redundant cleanup."
        )


@pytest.mark.asyncio
async def test_handle_disconnection_closes_handler(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_handle_disconnection()` correctly closes the connection handler."""
    dm, _ = device_manager
    dm.context.connection.handler = AsyncMock()  # Create the mock

    with (
        patch.object(
            type(dm), "is_connected", new_callable=PropertyMock, return_value=True
        ),
        patch.object(
            type(dm),
            "device_id",
            new_callable=PropertyMock,
            return_value=AsyncMock(model_name="MockedModel"),
        ),  # ? Ensure `model_name` is set
        patch.object(dm, "log_warning") as mock_log_warning,
        patch.object(
            dm.context.connection.task_manager, "add_task", new_callable=AsyncMock
        ),
        patch.object(
            dm.context.connection.dispatcher, "invoke_event", new_callable=AsyncMock
        ) as mock_invoke_event,
    ):
        # Ensure `invoke_event()` actually gets called, but doesn't block execution
        mock_invoke_event.return_value = None  # This allows execution to continue

        # Store a reference to the mock before it gets reset to None
        mock_handler = dm.context.connection.handler

        await dm._handle_disconnection()  # noqa: SLF001

        # Assert `close` was awaited using the stored reference
        mock_handler.close.assert_awaited_once()

        # Ensure handler is set to None after disconnection
        assert dm.context.connection.handler is None

        # Use `assert_any_call()` to check for the expected log message
        mock_log_warning.assert_any_call("Handling disconnection...")


@pytest.mark.asyncio
async def test_handle_disconnection_close_handler_exception(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_handle_disconnection()` handles exceptions when closing the connection handler."""
    dm, _ = device_manager
    dm.context.connection.handler = AsyncMock()

    with (
        patch.object(
            type(dm), "is_connected", new_callable=PropertyMock, return_value=True
        ),
        patch.object(
            type(dm),
            "device_id",
            new_callable=PropertyMock,
            return_value=AsyncMock(model_name="MockedModel"),
        ),
        patch.object(dm, "log_error") as mock_log_error,  # Patch log_error
        patch.object(dm, "log_warning") as mock_log_warning,
        patch.object(
            dm.context.connection.dispatcher, "invoke_event", new_callable=AsyncMock
        ),
    ):
        # Mock the close() method to raise an exception
        exception_instance = ConnectionError("Mocked connection error")
        dm.context.connection.handler.close.side_effect = exception_instance

        await dm._handle_disconnection()  # noqa: SLF001

        # Check that the error was logged
        mock_log_error.assert_called_with(
            "Error while closing handler: %s", exception_instance
        )

        # Ensure handler is set to None after exception
        assert dm.context.connection.handler is None

        # Ensure warning log is present
        mock_log_warning.assert_any_call("Handling disconnection...")


@pytest.mark.asyncio
async def test_retry_alive_check_succeeds_immediately(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_retry_alive_check()` exits immediately if `_check_device_alive` returns True."""
    dm, _ = device_manager

    with (
        patch.object(
            type(dm), "is_alive", new_callable=PropertyMock, return_value=False
        ),
        patch.object(
            type(dm), "is_connected", new_callable=PropertyMock, return_value=True
        ),
        patch.object(
            dm, "_check_device_alive", new_callable=AsyncMock, return_value=True
        ),
        patch.object(dm, "log") as mock_log,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        await dm._retry_alive_check()  # noqa: SLF001

        # `_check_device_alive` should be called only once
        dm._check_device_alive.assert_awaited_once()  # noqa: SLF001

        # Ensure sleep was never called since the loop exited immediately
        mock_sleep.assert_not_awaited()

        # Ensure no warning logs about retrying
        mock_log.warning.assert_not_called()


@pytest.mark.asyncio
async def test_retry_alive_check_succeeds_after_retries(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_retry_alive_check()` retries if `_check_device_alive` initially fails but later succeeds."""
    dm, _ = device_manager
    check_alive_mock = AsyncMock(
        side_effect=[False, False, True]
    )  # Fails twice, succeeds on third call

    with (
        patch.object(
            type(dm), "is_alive", new_callable=PropertyMock, return_value=False
        ),
        patch.object(
            type(dm), "is_connected", new_callable=PropertyMock, return_value=True
        ),
        patch.object(
            dm,
            "_check_device_alive",
            new_callable=AsyncMock,
            side_effect=check_alive_mock,
        ),
        patch.object(dm, "log") as mock_log,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        await dm._retry_alive_check(interval=5)  # noqa: SLF001

        # `_check_device_alive` should be called three times before succeeding
        assert dm._check_device_alive.await_count == 3  # noqa: SLF001

        # Ensure sleep was awaited twice (before success)
        assert mock_sleep.await_count == 2
        mock_sleep.assert_awaited_with(5)

        # Ensure warning logs were triggered twice
        assert mock_log.warning.call_count == 2
        mock_log.warning.assert_any_call(
            "Device is not responding. Retrying alive check in %i seconds...", 5
        )


@pytest.mark.asyncio
async def test_retry_alive_check_fails_and_keeps_retrying(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_retry_alive_check()` retries a limited number of times when `_check_device_alive` always fails."""
    dm, _ = device_manager

    max_retries = 5
    retry_counter = 0

    async def mock_check_alive():
        nonlocal retry_counter
        retry_counter += 1
        return not retry_counter <= max_retries  # Becomes True after `max_retries`

    with (
        patch.object(
            type(dm),
            "is_alive",
            new_callable=PropertyMock,
            side_effect=lambda: retry_counter > max_retries,
        ),
        patch.object(
            type(dm), "is_connected", new_callable=PropertyMock, return_value=True
        ),
        patch.object(
            dm,
            "_check_device_alive",
            new_callable=AsyncMock,
            side_effect=mock_check_alive,
        ),
        patch.object(
            dm, "log", new_callable=MagicMock
        ) as mock_log,  # ? Use MagicMock instead of AsyncMock
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        await dm._retry_alive_check(interval=2)  # noqa: SLF001

        # Ensure `_check_device_alive` was called `max_retries + 1` times (last call to break loop)
        assert (
            dm._check_device_alive.await_count == max_retries + 1  # noqa: SLF001
        ), f"Expected {max_retries + 1} calls, got {dm._check_device_alive.await_count}"  # noqa: SLF001

        # Ensure sleep was awaited `max_retries` times
        assert (
            mock_sleep.await_count == max_retries
        ), f"Expected {max_retries} sleep calls, got {mock_sleep.await_count}"

        # Ensure warning logs were triggered `max_retries` times
        assert (
            mock_log.warning.call_count == max_retries
        ), f"Expected {max_retries} warning logs, got {mock_log.warning.call_count}"
        mock_log.warning.assert_any_call(
            "Device is not responding. Retrying alive check in %i seconds...", 2
        )


@pytest.mark.asyncio
async def test_retry_alive_check_exits_if_disconnected(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_retry_alive_check()` exits if `is_connected` becomes False."""
    dm, _ = device_manager
    check_alive_mock = AsyncMock(return_value=False)  # Always fails

    with (
        patch.object(
            type(dm), "is_alive", new_callable=PropertyMock, return_value=False
        ),
        patch.object(
            type(dm),
            "is_connected",
            new_callable=PropertyMock,
            side_effect=[
                True,
                False,
            ],  # Disconnects after the first retry instead of the second
        ),
        patch.object(
            dm,
            "_check_device_alive",
            new_callable=AsyncMock,
            side_effect=check_alive_mock,
        ),
        patch.object(dm, "log", new_callable=MagicMock) as mock_log,  # ? Mock logger
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        await dm._retry_alive_check(interval=3)  # noqa: SLF001

        # `_check_device_alive` should be called once before detecting disconnection
        assert (
            dm._check_device_alive.await_count == 1  # noqa: SLF001
        ), f"Expected 1 call, got {dm._check_device_alive.await_count}"  # noqa: SLF001

        # Ensure sleep was awaited only once before disconnection
        assert (
            mock_sleep.await_count == 1
        ), f"Expected 1 sleep call, got {mock_sleep.await_count}"

        # Ensure a log warning was triggered about disconnection
        mock_log.warning.assert_any_call("Connection lost during retry loop.")


@pytest.mark.asyncio
async def test_reconnect_loop_disabled_due_to_manual_close(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_reconnect_loop()` exits immediately if `closing=True`."""
    dm, _ = device_manager

    with (
        patch.object(
            type(dm), "is_connected", new_callable=PropertyMock, return_value=False
        ),
        patch.object(dm.context.connection, "closing", True),
        patch.object(dm, "log", new_callable=MagicMock) as mock_log,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        await dm._reconnect_loop()  # noqa: SLF001

        mock_log.info.assert_any_call("Reconnection disabled due to manual close.")
        mock_sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_reconnect_loop_disabled_due_to_config(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_reconnect_loop()` exits immediately if `reconnect_enabled=False`."""
    dm, _ = device_manager

    with (
        patch.object(
            type(dm), "is_connected", new_callable=PropertyMock, return_value=False
        ),
        patch.object(dm.context.connection, "closing", False),
        patch.object(dm.context.connection.config, "reconnect_enabled", False),
        patch.object(dm, "log", new_callable=MagicMock) as mock_log,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        await dm._reconnect_loop()  # noqa: SLF001

        mock_log.info.assert_any_call(
            "Reconnection is disabled. Not attempting reconnect."
        )
        mock_sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_reconnect_loop_successful_on_first_attempt(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_reconnect_loop()` exits immediately when `open()` succeeds on the first attempt.

    This test verifies that if `open()` successfully establishes a connection,
    `_reconnect_loop()` does not wait for retries and exits as expected.
    """

    dm, _ = device_manager
    open_mock = AsyncMock()

    with (
        patch.object(
            type(dm),
            "is_connected",
            new_callable=PropertyMock,
            side_effect=lambda: open_mock.await_count
            > 0,  # Becomes True after open() is awaited
        ),
        patch.object(dm.context.connection, "closing", False),
        patch.object(dm.context.connection.config, "reconnect_enabled", True),
        patch.object(dm, "open", new=open_mock),
        patch.object(dm, "log", new_callable=MagicMock) as mock_log,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        await dm._reconnect_loop()  # noqa: SLF001

        mock_log.info.assert_any_call("Reconnection successful.")

        mock_sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_reconnect_loop_succeeds_after_multiple_attempts(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_reconnect_loop()` retries before succeeding."""
    dm, _ = device_manager
    retry_delay = 30

    open_mock = AsyncMock(side_effect=[asyncio.exceptions.TimeoutError, None])

    with (
        patch.object(
            type(dm),
            "is_connected",
            new_callable=PropertyMock,
            side_effect=[
                False,
                False,
                False,
                True,
            ],  # Ensures two retries before success
        ),
        patch.object(dm.context.connection, "closing", False),
        patch.object(dm.context.connection.config, "reconnect_enabled", True),
        patch.object(dm, "open", new=open_mock),
        patch.object(dm, "log", new_callable=MagicMock) as mock_log,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        await dm._reconnect_loop()  # noqa: SLF001

        assert open_mock.await_count == 2  # First attempt fails, second succeeds
        mock_log.warning.assert_any_call(
            "Attempting to reconnect in %d seconds... (Attempt %d/%d)",
            retry_delay,
            1,
            ANY,
        )
        mock_log.info.assert_any_call("Reconnection successful.")
        assert mock_sleep.await_count == 1  # Only waited once before success


@pytest.mark.asyncio
async def test_reconnect_loop_fails_due_to_oserror(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_reconnect_loop()` handles `OSError` correctly by retrying before failing."""
    dm, _ = device_manager
    error_mock = OSError(101, "Network unreachable")

    with (
        patch.object(
            type(dm),
            "is_connected",
            new_callable=PropertyMock,
            side_effect=[False, False, True],
        ),
        patch.object(dm.context.connection, "closing", False),
        patch.object(dm.context.connection.config, "reconnect_enabled", True),
        patch.object(
            dm, "open", new_callable=AsyncMock, side_effect=[error_mock, None]
        ),
        patch.object(dm, "log", new_callable=MagicMock) as mock_log,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        await dm._reconnect_loop()  # noqa: SLF001

        mock_log.error.assert_any_call(
            "Reconnection failed due to network error (Errno %d - %s): %s",
            error_mock.errno,
            ANY,
            ANY,
        )
        assert mock_sleep.await_count == 1


@pytest.mark.asyncio
async def test_reconnect_loop_fails_due_to_timeout(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_reconnect_loop()` handles `asyncio.TimeoutError` correctly and retries quickly."""

    dm, _ = device_manager

    with (
        patch.object(
            type(dm),
            "is_connected",
            new_callable=PropertyMock,
            side_effect=[False, False, True],
        ),
        patch.object(dm.context.connection, "closing", False),
        patch.object(dm.context.connection.config, "reconnect_enabled", True),
        patch.object(
            dm,
            "open",
            new_callable=AsyncMock,
            side_effect=[
                asyncio.exceptions.TimeoutError,
                None,
            ],
        ),
        patch.object(dm, "log", new_callable=MagicMock) as mock_log,
        patch("asyncio.sleep", return_value=None),
    ):
        await dm._reconnect_loop()  # noqa: SLF001

        log_messages = [call[0][0] for call in mock_log.error.call_args_list]

        assert any("timed out" in message.lower() for message in log_messages)


@pytest.mark.asyncio
async def test_reconnect_loop_reaches_max_retries(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_reconnect_loop()` stops after reaching the maximum retry limit."""

    dm, _ = device_manager
    test_max_retries = 3

    with (
        patch.object(
            type(dm), "is_connected", new_callable=PropertyMock, return_value=False
        ),
        patch.object(dm.context.connection, "closing", False),
        patch.object(dm.context.connection.config, "reconnect_enabled", True),
        patch.object(
            dm, "open", new_callable=AsyncMock, side_effect=OSError("Connection failed")
        ),
        patch.object(dm, "log", new_callable=MagicMock) as mock_log,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        await dm._reconnect_loop(max_retries=test_max_retries)  # noqa: SLF001

        assert mock_log.error.call_count > 0
        mock_log.error.assert_any_call(
            "Max reconnection attempts (%d) reached. Stopping retries.",
            test_max_retries,
        )


@pytest.mark.asyncio
async def test_reconnect_loop_cancelled(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_reconnect_loop()` exits when `asyncio.CancelledError` is raised."""
    dm, _ = device_manager

    with (
        patch.object(
            type(dm), "is_connected", new_callable=PropertyMock, return_value=False
        ),
        patch.object(dm.context.connection, "closing", False),
        patch.object(dm.context.connection.config, "reconnect_enabled", True),
        patch.object(
            dm, "open", new_callable=AsyncMock, side_effect=asyncio.CancelledError
        ),
        patch.object(dm, "log", new_callable=MagicMock) as mock_log,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        with pytest.raises(asyncio.CancelledError):
            await dm._reconnect_loop()  # noqa: SLF001

        mock_log.info.assert_any_call("Reconnect loop cancelled.")
        mock_sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_reconnect_loop_handles_valueerror_in_oserror(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test `_reconnect_loop()` handles `ValueError` from `os.strerror()` correctly."""
    dm, _ = device_manager

    error_mock = OSError("Connection failed")
    error_mock.errno = (
        None  # This will force `error_code` to be -1 and trigger ValueError
    )

    with (
        patch.object(
            type(dm), "is_connected", new_callable=PropertyMock, return_value=False
        ),
        patch.object(dm.context.connection, "closing", False),
        patch.object(dm.context.connection.config, "reconnect_enabled", True),
        patch.object(dm, "open", new_callable=AsyncMock, side_effect=error_mock),
        patch.object(dm, "log", new_callable=MagicMock) as mock_log,
        patch("asyncio.sleep", new_callable=AsyncMock),
        patch("os.strerror", side_effect=ValueError),  # Force ValueError
    ):
        await dm._reconnect_loop()  # noqa: SLF001

        mock_log.error.assert_any_call(
            "Reconnection failed due to network error (Errno %d - %s): %s",
            -1,
            "UNKNOWN_ERRNO",
            "Unknown error",  # This ensures the ValueError case is properly handled
        )


@pytest.mark.asyncio
async def test_async_event_handler_invalid_event_type(device_manager: tuple) -> None:
    """Test `_async_event_handler()` logs an error when an invalid event type is received."""
    dm, _ = device_manager

    with patch.object(dm, "log", new_callable=MagicMock) as mock_log:
        await dm._async_event_handler("INVALID_EVENT", {})  # noqa: SLF001

        mock_log.error.assert_any_call(
            "Invalid event type received: %s", "INVALID_EVENT"
        )


@pytest.mark.asyncio
async def test_async_event_handler_connection_state_missing_state(
    device_manager: tuple,
) -> None:
    """Test `_async_event_handler()` logs an error when 'state' key is missing in CONNECTION_STATE event."""
    dm, _ = device_manager

    with patch.object(dm, "log", new_callable=MagicMock) as mock_log:
        await dm._async_event_handler(EventType.CONNECTION_STATE, {})  # noqa: SLF001

        mock_log.error.assert_any_call("Missing 'state' key in event_data: %s", {})


@pytest.mark.asyncio
async def test_async_event_handler_connection_state_invalid_state(
    device_manager: tuple,
) -> None:
    """Test `_async_event_handler()` handles an invalid connection state gracefully."""
    dm, _ = device_manager

    with patch.object(dm, "log", new_callable=MagicMock) as mock_log:
        await dm._async_event_handler(  # noqa: SLF001
            EventType.CONNECTION_STATE, {"state": "INVALID_STATE"}
        )

        mock_log.error.assert_any_call(
            "Invalid connection state received: %s. Defaulting to DISCONNECTED.",
            "INVALID_STATE",
        )

        assert dm.context.connection.config.status == ConnectionStatus.DISCONNECTED


@pytest.mark.asyncio
async def test_async_event_handler_connection_state_connected(
    device_manager: tuple,
) -> None:
    """Test `_async_event_handler()` handles the CONNECTED state correctly."""

    dm, _ = device_manager
    dm.context.connection.config.status = ConnectionStatus.DISCONNECTED

    mock_task_manager = MagicMock()
    mock_task_manager.cancel_task = AsyncMock()
    mock_task_manager.add_task = MagicMock()
    mock_task_manager.add_task.side_effect = lambda *args, **kwargs: None

    dm.context.connection.task_manager = mock_task_manager

    with patch.object(dm, "log", new_callable=MagicMock) as mock_log:
        event_type = EventType.CONNECTION_STATE
        event_data = {"state": "connected"}

        await dm._async_event_handler(event_type, event_data)  # noqa: SLF001

        assert dm.context.connection.config.status == ConnectionStatus.CONNECTED

        mock_log.info.assert_any_call("Updated connection status: %s", "CONNECTED")
        mock_log.info.assert_any_call(
            "Device connected. Performing initial alive check."
        )

        dm.context.connection.task_manager.cancel_task.assert_called_once_with(
            "reconnect_loop"
        )
        dm.context.connection.task_manager.add_task.assert_called_once()


@pytest.mark.asyncio
async def test_async_event_handler_connection_state_disconnected(
    device_manager: tuple,
) -> None:
    """Test `_async_event_handler()` handles the DISCONNECTED state correctly."""

    dm, _ = device_manager

    dm.context.device_state.info = "some_info"
    dm.context.connection.handler = "some_handler"
    dm.context.connection.config.reconnect_enabled = True

    mock_task_manager = MagicMock()
    mock_task_manager.cancel_task = AsyncMock()
    mock_task_manager.add_task = MagicMock()
    dm.context.connection.task_manager = mock_task_manager

    with (
        patch.object(dm, "log", new_callable=MagicMock) as mock_log,
        patch.object(dm, "_reconnect_loop", new_callable=AsyncMock),
    ):
        event_type = EventType.CONNECTION_STATE
        event_data = {"state": "disconnected"}

        await dm._async_event_handler(event_type, event_data)  # noqa: SLF001

        assert dm.context.device_state.info is None
        assert dm.context.connection.handler is None
        assert dm.context.system_state.operational_state.is_alive is False

        mock_log.warning.assert_any_call("Connection lost. is_connected set to False.")

        if dm.context.connection.config.reconnect_enabled:
            mock_task_manager.add_task.assert_called_once()


@pytest.mark.asyncio
async def test_async_event_handler_data_received_missing_response(
    device_manager: tuple,
) -> None:
    """Test `_async_event_handler()` logs an error when 'response' key is missing in DATA_RECEIVED event."""
    dm, _ = device_manager

    with patch.object(dm, "log", new_callable=MagicMock) as mock_log:
        await dm._async_event_handler(EventType.DATA_RECEIVED, {})  # noqa: SLF001

        mock_log.error.assert_any_call("Missing 'response' key in event_data: %s", {})


@pytest.mark.asyncio
async def test_async_event_handler_data_received_valid_response(
    device_manager: tuple,
) -> None:
    """Test `_async_event_handler()` processes a valid DATA_RECEIVED event correctly."""

    dm, _ = device_manager

    response_mock = {"response": "some_value"}
    dm.context.device_state.last_data_received = None

    mock_task_manager = MagicMock()
    mock_task_manager.cancel_task = AsyncMock()
    mock_task_manager.add_task = MagicMock()
    mock_task_manager.add_task.side_effect = lambda *args, **kwargs: None

    dm.context.connection.task_manager = mock_task_manager

    with (
        patch("lumagen.device_manager.datetime", wraps=datetime) as mock_datetime,
        patch.object(dm, "_handle_data_received", new_callable=AsyncMock),
    ):
        mock_datetime.now.return_value = datetime(2024, 2, 25, tzinfo=ZoneInfo("UTC"))

        await dm._async_event_handler(  # noqa: SLF001
            EventType.DATA_RECEIVED, {"response": response_mock}
        )

        assert dm.context.device_state.last_data_received == datetime(
            2024, 2, 25, tzinfo=ZoneInfo("UTC")
        )


@pytest.mark.asyncio
async def test_device_info_callback_valid_update(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test that _device_info_callback correctly updates the device info when a change occurs."""
    dm, _ = device_manager

    old_device_info = DeviceInfo(
        model_name="Lumagen Pro",
        model_number=1000,
        serial_number=12345,
        software_revision=1,
    )

    new_device_info = DeviceInfo(
        model_name="Lumagen Pro",
        model_number=1000,
        serial_number=12345,
        software_revision=2,  # Simulating a change
    )

    dm.context.device_state.info = old_device_info
    dm.log = MagicMock()

    dm._device_info_callback(new_device_info)  # noqa: SLF001

    assert dm.context.device_state.info == new_device_info
    dm.log.info.assert_called_once_with("Device Info updated successfully.")


@pytest.mark.asyncio
async def test_device_info_callback_no_change(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test that _device_info_callback does not update if the device info is unchanged."""
    dm, _ = device_manager

    device_info = DeviceInfo(
        model_name="Lumagen Pro",
        model_number=1000,
        serial_number=12345,
        software_revision=1,
    )

    dm.context.device_state.info = device_info
    dm.log = MagicMock()

    dm._device_info_callback(device_info)  # noqa: SLF001

    dm.log.debug.assert_called_once_with(
        "No changes detected in DeviceInfo, skipping update."
    )
    dm.log.info.assert_not_called()


@pytest.mark.asyncio
async def test_device_info_callback_invalid_type(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test that _device_info_callback logs an error when an invalid type is passed."""
    dm, _ = device_manager
    invalid_input = "invalid_device_info"

    dm.log = MagicMock()

    dm._device_info_callback(invalid_input)  # noqa: SLF001

    dm.log.error.assert_called_once_with(
        "Invalid device info update: Expected DeviceInfo, got %s",
        type(invalid_input).__name__,
    )


@pytest.mark.asyncio
async def test_device_info_callback_logs_debug(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test that _device_info_callback calls custom_log_pprint with the correct arguments."""
    dm, _ = device_manager

    old_device_info = DeviceInfo(
        model_name="Lumagen Pro",
        model_number=1000,
        serial_number=12345,
        software_revision=1,
    )

    new_device_info = DeviceInfo(
        model_name="Lumagen Pro",
        model_number=1000,
        serial_number=12345,
        software_revision=2,
    )

    dm.context.device_state.info = old_device_info
    dm.log = MagicMock()

    with patch("lumagen.device_manager.custom_log_pprint") as mock_pprint:
        dm._device_info_callback(new_device_info)  # noqa: SLF001

        mock_pprint.assert_called_once_with(new_device_info.model_dump(), dm.log.debug)


@pytest.mark.asyncio
async def test_handle_data_received_valid_async_handler(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test that an async handler is properly awaited and executed."""
    dm, _ = device_manager
    response: TypingAny = {"test": "data"}  # Mock response

    async def mock_handler(resp: TypingAny):
        dm.log_debug("Async handler executed with response: %s", resp)

    dm._get_message_handler = MagicMock(return_value=mock_handler)  # noqa: SLF001
    dm.log_debug = MagicMock()

    await dm._handle_data_received(response)  # noqa: SLF001

    dm._get_message_handler.assert_called_once_with(type(response))  # noqa: SLF001
    dm.log_debug.assert_any_call("Handling received response: %s", "dict")
    dm.log_debug.assert_any_call("Async handler executed with response: %s", response)


@pytest.mark.asyncio
async def test_handle_data_received_valid_sync_handler(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test that a sync handler is executed properly."""
    dm, _ = device_manager
    response: TypingAny = "mock_string"

    def mock_handler(resp: TypingAny):
        dm.log_debug("Sync handler executed with response: %s", resp)

    dm._get_message_handler = MagicMock(return_value=mock_handler)  # noqa: SLF001
    dm.log_debug = MagicMock()

    await dm._handle_data_received(response)  # noqa: SLF001

    dm._get_message_handler.assert_called_once_with(type(response))  # noqa: SLF001
    dm.log_debug.assert_any_call("Handling received response: %s", "str")
    dm.log_debug.assert_any_call("Sync handler executed with response: %s", response)


@pytest.mark.asyncio
async def test_handle_data_received_no_handler(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test that a missing handler logs a warning and does not process further."""
    dm, _ = device_manager
    response: TypingAny = 123  # Some arbitrary response type

    dm._get_message_handler = MagicMock(return_value=None)  # noqa: SLF001
    dm.log_warning = MagicMock()

    await dm._handle_data_received(response)  # noqa: SLF001

    dm._get_message_handler.assert_called_once_with(type(response))  # noqa: SLF001
    dm.log_warning.assert_called_once_with(
        "No handler found for response type: %s", "int"
    )


@pytest.mark.asyncio
async def test_handle_data_received_invalid_handler(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test that an invalid handler logs an error and does not process further."""
    dm, _ = device_manager
    response: TypingAny = [1, 2, 3]  # Example response

    dm._get_message_handler = MagicMock(return_value="invalid_handler")  # noqa: SLF001
    dm.log_error = MagicMock()

    await dm._handle_data_received(response)  # noqa: SLF001

    dm._get_message_handler.assert_called_once_with(type(response))  # noqa: SLF001
    dm.log_error.assert_called_once_with(
        "Invalid handler returned for type %s: %s", "list", "invalid_handler"
    )


@pytest.mark.asyncio
async def test_handle_data_received_handler_raises_exception(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test that if the handler raises an exception, it is logged and re-raised."""
    dm, _ = device_manager
    response: TypingAny = {"test": "error"}

    async def faulty_handler(resp: TypingAny):
        raise ValueError("Test handler failure")

    dm._get_message_handler = MagicMock(return_value=faulty_handler)  # noqa: SLF001
    dm.log_critical = MagicMock()

    with pytest.raises(ValueError, match="Test handler failure"):
        await dm._handle_data_received(response)  # noqa: SLF001

    dm._get_message_handler.assert_called_once_with(type(response))  # noqa: SLF001

    # Fix: Use `ANY` for the exception message to match actual logged call
    dm.log_critical.assert_called_once_with(
        "Error while handling response of type %s: %s", "dict", ANY
    )

    # Additional assertion to check exact log message
    logged_message = dm.log_critical.call_args[0][2]  # Extract the 3rd argument
    assert isinstance(logged_message, ValueError)
    assert str(logged_message) == "Test handler failure"


@pytest.mark.parametrize(
    ("response_type", "expected_handler"),
    [
        (AutoAspect, "_handle_operational_state"),
        (GameMode, "_handle_operational_state"),
        (OutputColorFormat, "_handle_operational_state"),
        (PowerState, "_handle_operational_state"),
        (StatusAlive, "_handle_operational_state"),
        (FullInfoV1, "_handle_full_info"),
        (FullInfoV2, "_handle_full_info"),
        (FullInfoV3, "_handle_full_info"),
        (FullInfoV4, "_handle_full_info"),
        (InputBasicInfo, "_handle_system_state"),
        (InputVideo, "_handle_system_state"),
        (OutputBasicInfo, "_handle_system_state"),
        (OutputMode, "_handle_system_state"),
        (StatusID, "_handle_system_state"),
        (LabelQuery, "_handle_label_query"),
    ],
)
def test_get_message_handler_valid_response_types(
    device_manager: tuple[DeviceManager, str],
    response_type: type,
    expected_handler: str,
) -> None:
    """Test that _get_message_handler returns the correct handler for valid response types."""
    dm, _ = device_manager

    # Mock the handler functions to verify they are correctly returned
    setattr(dm, expected_handler, MagicMock())

    handler = dm._get_message_handler(response_type)  # noqa: SLF001

    assert (
        handler is not None
    ), f"Handler should not be None for {response_type.__name__}"

    # For partial functions, check the `func` attribute
    if isinstance(handler, partial):
        assert (
            handler.func == getattr(dm, expected_handler)
        ), f"Handler for {response_type.__name__} should be a partial function of {expected_handler}"
    else:
        assert handler == getattr(
            dm, expected_handler
        ), f"Handler for {response_type.__name__} should be {expected_handler}"


def test_get_message_handler_invalid_response_type(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test that passing a non-type logs an error and returns None."""
    dm, _ = device_manager
    dm.log = MagicMock()

    response_type = "InvalidType"  # Not a type

    handler = dm._get_message_handler(response_type)  # noqa: SLF001

    assert handler is None, "Handler should be None for an invalid response type"
    dm.log.error.assert_called_once_with(
        "Invalid response_type passed to _get_message_handler: %s", response_type
    )


def test_get_message_handler_missing_handler(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test that if no handler is found, a warning is logged and None is returned."""
    dm, _ = device_manager
    dm.log = MagicMock()

    class UnknownResponse:
        pass  # A response type not in the handlers dictionary

    handler = dm._get_message_handler(UnknownResponse)  # noqa: SLF001

    assert handler is None, "Handler should be None for an unknown response type"
    dm.log.warning.assert_called_once_with(
        "No handler found for response type: %s", "UnknownResponse"
    )


@pytest.mark.asyncio
async def test_handle_operational_state_valid_field(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that _handle_operational_state correctly updates the system state when a valid response is received."""
    dm, _ = device_manager
    dm.context = DeviceContext(reconnect=False)

    response = PowerState.__new__(PowerState)
    type(response).fields = PropertyMock(return_value=["1"])
    type(response).field_device_status = PropertyMock(return_value="1")

    dm.context.system_state.update_state = MagicMock(return_value=True)
    dm.log = MagicMock()

    expected_status = BaseOperationalState.DEVICE_STATUS_MAPPING["1"]

    with patch("lumagen.device_manager.custom_log_pprint") as mock_pprint:
        dm._handle_operational_state(response)  # noqa: SLF001
        dm.context.system_state.update_state.assert_called_once()
        dm.log.debug.assert_any_call(
            "operational_state[%s] updated: %s", "device_status", expected_status
        )
        mock_pprint.assert_called_once()


@pytest.mark.asyncio
async def test_handle_operational_state_no_expected_or_missing_field(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that warnings are logged when no expected field is found or the field value is missing in the response."""
    dm, _ = device_manager
    dm.context = DeviceContext(reconnect=False)
    dm.log = MagicMock()

    class EmptyResponse(Response):
        """Mock response class with no expected field attributes."""

    response = EmptyResponse.__new__(EmptyResponse)  # Bypass __init__

    dm._handle_operational_state(response)  # noqa: SLF001

    dm.log.warning.assert_any_call("No expected field found in response: %s", response)

    # Now test the second warning: response contains a `field_` attribute but its value is None
    class MissingFieldResponse(Response):
        """Mock response class with an expected field attribute but no value."""

        field_device_status = None  # Simulates missing field value

    response = MissingFieldResponse.__new__(MissingFieldResponse)  # Bypass __init__

    dm._handle_operational_state(response)  # noqa: SLF001

    dm.log.warning.assert_any_call(
        "Missing '%s' in response: %s", "field_device_status", response
    )


@pytest.mark.asyncio
async def test_handle_operational_state_sets_is_alive(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that _handle_operational_state sets the alive_event when receiving a StatusAlive response."""
    dm, _ = device_manager
    dm.context = DeviceContext(reconnect=False)
    dm.log = MagicMock()

    response = StatusAlive.__new__(StatusAlive)
    type(response).fields = PropertyMock(return_value=["Ok"])
    type(response).field_is_alive = PropertyMock(return_value=True)

    dm.context.device_state.alive_event = MagicMock()

    dm._handle_operational_state(response)  # noqa: SLF001

    dm.context.device_state.alive_event.set.assert_called_once()


@pytest.mark.asyncio
async def test_handle_operational_state_no_update_needed(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that _handle_operational_state logs a debug message when no update is needed."""
    dm, _ = device_manager
    dm.context = DeviceContext(reconnect=False)
    dm.log = MagicMock()

    response = PowerState.__new__(PowerState)
    type(response).fields = PropertyMock(return_value=["1"])
    type(response).field_device_status = PropertyMock(return_value="1")

    dm.context.system_state.update_state = MagicMock(return_value=False)

    dm._handle_operational_state(response)  # noqa: SLF001

    dm.context.system_state.update_state.assert_called_once()
    dm.log.debug.assert_called_with("Operational State unchanged, no update needed.")


@pytest.mark.asyncio
async def test_handle_system_state_update_status_id(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Test that _handle_system_state correctly updates the system state using a StatusID response."""
    dm, _ = device_manager
    dm.context = DeviceContext(reconnect=False)
    dm.log = MagicMock()

    parsed = MessageParser("!S01,RadiancePro,101524,1018,001351")
    response = StatusID(parsed)

    state_attr = "device_id"

    def mock_update_state(**kwargs):
        if state_attr in kwargs:
            dm.context.system_state.state_models[state_attr] = kwargs[state_attr]
        return True

    dm.context.system_state.update_state = MagicMock(side_effect=mock_update_state)

    with patch("lumagen.device_manager.custom_log_pprint") as mock_pprint:
        dm._handle_system_state(response, state_attr)  # noqa: SLF001

        dm.context.system_state.update_state.assert_called_once_with(
            **{state_attr: response}
        )
        assert dm.context.system_state.state_models[state_attr] == response

        expected_dict = response.model_dump()
        mock_pprint.assert_called_once_with(expected_dict, dm.log.debug)


@pytest.mark.asyncio
async def test_handle_system_state_no_update_status_id(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that _handle_system_state logs correctly when no update occurs for a StatusID response."""

    dm, _ = device_manager
    dm.context = DeviceContext(reconnect=False)
    dm.log = MagicMock()

    parsed = MessageParser("!S01,Lumagen Pro,2,1000,12345")
    response = StatusID(parsed)

    state_attr = "device_id"
    dm.context.system_state.update_state = MagicMock(return_value=False)

    dm._handle_system_state(response, state_attr)  # noqa: SLF001

    dm.context.system_state.update_state.assert_called_once_with(
        **{state_attr: response}
    )
    dm.log.debug.assert_called_with(
        "%s unchanged, no update needed.", state_attr.replace("_", " ").title()
    )


@pytest.mark.asyncio
async def test_handle_full_info_update(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that _handle_full_info correctly updates full device information."""

    dm, _ = device_manager
    dm.context = DeviceContext(reconnect=False)
    dm.log = MagicMock()

    parsed = MessageParser("!I21,0,000,0000,0,0,178,178,-,0,000f,0,0,000,1080,178")
    response = FullInfoV1(parsed)

    version = "V1"
    dm.context.system_state.update_full_info = MagicMock(return_value=True)

    with patch("lumagen.device_manager.custom_log_pprint") as mock_pprint:
        await dm._handle_full_info(response, version)  # noqa: SLF001

        dm.context.system_state.update_full_info.assert_called_once_with(response)
        dm.log.info.assert_called_once_with("Full Info %s Updated", version)
        mock_pprint.assert_called_once_with(
            dm.context.system_state.full_info.model_dump(), dm.log.debug
        )


@pytest.mark.asyncio
async def test_handle_full_info_no_update(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that _handle_full_info logs correctly when no update occurs."""

    dm, _ = device_manager
    dm.context = DeviceContext(reconnect=False)
    dm.log = MagicMock()

    parsed = MessageParser("!I21,0,000,0000,0,0,178,178,-,0,000f,0,0,000,1080,178")
    response = FullInfoV1(parsed)

    version = "V1"
    dm.context.system_state.update_full_info = MagicMock(return_value=False)

    await dm._handle_full_info(response, version)  # noqa: SLF001

    dm.context.system_state.update_full_info.assert_called_once_with(response)
    dm.log.debug.assert_called_once_with("Full Info unchanged, no update needed.")


@pytest.mark.asyncio
async def test_handle_full_info_invalid_response(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that _handle_full_info handles invalid response types correctly."""

    dm, _ = device_manager
    dm.context = DeviceContext(reconnect=False)
    dm.log = MagicMock()

    response = "InvalidResponse"
    version = "V1"

    await dm._handle_full_info(response, version)  # noqa: SLF001

    dm.log.error.assert_called_once_with(
        "Invalid response type for full info update: %s", type(response).__name__
    )


@pytest.mark.asyncio
async def test_handle_full_info_device_event_set(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that _handle_full_info clears the device event flag if set."""

    dm, _ = device_manager
    dm.context = DeviceContext(reconnect=False)
    dm.log = MagicMock()

    parsed = MessageParser("!I21,0,000,0000,0,0,178,178,-,0,000f,0,0,000,1080,178")
    response = FullInfoV1(parsed)

    version = "V1"
    dm.context.system_state.update_full_info = MagicMock(return_value=True)
    dm.context.device_state.device_event = MagicMock()
    dm.context.device_state.device_event.is_set.return_value = True
    dm.context.device_state.device_event.clear = MagicMock()

    with patch("lumagen.device_manager.custom_log_pprint"):
        await dm._handle_full_info(response, version)  # noqa: SLF001

        dm.context.system_state.update_full_info.assert_called_once_with(response)
        dm.context.device_state.device_event.clear.assert_called_once()

        # Ensure both debug calls exist, instead of enforcing exactly one call
        debug_calls = [call[0][0] for call in dm.log.debug.call_args_list]
        assert "Clearing device event flag." in debug_calls


@pytest.mark.asyncio
async def test_handle_full_info_trigger_system_state_refresh(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that _handle_full_info triggers a full system state refresh when the device is active."""

    dm, _ = device_manager
    dm.context = DeviceContext(reconnect=False)
    dm.log = MagicMock()

    parsed = MessageParser("!I21,0,000,0000,0,0,178,178,-,0,000f,0,0,000,1080,178")
    response = FullInfoV1(parsed)

    version = "V1"
    dm.context.system_state.update_full_info = MagicMock(return_value=True)
    dm.context.device_state.device_event.is_set = MagicMock(return_value=False)
    dm.context.connection = MagicMock()
    dm.context.connection.executor = AsyncMock()

    with (
        patch("lumagen.device_manager.custom_log_pprint"),
        patch.object(
            type(dm),
            "device_status",
            new_callable=PropertyMock,
            return_value=DeviceStatus.ACTIVE,
        ),
    ):
        await dm._handle_full_info(response, version)  # noqa: SLF001

        dm.context.system_state.update_full_info.assert_called_once_with(response)
        dm.log.debug.assert_any_call("Triggering full system state refresh.")
        dm.context.connection.executor.get_all.assert_awaited_once_with(
            exclude_status=True
        )


@pytest.mark.asyncio
async def test_handle_full_info_network_error(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that _handle_full_info logs an error when system state refresh fails due to network issues."""

    dm, _ = device_manager
    dm.context = DeviceContext(reconnect=False)
    dm.log = MagicMock()

    parsed = MessageParser("!I21,0,000,0000,0,0,178,178,-,0,000f,0,0,000,1080,178")
    response = FullInfoV1(parsed)

    version = "V1"
    dm.context.system_state.update_full_info = MagicMock(return_value=True)
    dm.context.device_state.device_event.is_set = MagicMock(return_value=False)

    dm.context.connection = MagicMock()
    dm.context.connection.executor.get_all = AsyncMock(
        side_effect=TimeoutError("Network timeout")
    )

    with (
        patch("lumagen.device_manager.custom_log_pprint"),
        patch.object(
            type(dm),
            "device_status",
            new_callable=PropertyMock,
            return_value=DeviceStatus.ACTIVE,
        ),
    ):
        await dm._handle_full_info(response, version)  # noqa: SLF001

        dm.context.connection.executor.get_all.assert_called_once()

        dm.log.error.assert_any_call(
            "System state refresh failed due to network issue: %s", ANY
        )


@pytest.mark.asyncio
async def test_handle_label_query_valid_response(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that a valid LabelQuery response updates the label mapping."""
    dm, _ = device_manager
    dm.log = MagicMock()
    dm.show_labels = AsyncMock()

    message = "#ZQS1A1!S1A,HDMI1"
    parsed = MessageParser(message)
    response = LabelQuery(parsed)

    await dm._handle_label_query(response)  # noqa: SLF001

    assert dm.labels["A1"] == "HDMI1"
    dm.log.debug.assert_called_with(
        "Label Updated: Index %s -> Name '%s'", "A1", "HDMI1"
    )


@pytest.mark.asyncio
async def test_handle_label_query_invalid_data(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that a LabelQuery response with invalid data logs a warning and does not update labels."""
    dm, _ = device_manager
    dm.log = MagicMock()

    response = MagicMock(spec=LabelQuery)
    response.field_label_index = None
    response.field_label_name = None

    await dm._handle_label_query(response)  # noqa: SLF001

    dm.log.warning.assert_called_with("Invalid label data in response: %s", response)
    assert not dm.labels


@pytest.mark.asyncio
async def test_handle_label_query_malformed_response(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that a malformed LabelQuery response logs a warning and does not update labels."""
    dm, _ = device_manager
    dm.log = MagicMock()

    # Create a mock LabelQuery response missing required attributes
    response = MagicMock()
    del response.field_label_index  # Ensure attribute does not exist
    del response.field_label_name  # Ensure attribute does not exist

    await dm._handle_label_query(response)  # Call function  # noqa: SLF001

    # Verify the warning log is triggered
    dm.log.warning.assert_called_with(
        "Malformed LabelQuery response received: %s", response
    )

    # Ensure labels are not updated
    assert not dm.labels


@pytest.mark.asyncio
async def test_handle_label_query_all_labels_received(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that when 64 labels are received, it triggers label display."""
    dm, _ = device_manager
    dm.log = MagicMock()
    dm.show_labels = AsyncMock()

    # Populate labels dictionary with 63 entries
    dm.labels = {f"A{i}": f"Label{i}" for i in range(63)}

    # Add the 64th label
    message = "#ZQS1A63!S1A,HDMI64"
    parsed = MessageParser(message)
    response = LabelQuery(parsed)

    await dm._handle_label_query(response)  # Call function  # noqa: SLF001

    # Ensure log message was triggered
    dm.log.debug.assert_called_with("All 64 labels received, triggering label display.")

    # Ensure show_labels() was awaited
    dm.show_labels.assert_awaited_once()


@pytest.mark.asyncio
async def test_show_all(device_manager: tuple[DeviceManager, str]) -> None:
    """Verify that show_all logs system state information correctly."""

    dm, _ = device_manager
    dm.context = DeviceContext(reconnect=False)
    dm.log = MagicMock()

    # Mock system state and its `to_dict()` method
    dm.context.system_state.to_dict = MagicMock(return_value={"mocked": "data"})

    with patch("lumagen.device_manager.custom_log_pprint") as mock_pprint:
        await dm.show_all()  # Call the method

        # Ensure `to_dict()` is called on the system state
        dm.context.system_state.to_dict.assert_called_once()

        # Ensure `custom_log_pprint` is called with the expected arguments
        mock_pprint.assert_called_once_with({"mocked": "data"}, dm.log.info)


@pytest.mark.asyncio
async def test_show_info_with_device_info(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that show_info logs and displays device information correctly when available."""

    dm, _ = device_manager
    dm.log = MagicMock()

    # Mock the property correctly
    mock_device_info = MagicMock()
    mock_device_info.model_dump.return_value = {"model": "MockDevice", "version": "1.0"}

    with (
        patch.object(
            type(dm),
            "device_info",
            new_callable=PropertyMock,
            return_value=mock_device_info,
        ),
        patch("lumagen.device_manager.custom_log_pprint") as mock_pprint,
    ):
        await dm.show_info()  # Call the method

        # Ensure log.info() is called before displaying info
        dm.log.info.assert_any_call("Displaying device information:")

        # Ensure `custom_log_pprint` is called with the correct data
        mock_pprint.assert_called_once_with(
            {"model": "MockDevice", "version": "1.0"}, dm.log.info
        )


@pytest.mark.asyncio
async def test_show_info_no_device_info(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that show_info logs a warning when device information is unavailable."""

    dm, _ = device_manager
    dm.log = MagicMock()

    # Correctly mock device_info as None using PropertyMock
    with patch.object(
        type(dm), "device_info", new_callable=PropertyMock, return_value=None
    ):
        await dm.show_info()  # Call the method

        # Ensure warning is logged
        dm.log.warning.assert_called_once_with("No device information available.")


@pytest.mark.asyncio
async def test_show_labels_with_labels(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that show_labels correctly logs and categorizes labels when they exist."""

    dm, _ = device_manager
    dm.log = MagicMock()

    # Mocking labels
    dm.labels = {
        "A0": "HDMI A0",
        "A1": "HDMI A1",
        "A2": "HDMI A2",
        "A3": "HDMI A3",
        "A4": "HDMI A4",
        "A5": "HDMI A5",
        "A6": "HDMI A6",
        "A7": "HDMI A7",
        "A8": "HDMI A8",
        "A9": "HDMI A9",
        "B0": "HDMI B0",
        "B1": "HDMI B1",
        "B2": "HDMI B2",
        "B3": "HDMI B3",
        "B4": "HDMI B4",
        "B5": "HDMI B5",
        "B6": "HDMI B6",
        "B7": "HDMI B7",
        "B8": "HDMI B8",
        "B9": "HDMI B9",
        "C0": "HDMI C0",
        "C1": "HDMI C1",
        "C2": "HDMI C2",
        "C3": "HDMI C3",
        "C4": "HDMI C4",
        "C5": "HDMI C5",
        "C6": "HDMI C6",
        "C7": "HDMI C7",
        "C8": "HDMI C8",
        "C9": "HDMI C9",
        "D0": "HDMI D0",
        "D1": "HDMI D1",
        "D2": "HDMI D2",
        "D3": "HDMI D3",
        "D4": "HDMI D4",
        "D5": "HDMI D5",
        "D6": "HDMI D6",
        "D7": "HDMI D7",
        "D8": "HDMI D8",
        "D9": "HDMI D9",
        "10": "Custom0",
        "11": "Custom1",
        "12": "Custom2",
        "13": "Custom3",
        "14": "Custom4",
        "15": "Custom5",
        "16": "Custom6",
        "17": "Custom7",
        "20": "CMS0",
        "21": "CMS1",
        "22": "CMS2",
        "23": "CMS3",
        "24": "CMS4",
        "25": "CMS5",
        "26": "CMS6",
        "27": "CMS7",
        "30": "Style0",
        "31": "Style1",
        "32": "Style2",
        "33": "Style3",
        "34": "Style4",
        "35": "Style5",
        "36": "Style6",
        "37": "Style7",
    }

    with patch("lumagen.device_manager.custom_log_pprint") as mock_pprint:
        await dm.show_labels()  # Call the method

        # Ensure labels are sorted and displayed
        mock_pprint.assert_called_once_with(
            {
                key: dm.labels[key]
                for key in sorted(dm.labels.keys(), key=lambda k: (k[0].isdigit(), k))
            },
            dm.log.info,
        )

        # Ensure lists are categorized correctly
        assert dm.source_list == [
            dm.labels[key] for key in sorted(dm.labels.keys()) if key.startswith("A")
        ]
        assert dm.cms_list == [
            dm.labels[key] for key in sorted(dm.labels.keys()) if key.startswith("2")
        ]
        assert dm.style_list == [
            dm.labels[key] for key in sorted(dm.labels.keys()) if key.startswith("3")
        ]

        # Ensure logs contain expected information
        dm.log.info.assert_any_call("Displaying sorted port labels:")
        dm.log.info.assert_any_call("Source List: %s", dm.source_list)
        dm.log.info.assert_any_call("CMS List: %s", dm.cms_list)
        dm.log.info.assert_any_call("Style List: %s", dm.style_list)


@pytest.mark.asyncio
async def test_show_labels_no_labels(device_manager: tuple[DeviceManager, str]) -> None:
    """Verify that show_labels logs a warning when no labels are available."""

    dm, _ = device_manager
    dm.log = MagicMock()

    dm.labels = {}  # No labels

    await dm.show_labels()  # Call the method

    # Ensure warning is logged
    dm.log.warning.assert_called_once_with("No labels available to display.")


@pytest.mark.asyncio
async def test_show_source_list_with_data(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that show_source_list correctly logs and displays the source list when available."""

    dm, _ = device_manager
    dm.log = MagicMock()

    # Mock source list with HDMI sources
    dm.source_list = [
        "HDMI A0",
        "HDMI A1",
        "HDMI A2",
        "HDMI A3",
        "HDMI A4",
        "HDMI A5",
        "HDMI A6",
        "HDMI A7",
        "HDMI A8",
        "HDMI A9",
    ]

    with patch("lumagen.device_manager.custom_log_pprint") as mock_pprint:
        await dm.show_source_list()  # Call the method

        # Ensure logs contain expected information
        dm.log.debug.assert_called_once_with("Displaying source list:")

        # Ensure correct display
        mock_pprint.assert_called_once_with(dm.source_list, dm.log.debug)


@pytest.mark.asyncio
async def test_show_source_list_empty(
    device_manager: tuple[DeviceManager, str],
) -> None:
    """Verify that show_source_list logs a warning when the source list is empty."""

    dm, _ = device_manager
    dm.log = MagicMock()

    dm.source_list = []  # Empty list

    await dm.show_source_list()  # Call the method

    # Ensure warning is logged
    dm.log.warning.assert_called_once_with("Source list is empty or not initialized.")


@pytest.mark.asyncio
async def test_show_power_state(device_manager: tuple[DeviceManager, str]) -> None:
    """Verify that show_power_state logs the correct power state."""

    dm, _ = device_manager
    dm.log = MagicMock()

    # Mock the device_status property
    with patch.object(
        dm.__class__,
        "device_status",
        new_callable=PropertyMock,
        return_value=DeviceStatus.ACTIVE,
    ):
        await dm.show_power_state()  # Call the method

        # Ensure the correct log message is printed
        dm.log.info.assert_called_once_with(
            "Power State = %s", str(DeviceStatus.ACTIVE)
        )
