"""Module: CommandExecutor.

Handles execution of device commands by grouping them into specialized command handlers.
This improves **organization**, **maintainability**, and **structured control** over the device.
"""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

from .connection import BaseHandler
from .constants import (
    ASCII_COMMAND_LIST,
    CMD_DEVICE_START,
    DEVICE_AUTOASPECT_QUERY,
    DEVICE_BASIC_OUTPUT_INFO,
    DEVICE_DISPLAY_CLEAR,
    DEVICE_DISPLAY_INPUT_ASPECT,
    DEVICE_DISPLAY_MSG,
    DEVICE_FAN_SPEED,
    DEVICE_FULL_V4,
    DEVICE_GAMEMODE_QUERY,
    DEVICE_HOTPLUG,
    DEVICE_LABEL_QUERY,
    DEVICE_OUTPUT_COLOR_FORMAT,
    DEVICE_OUTPUT_MODE,
    DEVICE_SET_LABEL,
    INPUT_BASIC_INFO,
    INPUT_VIDEO,
    STATUS_ID,
    STATUS_POWER,
    DeviceStatus,
)
from .utils import LoggingMixin

if TYPE_CHECKING:  # pragma: no cover
    from .device_manager import DeviceManager


class CommandSender(LoggingMixin):
    """Handles sending raw commands to the device."""

    def __init__(self, connection_handler: BaseHandler) -> None:
        """Initialize with a connection handler."""
        super().__init__()
        self._handler = connection_handler

    async def send_command(self, command: str | list[str]) -> None:
        """Send a command or list of commands over the connection."""
        try:
            if isinstance(command, str):
                commands = [command.strip()] if command.strip() else []
            elif isinstance(command, list):
                commands = [
                    cmd.strip()
                    for cmd in command
                    if isinstance(cmd, str) and cmd.strip()
                ]
            else:
                self.log.error("Invalid command type: %s", type(command).__name__)
                return

            if not commands:
                self.log.warning("No valid commands to send after filtering.")
                return

            await self._handler.queue_command(commands)
        except AttributeError as e:
            self.log.error("Attribute error in send_command(): %s", e)
        except TypeError as e:
            self.log.error("Type error in send_command(): %s", e)
        except asyncio.exceptions.TimeoutError as e:
            self.log.error("Timeout while sending command: %s", e)
        except ConnectionError as e:
            self.log.error("Connection error while sending command: %s", e)
        except RuntimeError as e:
            self.log.error("Runtime error while sending command: %s", e)

    async def send_remote_command(self, value: str, key: str = "remote") -> None:
        """Send a command by looking up a key-value pair in ASCII_COMMAND_LIST."""

        cmd = {j.get(key): i for i, j in ASCII_COMMAND_LIST.items()}.get(value)

        if cmd:
            self.log.debug("Sending remote command: %s", cmd)
            await self.send_command(cmd)
        else:
            self.log.warning(
                "Command not found for value: %s (searched by key: %s)", value, key
            )


class AspectControl:
    """Handles source aspect ratio commands."""

    def __init__(self, sender: CommandSender) -> None:
        """Initialize with a command sender."""
        self.sender = sender

    async def source_aspect_4x3(self) -> None:
        """Set source aspect ratio to 4:3."""
        await self.sender.send_remote_command("4:3")

    async def source_aspect_16x9(self) -> None:
        """Set source aspect ratio to 16:9."""
        await self.sender.send_remote_command("16:9")

    async def source_aspect_1_85(self) -> None:
        """Send SOURCE ASPECT 1.85 command."""
        await self.sender.send_remote_command("1.85")

    async def source_aspect_1_90(self) -> None:
        """Send SOURCE ASPECT 1.90 command."""
        await self.sender.send_remote_command("1.90")

    async def source_aspect_2_00(self) -> None:
        """Send SOURCE ASPECT 2.00 command."""
        await self.sender.send_remote_command("2.00")

    async def source_aspect_2_20(self) -> None:
        """Send SOURCE ASPECT 2.20 command."""
        await self.sender.send_remote_command("2.20")

    async def source_aspect_2_35(self) -> None:
        """Send SOURCE ASPECT 2.35 command."""
        await self.sender.send_remote_command("2.35")

    async def source_aspect_2_40(self) -> None:
        """Send SOURCE ASPECT 2.40 command."""
        await self.sender.send_remote_command("2.40")

    async def source_aspect_lbox(self) -> None:
        """Send SOURCE ASPECT Letterbox (LBOX) command."""
        await self.sender.send_remote_command("LBOX")


class AspectControlMixin:
    """Mixin for handling aspect ratio commands."""

    aspect: AspectControl

    async def source_aspect_4x3(self) -> None:
        """Set the source aspect ratio to 4:3."""
        await self.aspect.source_aspect_4x3()

    async def source_aspect_16x9(self) -> None:
        """Set the source aspect ratio to 16:9."""
        await self.aspect.source_aspect_16x9()

    async def source_aspect_1_85(self) -> None:
        """Set the source aspect ratio to 1.85:1."""
        await self.aspect.source_aspect_1_85()

    async def source_aspect_1_90(self) -> None:
        """Set the source aspect ratio to 1.90:1."""
        await self.aspect.source_aspect_1_90()

    async def source_aspect_2_00(self) -> None:
        """Set the source aspect ratio to 2.00:1."""
        await self.aspect.source_aspect_2_00()

    async def source_aspect_2_20(self) -> None:
        """Set the source aspect ratio to 2.20:1."""
        await self.aspect.source_aspect_2_20()

    async def source_aspect_2_35(self) -> None:
        """Set the source aspect ratio to 2.35:1."""
        await self.aspect.source_aspect_2_35()

    async def source_aspect_2_40(self) -> None:
        """Set the source aspect ratio to 2.40:1."""
        await self.aspect.source_aspect_2_40()

    async def source_aspect_lbox(self) -> None:
        """Set the source aspect ratio to Letterbox (LBOX)."""
        await self.aspect.source_aspect_lbox()


class LabelControl:
    """Handles input label querying and setting."""

    def __init__(self, sender: CommandSender, device_manager: DeviceManager) -> None:
        """Initialize with a command sender and device manager.

        Args:
            sender (CommandSender): The sender instance for executing commands.
            device_manager (DeviceManager): The device manager instance.

        """
        self.sender = sender
        self.device_manager = device_manager

    async def get_labels(self) -> None:
        """Retrieve all input labels dynamically."""
        self.device_manager.labels = {}
        commands = []

        # First loop: Letters A-D with numbers 9-0
        for x in range(ord("A"), ord("D") + 1):
            for y in range(9, -1, -1):  # Count down due to a known bug
                label = f"{chr(x)}{y}"
                commands.append(f"{CMD_DEVICE_START}{DEVICE_LABEL_QUERY}{label}")

        # Second loop: Numbers 1-3 with numbers 0-7
        for x in range(1, 4):
            for y in range(8):
                label = f"{x}{y}"
                commands.append(f"{CMD_DEVICE_START}{DEVICE_LABEL_QUERY}{label}")

        self.sender.log.info("Sending %d label queries...", len(commands))
        await self.sender.send_command(commands)
        self.sender.log.info("All label queries sent successfully.")

    async def set_labels(self, port_config: dict[str, str] | None = None):
        """Set input labels based on port configurations."""

        port_config = port_config or {
            f"{x}{y}": f"HDMI {x}{y}" for x in "ABCD" for y in "0123456789"
        }

        valid_key_pattern = re.compile(r"^[ABCD][0-9]$|^[123][0-7]$")
        max_label_length = {"ABCD": 10, "1": 7}

        commands = [
            f"{DEVICE_SET_LABEL}{key}{label[:max_label_length.get(key[0], 8)]}"
            for key, label in port_config.items()
            if valid_key_pattern.match(key)
        ]

        if not commands:
            self.sender.log.warning("No valid label commands generated.")
            return

        self.sender.log.info("Sending %d label commands...", len(commands))
        await self.sender.send_command(commands)
        self.sender.log.debug("All label commands sent successfully.")


class LabelControlMixin:
    """Mixin for handling input label commands."""

    label: LabelControl

    async def get_labels(self) -> None:
        """Retrieve all input labels."""
        await self.label.get_labels()

    async def set_labels(self, port_config: dict[str, str] | None = None) -> None:
        """Set input labels based on port configurations."""
        await self.label.set_labels(port_config)


class MessageControl(LoggingMixin):
    """Handles messages on display."""

    def __init__(self, sender: CommandSender, device_manager: DeviceManager) -> None:
        """Initialize with a command sender and device manager."""
        super().__init__()
        self.sender = sender
        self.dm = device_manager

    async def display_message(self, timeout: int, message: str) -> None:
        """Send a Display Message command (timeout: 0-9, 9 keeps displayed until "ZC").

        Args:
            timeout (int): 0 to 9, where 9 keeps the message displayed until "ZC" is sent.
            message (str): The message to display (supports 2 lines, 30 chars each).

        Only allows ASCII characters (0x20-0x7A). ASCII extended characters allowed for volume bars.

        """

        if not isinstance(timeout, int) or not 0 <= timeout <= 9:
            raise ValueError(
                f"Invalid timeout: {timeout}. Must be an integer between 0 and 9."
            )

        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message must be a non-empty string.")

        # Filter message to only include allowed ASCII characters
        sanitized_message = "".join(
            char for char in message if 0x20 <= ord(char) <= 0x7A
        )

        if not sanitized_message:
            self.log.warning("Filtered message is empty after character sanitization.")
            return

        command = f"{DEVICE_DISPLAY_MSG}{timeout}{sanitized_message}"

        if self.dm.device_status != DeviceStatus.ACTIVE:
            self.log.warning("Cannot display message. Device is not in ACTIVE mode.")
            return

        self.log.info(
            "Sending show message command: '%s' with timeout %d",
            sanitized_message,
            timeout,
        )
        await self.sender.send_command(command)
        self.log.info("Message sent successfully.")

    async def clear_message(self) -> None:
        """Send Clear Message command to the device."""

        if self.dm.device_status != DeviceStatus.ACTIVE:
            self.log.warning("Cannot clear message. Device is not in ACTIVE mode.")
            return

        await self.sender.send_command(DEVICE_DISPLAY_CLEAR)


class MessageControlMixin:
    """Mixin for handling display message commands."""

    message: MessageControl

    async def display_message(self, timeout: int, message: str) -> None:
        """Send a Display Message command to the device..

        Args:
            timeout (int): 0 to 9, where 9 keeps the message displayed until "ZC" is sent.
            message (str): The message to display (supports 2 lines, 30 chars each).

        Only allows ASCII characters (0x20-0x7A). ASCII extended characters allowed for volume bars.

        """
        await self.message.display_message(timeout, message)

    async def clear_message(self) -> None:
        """Send a Clear Message command to the device."""
        await self.message.clear_message()


class NavigationControl:
    """Handles remote commands for navigation."""

    def __init__(self, sender: CommandSender) -> None:
        """Initialize with a command sender."""
        self.sender = sender

    async def down(self) -> None:
        """Send DOWN command."""
        await self.sender.send_remote_command("v")

    async def exit(self) -> None:
        """Send EXIT command (exit current menu or screen)."""
        await self.sender.send_remote_command("EXIT")

    async def enter(self) -> None:
        """Send ENTER command (confirm selection)."""
        await self.sender.send_remote_command("ENTER")

    async def home(self) -> None:
        """Send HOME command (return to the main screen)."""
        await self.sender.send_remote_command("HOME")

    async def left(self) -> None:
        """Send LEFT command."""
        await self.sender.send_remote_command("<")

    async def menu(self) -> None:
        """Send MENU command (open settings menu)."""
        await self.sender.send_remote_command("MENU")

    async def ok(self) -> None:
        """Send OK command."""

        await self.sender.send_remote_command("Accept command", key="desc")

    async def right(self) -> None:
        """Send RIGHT command."""
        await self.sender.send_remote_command(">")

    async def up(self) -> None:
        """Send UP command."""
        await self.sender.send_remote_command("^")


class NavigationControlMixin:
    """Mixin for handling navigation commands."""

    navigation: NavigationControl  # Type hint for IDE support

    async def down(self) -> None:
        """Send DOWN command."""
        await self.navigation.down()

    async def exit(self) -> None:
        """Send EXIT command (exit current menu or screen)."""
        await self.navigation.exit()

    async def enter(self) -> None:
        """Send ENTER command (confirm selection)."""
        await self.navigation.enter()

    async def home(self) -> None:
        """Send HOME command (return to the main screen)."""
        await self.navigation.home()

    async def left(self) -> None:
        """Send LEFT command."""
        await self.navigation.left()

    async def menu(self) -> None:
        """Send MENU command (open settings menu)."""
        await self.navigation.menu()

    async def ok(self) -> None:
        """Send OK command."""
        await self.navigation.ok()

    async def right(self) -> None:
        """Send RIGHT command."""
        await self.navigation.right()

    async def up(self) -> None:
        """Send UP command."""
        await self.navigation.up()


class PowerControl:
    """Handles power state transitions."""

    def __init__(self, sender: CommandSender) -> None:
        """Initialize with a command sender and device manager."""
        self.sender = sender

    async def standby(self) -> None:
        """Put the device in standby mode."""
        await self.sender.send_remote_command("STBY")

    async def power_on(self) -> None:
        """Turn the device on."""
        await self.sender.send_remote_command("ON")


class PowerControlMixin:
    """Mixin for power state transitions."""

    power: PowerControl

    async def standby(self) -> None:
        """Put the device in standby mode."""
        await self.power.standby()

    async def power_on(self) -> None:
        """Turn the device on."""
        await self.power.power_on()


class RemoteControl(LoggingMixin):
    """Handles remote commands for menus and settings."""

    def __init__(self, sender: CommandSender, device_manager: DeviceManager) -> None:
        """Initialize with a command sender."""
        super().__init__()
        self.sender = sender
        self.dm = device_manager

    async def alt(self) -> None:
        """Send ALT command."""

        await self.sender.send_remote_command("ALT")

    async def auto_aspect_disable(self) -> None:
        """Send AUTO ASPECT DISABLE command."""

        await self.sender.send_remote_command("AAD")

    async def auto_aspect_enable(self) -> None:
        """Send AUTO ASPECT ENABLE command."""

        await self.sender.send_remote_command("AAE")

    async def clear(self) -> None:
        """Send CLEAR command to the device."""

        if self.dm.device_status != DeviceStatus.ACTIVE:
            self.log.warning("Cannot send CLEAR command. Device is not in ACTIVE mode.")
            return

        await self.sender.send_remote_command("CLR")

    async def display_input_aspect(self) -> None:
        """Send DISPLAY INPUT ASPECT command."""

        await self.sender.send_command(DEVICE_DISPLAY_INPUT_ASPECT)

    async def fanspeed(self, speed: int) -> None:
        """Send FANSPEED command to the device.

        Args:
            speed (int): 1-10 for speeds, translated internally to 0-9.

        """
        if self.dm.device_status != DeviceStatus.ACTIVE:
            self.log.warning(
                "Cannot send FANSPEED command. Device is not in ACTIVE mode."
            )
            return

        if not 1 <= speed <= 10:
            self.log.error("Invalid Fan Speed. Must be between 1 and 10.")
            return

        translated_speed = speed - 1

        command = f"{DEVICE_FAN_SPEED}{translated_speed}"
        await self.sender.send_command(command)

    async def hotplug(self, x: str) -> None:
        """Send HOTPLUG command to the device.

        Args:
            x (str): HDMI input identifier ('0'-'9' for HDMI 1-10, 'A' for all inputs)

        """
        if self.dm.device_status != DeviceStatus.ACTIVE:
            self.log.warning(
                "Cannot send HOTPLUG command. Device is not in ACTIVE mode."
            )
            return

        valid_inputs = {str(i) for i in range(10)} | {"A"}

        if x not in valid_inputs:
            self.log.error("Invalid HDMI input. Must be '0'-'9' or 'A'.")
            return

        command = f"{DEVICE_HOTPLUG}{x}"
        await self.sender.send_command(command)

    async def info(self) -> None:
        """Send INFO command (display system information)."""
        await self.sender.send_remote_command("INFO")

    async def input(self, index: int) -> None:
        """Send INPUT command with the specified index."""

        if not isinstance(index, int) or index < 0:
            raise ValueError(
                f"Invalid input index: {index}. Must be a non-negative integer."
            )

        await self.sender.send_command(f"i{index}")

    async def mema(self) -> None:
        """Send send MEMA command."""

        await self.sender.send_remote_command("MEMA")

    async def memb(self) -> None:
        """Send MEMB command."""

        await self.sender.send_remote_command("MEMB")

    async def memc(self) -> None:
        """Send MEMC command."""

        await self.sender.send_remote_command("MEMC")

    async def memd(self) -> None:
        """Send MEMD command."""

        await self.sender.send_remote_command("MEMD")

    async def nls(self) -> None:
        """Send NLS command."""

        await self.sender.send_remote_command("NLS")


class RemoteControlMixin:
    """Mixin for handling remote commands for menus and settings."""

    remote: RemoteControl

    async def alt(self) -> None:
        """Send ALT command."""
        await self.remote.alt()

    async def auto_aspect_disable(self) -> None:
        """Send AUTO ASPECT DISABLE command."""
        await self.remote.auto_aspect_disable()

    async def auto_aspect_enable(self) -> None:
        """Send AUTO ASPECT ENABLE command."""
        await self.remote.auto_aspect_enable()

    async def clear(self) -> None:
        """Send CLEAR command to the device."""
        await self.remote.clear()

    async def hotplug(self, x: str) -> None:
        """Send HOTPLUG command to the device."""
        await self.remote.hotplug(x)

    async def fanspeed(self, speed: int) -> None:
        """Send FANSPEED command to the device.

        Args:
            speed (int): 1-10 for speeds.

        """
        await self.remote.fanspeed(speed)

    async def info(self) -> None:
        """Send INFO command (display system information)."""
        await self.remote.info()

    async def input(self, index: int) -> None:
        """Send INPUT command with the specified index."""
        await self.remote.input(index)

    async def mema(self) -> None:
        """Send MEMA command."""
        await self.remote.mema()

    async def memb(self) -> None:
        """Send MEMB command."""
        await self.remote.memb()

    async def memc(self) -> None:
        """Send MEMC command."""
        await self.remote.memc()

    async def memd(self) -> None:
        """Send MEMD command."""
        await self.remote.memd()

    async def nls(self) -> None:
        """Send NLS command."""
        await self.remote.nls()


class CommandExecutor(
    LoggingMixin,
    AspectControlMixin,
    LabelControlMixin,
    MessageControlMixin,
    NavigationControlMixin,
    PowerControlMixin,
    RemoteControlMixin,
):
    """The main command executor that combines all functionality."""

    def __init__(
        self, connection_handler: BaseHandler, device_manager: DeviceManager
    ) -> None:
        """Initialize and set up all command groups.

        Args:
            connection_handler (BaseHandler): The device connection handler.
            device_manager (DeviceManager): The device manager instance.

        """
        super().__init__()
        self.dm = device_manager
        self.sender = CommandSender(connection_handler)

        self._controls = {
            "aspect": AspectControl(self.sender),
            "label": LabelControl(self.sender, self.dm),
            "message": MessageControl(self.sender, self.dm),
            "navigation": NavigationControl(self.sender),
            "power": PowerControl(self.sender),
            "remote": RemoteControl(self.sender, self.dm),
        }

    def __getattr__(self, name):
        """Efficiently resolve attributes dynamically with caching."""

        if name in self._controls:
            self.log.info(name)
            setattr(self, name, self._controls[name])
            return self._controls[name]

        for control in self._controls.values():
            if hasattr(control, name):
                setattr(self, name, getattr(control, name))
                return getattr(self, name)

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )

    async def send_command(self, command: str) -> None:
        """Send a command using the main executor."""
        await self.sender.send_command(command)

    async def send_remote_command(self, value: str, key: str = "remote") -> None:
        """Send a remote command through the executor."""
        await self.sender.send_remote_command(value, key)

    async def get_all(self, exclude_status: bool = False) -> str:
        """Retrieve all system information by sending multiple commands.

        - If `exclude_status` is True, excludes STATUS_ID, STATUS_POWER, and DEVICE_FULL_V4.

        Args:
            exclude_status (bool, optional): Whether to exclude status-related queries.

        Returns:
            str: Confirmation message that commands were sent.

        """

        command_types = [
            STATUS_ID,
            STATUS_POWER,
            INPUT_BASIC_INFO,
            INPUT_VIDEO,
            DEVICE_FULL_V4,
            DEVICE_BASIC_OUTPUT_INFO,
            DEVICE_OUTPUT_MODE,
            DEVICE_OUTPUT_COLOR_FORMAT,
            DEVICE_AUTOASPECT_QUERY,
            DEVICE_GAMEMODE_QUERY,
        ]

        if exclude_status:
            command_types = [
                cmd
                for cmd in command_types
                if cmd not in {STATUS_ID, STATUS_POWER, DEVICE_FULL_V4}
            ]

        if not command_types:
            self.sender.log.warning("No commands to send in get_all() after exclusion.")
            return ""

        commands = [f"{CMD_DEVICE_START}{cmd}" for cmd in command_types]

        self.sender.log.info("Sending commands: %s", commands)

        await self.send_command(commands)

        if exclude_status:
            self.sender.log.debug(
                "Device event cleared after excluding status commands."
            )
            self.dm.context.device_state.device_event.clear()
        else:
            self.sender.log.debug("Device event set after sending all commands.")
            self.dm.context.device_state.device_event.set()

        return "Commands sent successfully."
