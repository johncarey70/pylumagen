"""Tests for the `lumagen.command_executor`."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from lumagen.command_executor import (
    AspectControl,
    AspectControlMixin,
    CommandExecutor,
    LabelControl,
    LabelControlMixin,
    MessageControl,
    MessageControlMixin,
    NavigationControl,
    NavigationControlMixin,
    PowerControl,
    PowerControlMixin,
    RemoteControl,
    RemoteControlMixin,
)
from lumagen.constants import (
    DEVICE_DISPLAY_CLEAR,
    DEVICE_DISPLAY_INPUT_ASPECT,
    DEVICE_FAN_SPEED,
    DEVICE_HOTPLUG,
    DeviceStatus,
)
import pytest


@pytest.fixture
def mock_connection_handler() -> AsyncMock:
    """Fixture to mock the connection handler."""
    return AsyncMock()


@pytest.fixture
def mock_device_manager() -> MagicMock:
    """Fixture to mock the device manager."""
    return MagicMock()


@pytest.fixture
def command_executor(mock_connection_handler, mock_device_manager) -> CommandExecutor:
    """Fixture to create a CommandExecutor instance with mocked dependencies."""
    return CommandExecutor(mock_connection_handler, mock_device_manager)


@pytest.fixture
def aspect_control() -> AspectControl:
    """Fixture to create an AspectControl instance with a mocked sender."""
    sender_mock = AsyncMock()
    return AspectControl(sender_mock)


@pytest.fixture
def aspect_control_mixin() -> AspectControlMixin:
    """Fixture to create an AspectControlMixin instance with a mocked AspectControl."""
    mixin = AspectControlMixin()
    mixin.aspect = AsyncMock()
    return mixin


@pytest.fixture
def label_control() -> LabelControl:
    """Fixture to create a LabelControl instance with mocked sender and device manager."""
    sender_mock = AsyncMock()
    sender_mock.log.info = MagicMock()
    sender_mock.log.debug = MagicMock()
    sender_mock.log.warning = MagicMock()
    device_manager_mock = MagicMock()
    return LabelControl(sender_mock, device_manager_mock)


@pytest.fixture
def label_control_mixin() -> LabelControlMixin:
    """Fixture to create a LabelControlMixin instance with a mocked LabelControl."""
    mixin = LabelControlMixin()
    mixin.label = AsyncMock()
    return mixin


@pytest.fixture
def message_control() -> MessageControl:
    """Fixture to create a MessageControl instance with mocked sender and device manager."""
    sender_mock = AsyncMock()
    device_manager_mock = MagicMock()
    return MessageControl(sender_mock, device_manager_mock)


@pytest.fixture
def message_control_mixin() -> MessageControlMixin:
    """Fixture to create a MessageControlMixin instance with a mocked MessageControl."""
    mixin = MessageControlMixin()
    mixin.message = AsyncMock()
    return mixin


@pytest.fixture
def navigation_control() -> NavigationControl:
    """Fixture to create a NavigationControl instance with a mocked sender."""
    sender_mock = AsyncMock()
    return NavigationControl(sender_mock)


@pytest.fixture
def navigation_control_mixin() -> NavigationControlMixin:
    """Fixture to create a NavigationControlMixin instance with a mocked NavigationControl."""
    mixin = NavigationControlMixin()
    mixin.navigation = AsyncMock()
    return mixin


@pytest.fixture
def power_control() -> PowerControl:
    """Fixture to create a PowerControl instance with a mocked sender."""
    sender_mock = AsyncMock()
    return PowerControl(sender_mock)


@pytest.fixture
def power_control_mixin() -> PowerControlMixin:
    """Fixture to create a PowerControlMixin instance with a mocked PowerControl."""
    mixin = PowerControlMixin()
    mixin.power = AsyncMock()
    return mixin


@pytest.fixture
def remote_control() -> RemoteControl:
    """Fixture to create a RemoteControl instance with a mocked sender and device manager."""
    sender_mock = AsyncMock()
    device_manager_mock = MagicMock()
    return RemoteControl(sender_mock, device_manager_mock)


@pytest.fixture
def remote_control_mixin() -> RemoteControlMixin:
    """Fixture to create a RemoteControlMixin instance with a mocked RemoteControl."""
    mixin = RemoteControlMixin()
    mixin.remote = AsyncMock()
    return mixin


@pytest.mark.asyncio
async def test_send_command(
    command_executor, mock_connection_handler, caplog: pytest.LogCaptureFixture
) -> None:
    """Test sending valid and invalid commands through the command executor."""
    # Test single command
    await command_executor.send_command("TEST_COMMAND")
    mock_connection_handler.queue_command.assert_called_once_with(["TEST_COMMAND"])

    # Reset mock
    mock_connection_handler.queue_command.reset_mock()

    # Test list of commands
    command_list = ["CMD1", "CMD2", "CMD3"]
    await command_executor.send_command(command_list)
    mock_connection_handler.queue_command.assert_called_once_with(
        ["CMD1", "CMD2", "CMD3"]
    )

    # Reset mock
    mock_connection_handler.queue_command.reset_mock()

    # Test None as command
    await command_executor.send_command(None)
    mock_connection_handler.queue_command.assert_not_called()

    # Test empty string
    await command_executor.send_command("")
    assert "No valid commands to send after filtering." in caplog.text
    mock_connection_handler.queue_command.assert_not_called()

    # Reset log capture and mock
    caplog.clear()
    mock_connection_handler.queue_command.reset_mock()

    # Test string with spaces
    await command_executor.send_command("   ")
    assert "No valid commands to send after filtering." in caplog.text
    mock_connection_handler.queue_command.assert_not_called()

    # Reset log capture and mock
    caplog.clear()
    mock_connection_handler.queue_command.reset_mock()

    # Test empty list
    await command_executor.send_command([])
    assert "No valid commands to send after filtering." in caplog.text
    mock_connection_handler.queue_command.assert_not_called()

    # Reset log capture and mock
    caplog.clear()
    mock_connection_handler.queue_command.reset_mock()

    # Test list with empty strings
    await command_executor.send_command(["", "   "])
    assert "No valid commands to send after filtering." in caplog.text
    mock_connection_handler.queue_command.assert_not_called()

    # Test error handling
    mock_connection_handler.queue_command.side_effect = AttributeError(
        "Mock AttributeError"
    )
    await command_executor.send_command("TEST_COMMAND")
    assert "Attribute error in send_command()" in caplog.text

    mock_connection_handler.queue_command.side_effect = TypeError("Mock TypeError")
    await command_executor.send_command("TEST_COMMAND")
    assert "Type error in send_command()" in caplog.text

    mock_connection_handler.queue_command.side_effect = asyncio.exceptions.TimeoutError(
        "Mock TimeoutError"
    )
    await command_executor.send_command("TEST_COMMAND")
    assert "Timeout while sending command" in caplog.text

    mock_connection_handler.queue_command.side_effect = ConnectionError(
        "Mock ConnectionError"
    )
    await command_executor.send_command("TEST_COMMAND")
    assert "Connection error while sending command" in caplog.text

    mock_connection_handler.queue_command.side_effect = RuntimeError(
        "Mock RuntimeError"
    )
    await command_executor.send_command("TEST_COMMAND")
    assert "Runtime error while sending command" in caplog.text


@pytest.mark.asyncio
async def test_send_remote_command(
    command_executor, caplog: pytest.LogCaptureFixture
) -> None:
    """Test sending a remote command through the command executor."""
    command_executor.sender.send_command = AsyncMock()

    # Test valid remote command
    await command_executor.send_remote_command("EXIT")
    command_executor.sender.send_command.assert_called()

    # Test invalid remote command
    caplog.clear()
    await command_executor.send_remote_command("INVALID_COMMAND")
    assert (
        "Command not found for value: INVALID_COMMAND (searched by key: remote)"
        in caplog.text
    )


@pytest.mark.asyncio
async def test_aspect_control_commands(aspect_control) -> None:
    """Test all aspect ratio commands in AspectControl class."""
    aspect_control.sender.send_remote_command = AsyncMock()

    aspect_commands = {
        "source_aspect_4x3": "4:3",
        "source_aspect_16x9": "16:9",
        "source_aspect_1_85": "1.85",
        "source_aspect_1_90": "1.90",
        "source_aspect_2_00": "2.00",
        "source_aspect_2_20": "2.20",
        "source_aspect_2_35": "2.35",
        "source_aspect_2_40": "2.40",
        "source_aspect_lbox": "LBOX",
    }

    for method, command in aspect_commands.items():
        await getattr(aspect_control, method)()
        aspect_control.sender.send_remote_command.assert_called_with(command)
        aspect_control.sender.send_remote_command.reset_mock()


@pytest.mark.asyncio
async def test_aspect_control_mixin_commands(aspect_control_mixin) -> None:
    """Test all aspect ratio commands in AspectControlMixin class."""
    aspect_commands = {
        "source_aspect_4x3": "4x3",
        "source_aspect_16x9": "16x9",
        "source_aspect_1_85": "1.85",
        "source_aspect_1_90": "1.90",
        "source_aspect_2_00": "2.00",
        "source_aspect_2_20": "2.20",
        "source_aspect_2_35": "2.35",
        "source_aspect_2_40": "2.40",
        "source_aspect_lbox": "LBOX",
    }

    for method in aspect_commands:
        await getattr(aspect_control_mixin, method)()
        getattr(aspect_control_mixin.aspect, method).assert_called_once()
        getattr(aspect_control_mixin.aspect, method).reset_mock()


@pytest.mark.asyncio
async def test_label_control_get_labels(label_control) -> None:
    """Test retrieving all input labels in LabelControl class."""
    label_control.sender.send_command = AsyncMock()
    await label_control.get_labels()
    label_control.sender.send_command.assert_called()


@pytest.mark.asyncio
async def test_label_control_set_labels(label_control) -> None:
    """Test setting input labels in LabelControl class."""
    label_control.sender.send_command = AsyncMock()
    await label_control.set_labels()
    label_control.sender.send_command.assert_called()


@pytest.mark.asyncio
async def test_label_control_mixin_get_labels(label_control_mixin) -> None:
    """Test retrieving all input labels in LabelControlMixin class."""
    await label_control_mixin.get_labels()
    label_control_mixin.label.get_labels.assert_called_once()


@pytest.mark.asyncio
async def test_label_control_mixin_set_labels(label_control_mixin) -> None:
    """Test setting input labels in LabelControlMixin class."""
    await label_control_mixin.set_labels()
    label_control_mixin.label.set_labels.assert_called_once()


@pytest.mark.asyncio
async def test_label_control_set_labels_no_commands(label_control) -> None:
    """Test setting labels when no valid commands are generated."""
    label_control.sender.send_command = AsyncMock()
    invalid_port_config = {"Z9": "Invalid Port"}  # No valid keys

    await label_control.set_labels(invalid_port_config)

    label_control.sender.log.warning.assert_called_once_with(
        "No valid label commands generated."
    )
    label_control.sender.send_command.assert_not_called()


@pytest.mark.asyncio
async def test_message_control_display_message(message_control) -> None:
    """Test displaying a message when device is active."""
    message_control.sender.send_command = AsyncMock()
    message_control.dm.device_status = DeviceStatus.ACTIVE
    await message_control.display_message(5, "Test Message")
    message_control.sender.send_command.assert_called_once()


@pytest.mark.asyncio
async def test_message_control_display_message_invalid_timeout(message_control) -> None:
    """Test display message with an invalid timeout value."""
    with pytest.raises(ValueError, match="Invalid timeout: 10"):
        await message_control.display_message(10, "Test Message")


@pytest.mark.asyncio
async def test_message_control_display_message_invalid_message(message_control) -> None:
    """Test display message with an invalid empty message."""
    with pytest.raises(ValueError, match="Message must be a non-empty string."):
        await message_control.display_message(5, "")


@pytest.mark.asyncio
async def test_message_control_display_message_filtered_empty(message_control) -> None:
    """Test display message where the sanitized message results in an empty string."""
    message_control.dm.device_status = DeviceStatus.ACTIVE

    with patch.object(message_control, "log", new_callable=MagicMock) as mock_log:
        await message_control.display_message(5, "\x01\x02\x03\x04\x05")
        mock_log.warning.assert_called_once_with(
            "Filtered message is empty after character sanitization."
        )


@pytest.mark.asyncio
async def test_message_control_display_message_device_inactive(message_control) -> None:
    """Test attempting to display a message when device is not active."""
    message_control.dm.device_status = DeviceStatus.STANDBY
    with patch.object(message_control, "log", new_callable=MagicMock) as mock_log:
        await message_control.display_message(5, "Test Message")
        mock_log.warning.assert_called_once_with(
            "Cannot display message. Device is not in ACTIVE mode."
        )


@pytest.mark.asyncio
async def test_message_control_clear_message(message_control) -> None:
    """Test clearing a message when device is active."""
    message_control.sender.send_command = AsyncMock()
    message_control.dm.device_status = DeviceStatus.ACTIVE
    await message_control.clear_message()
    message_control.sender.send_command.assert_called_once_with(DEVICE_DISPLAY_CLEAR)


@pytest.mark.asyncio
async def test_message_control_clear_message_device_inactive(message_control) -> None:
    """Test attempting to clear a message when device is not active."""
    message_control.dm.device_status = DeviceStatus.STANDBY
    with patch.object(message_control, "log", new_callable=MagicMock) as mock_log:
        await message_control.clear_message()
        mock_log.warning.assert_called_once_with(
            "Cannot clear message. Device is not in ACTIVE mode."
        )


@pytest.mark.asyncio
async def test_message_control_mixin_display_message(message_control_mixin) -> None:
    """Test calling display_message through MessageControlMixin."""
    await message_control_mixin.display_message(5, "Test Message")
    message_control_mixin.message.display_message.assert_called_once_with(
        5, "Test Message"
    )


@pytest.mark.asyncio
async def test_message_control_mixin_clear_message(message_control_mixin) -> None:
    """Test calling clear_message through MessageControlMixin."""
    await message_control_mixin.clear_message()
    message_control_mixin.message.clear_message.assert_called_once()


@pytest.mark.asyncio
async def test_navigation_control_commands(navigation_control) -> None:
    """Test all navigation commands in NavigationControl class."""
    navigation_control.sender.send_remote_command = AsyncMock()

    navigation_commands = {
        "down": "v",
        "exit": "EXIT",
        "enter": "ENTER",
        "home": "HOME",
        "left": "<",
        "menu": "MENU",
        "ok": ("Accept command", "desc"),
        "right": ">",
        "up": "^",
    }

    for method, command in navigation_commands.items():
        if isinstance(command, tuple):
            await getattr(navigation_control, method)()
            navigation_control.sender.send_remote_command.assert_called_with(
                command[0], key=command[1]
            )
        else:
            await getattr(navigation_control, method)()
            navigation_control.sender.send_remote_command.assert_called_with(command)
        navigation_control.sender.send_remote_command.reset_mock()


@pytest.mark.asyncio
async def test_navigation_control_mixin_commands(navigation_control_mixin) -> None:
    """Test all navigation commands in NavigationControlMixin class."""
    navigation_methods = [
        "down",
        "exit",
        "enter",
        "home",
        "left",
        "menu",
        "ok",
        "right",
        "up",
    ]

    for method in navigation_methods:
        await getattr(navigation_control_mixin, method)()
        getattr(navigation_control_mixin.navigation, method).assert_called_once()
        getattr(navigation_control_mixin.navigation, method).reset_mock()


@pytest.mark.asyncio
async def test_power_control_commands(power_control) -> None:
    """Test power control commands in PowerControl class."""
    power_control.sender.send_remote_command = AsyncMock()

    power_commands = {
        "standby": "STBY",
        "power_on": "ON",
    }

    for method, command in power_commands.items():
        await getattr(power_control, method)()
        power_control.sender.send_remote_command.assert_called_with(command)
        power_control.sender.send_remote_command.reset_mock()


@pytest.mark.asyncio
async def test_power_control_mixin_commands(power_control_mixin) -> None:
    """Test power control commands in PowerControlMixin class."""
    power_methods = ["standby", "power_on"]

    for method in power_methods:
        await getattr(power_control_mixin, method)()
        getattr(power_control_mixin.power, method).assert_called_once()
        getattr(power_control_mixin.power, method).reset_mock()


@pytest.mark.asyncio
async def test_remote_control_commands(remote_control) -> None:
    """Test remote control commands in RemoteControl class."""
    remote_control.sender.send_remote_command = AsyncMock()
    remote_control.sender.send_command = AsyncMock()

    remote_commands = {
        "alt": "ALT",
        "auto_aspect_disable": "AAD",
        "auto_aspect_enable": "AAE",
        "info": "INFO",
        "mema": "MEMA",
        "memb": "MEMB",
        "memc": "MEMC",
        "memd": "MEMD",
        "nls": "NLS",
    }

    for method, command in remote_commands.items():
        await getattr(remote_control, method)()
        remote_control.sender.send_remote_command.assert_called_with(command)
        remote_control.sender.send_remote_command.reset_mock()

    await remote_control.display_input_aspect()
    remote_control.sender.send_command.assert_called_with(DEVICE_DISPLAY_INPUT_ASPECT)
    remote_control.sender.send_command.reset_mock()

    await remote_control.input(5)
    remote_control.sender.send_command.assert_called_with("i5")
    remote_control.sender.send_command.reset_mock()

    with patch.object(remote_control, "log", new_callable=MagicMock) as mock_log:
        remote_control.dm.device_status = DeviceStatus.ACTIVE
        await remote_control.clear()
        remote_control.sender.send_remote_command.assert_called_with("CLR")
        mock_log.warning.assert_not_called()

    with patch.object(remote_control, "log", new_callable=MagicMock) as mock_log:
        remote_control.dm.device_status = DeviceStatus.STANDBY
        await remote_control.clear()
        mock_log.warning.assert_called_once_with(
            "Cannot send CLEAR command. Device is not in ACTIVE mode."
        )

    with patch.object(remote_control, "log", new_callable=MagicMock) as mock_log:
        remote_control.dm.device_status = DeviceStatus.ACTIVE
        remote_control.sender.send_command = AsyncMock()
        await remote_control.fanspeed(5)  # Valid fan speed
        remote_control.sender.send_command.assert_called_with(f"{DEVICE_FAN_SPEED}4")
        mock_log.error.assert_not_called()

    with patch.object(remote_control, "log", new_callable=MagicMock) as mock_log:
        remote_control.dm.device_status = DeviceStatus.STANDBY
        await remote_control.fanspeed(5)
        mock_log.warning.assert_called_once_with(
            "Cannot send FANSPEED command. Device is not in ACTIVE mode."
        )

    with patch.object(remote_control, "log", new_callable=MagicMock) as mock_log:
        remote_control.dm.device_status = DeviceStatus.ACTIVE
        await remote_control.fanspeed(11)  # Invalid fan speed
        mock_log.error.assert_called_once_with(
            "Invalid Fan Speed. Must be between 1 and 10."
        )

    with patch.object(remote_control, "log", new_callable=MagicMock) as mock_log:
        remote_control.dm.device_status = DeviceStatus.ACTIVE
        await remote_control.fanspeed(0)  # Invalid fan speed
        mock_log.error.assert_called_once_with(
            "Invalid Fan Speed. Must be between 1 and 10."
        )

    with patch.object(remote_control, "log", new_callable=MagicMock) as mock_log:
        remote_control.dm.device_status = DeviceStatus.ACTIVE
        remote_control.sender.send_command = AsyncMock()
        await remote_control.hotplug("A")  # Valid hotplug command
        remote_control.sender.send_command.assert_called_with(f"{DEVICE_HOTPLUG}A")
        mock_log.error.assert_not_called()

    with patch.object(remote_control, "log", new_callable=MagicMock) as mock_log:
        remote_control.dm.device_status = DeviceStatus.STANDBY
        await remote_control.hotplug("A")
        mock_log.warning.assert_called_once_with(
            "Cannot send HOTPLUG command. Device is not in ACTIVE mode."
        )

    with patch.object(remote_control, "log", new_callable=MagicMock) as mock_log:
        remote_control.dm.device_status = DeviceStatus.ACTIVE
        await remote_control.hotplug("Z")  # Invalid HDMI input
        mock_log.error.assert_called_once_with(
            "Invalid HDMI input. Must be '0'-'9' or 'A'."
        )

    with pytest.raises(
        ValueError, match="Invalid input index: -1. Must be a non-negative integer."
    ):
        await remote_control.input(-1)  # Invalid input index

    with pytest.raises(
        ValueError, match="Invalid input index: test. Must be a non-negative integer."
    ):
        await remote_control.input("test")  # Invalid input type


@pytest.mark.asyncio
async def test_remote_control_mixin_commands(remote_control_mixin) -> None:
    """Test remote control commands in RemoteControlMixin class."""
    remote_methods_with_args = {
        "input": 5,
        "fanspeed": 5,
        "hotplug": "A",
    }

    remote_methods_without_args = [
        "alt",
        "auto_aspect_disable",
        "auto_aspect_enable",
        "info",
        "mema",
        "memb",
        "memc",
        "memd",
        "nls",
        "clear",
    ]

    # Test methods that require arguments
    for method, arg in remote_methods_with_args.items():
        await getattr(remote_control_mixin, method)(arg)
        getattr(remote_control_mixin.remote, method).assert_called_once()
        getattr(remote_control_mixin.remote, method).reset_mock()

    # Test methods that do not require arguments
    for method in remote_methods_without_args:
        await getattr(remote_control_mixin, method)()  # No arguments
        getattr(remote_control_mixin.remote, method).assert_called_once()
        getattr(remote_control_mixin.remote, method).reset_mock()


@pytest.mark.asyncio
async def test_command_executor_send_command(command_executor) -> None:
    """Test sending a command through the CommandExecutor."""
    command_executor.sender.send_command = AsyncMock()
    await command_executor.send_command("TEST_COMMAND")
    command_executor.sender.send_command.assert_called_once_with("TEST_COMMAND")


@pytest.mark.asyncio
async def test_command_executor_send_remote_command(command_executor) -> None:
    """Test sending a remote command through the CommandExecutor."""
    command_executor.sender.send_remote_command = AsyncMock()
    await command_executor.send_remote_command("TEST_REMOTE")
    command_executor.sender.send_remote_command.assert_called_once_with(
        "TEST_REMOTE", "remote"
    )


@pytest.mark.asyncio
async def test_command_executor_get_all(command_executor) -> None:
    """Test retrieving all system information."""
    command_executor.sender.send_command = AsyncMock()
    command_executor.dm.context.device_state.device_event = MagicMock()

    result = await command_executor.get_all()
    command_executor.sender.send_command.assert_called()
    assert result == "Commands sent successfully."
    command_executor.dm.context.device_state.device_event.set.assert_called_once()


@pytest.mark.asyncio
async def test_command_executor_get_all_exclude_status(command_executor) -> None:
    """Test retrieving all system information excluding status commands."""
    command_executor.sender.send_command = AsyncMock()
    command_executor.dm.context.device_state.device_event = MagicMock()

    result = await command_executor.get_all(exclude_status=True)
    command_executor.sender.send_command.assert_called()
    assert result == "Commands sent successfully."
    command_executor.dm.context.device_state.device_event.clear.assert_called_once()


@pytest.mark.asyncio
async def test_command_executor_get_all_no_commands(command_executor) -> None:
    """Test get_all when no commands are left after exclusion."""
    command_executor.sender.log = MagicMock()

    # Force command_types to be empty
    with (
        patch("lumagen.command_executor.STATUS_ID", new=None),
        patch("lumagen.command_executor.STATUS_POWER", new=None),
        patch("lumagen.command_executor.DEVICE_FULL_V4", new=None),
        patch("lumagen.command_executor.INPUT_BASIC_INFO", new=None),
        patch("lumagen.command_executor.INPUT_VIDEO", new=None),
        patch("lumagen.command_executor.DEVICE_BASIC_OUTPUT_INFO", new=None),
        patch("lumagen.command_executor.DEVICE_OUTPUT_MODE", new=None),
        patch("lumagen.command_executor.DEVICE_OUTPUT_COLOR_FORMAT", new=None),
        patch("lumagen.command_executor.DEVICE_AUTOASPECT_QUERY", new=None),
        patch("lumagen.command_executor.DEVICE_GAMEMODE_QUERY", new=None),
    ):
        result = await command_executor.get_all(exclude_status=True)

    # Now we expect the log warning
    command_executor.sender.log.warning.assert_called_once_with(
        "No commands to send in get_all() after exclusion."
    )
    assert result == ""


@pytest.mark.asyncio
async def test_command_executor_getattr(command_executor) -> None:
    """Test __getattr__ method for dynamically resolving attributes."""
    aspect_control = command_executor.aspect  # Triggers __getattr__
    assert isinstance(aspect_control, AspectControl)

    with patch.object(command_executor, "log", new_callable=MagicMock) as mock_log:
        with pytest.raises(
            AttributeError,
            match="'CommandExecutor' object has no attribute 'non_existent'",
        ):
            _ = command_executor.non_existent
        mock_log.info.assert_not_called()
