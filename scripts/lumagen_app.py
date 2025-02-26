#!/usr/bin/env python3

"""Lumagen CLI Application."""

import argparse
import asyncio
import logging
import sys

from lumagen.constants import DEFAULT_BAUDRATE, DEFAULT_IP_PORT
from lumagen.device_manager import DeviceManager
from lumagen.utils import LoggingMixin
from prompt_toolkit.application import Application
from prompt_toolkit.clipboard import InMemoryClipboard
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.key_binding.bindings.focus import focus_next
from prompt_toolkit.key_binding.bindings.page_navigation import (
    scroll_page_down,
    scroll_page_up,
)
from prompt_toolkit.layout.containers import (
    Float,
    FloatContainer,
    HSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import SearchToolbar, TextArea


# pylint: disable=too-many-arguments, too-many-positional-arguments
class CustomLogger(logging.Logger):
    """Custom Logger that adds classname to log records."""

    def _log(
        self,
        level,
        msg,
        args,
        exc_info=None,
        extra=None,
        stack_info=False,
        stacklevel=1,
    ):
        if extra is None:
            extra = {}
        # Add classname to the extra fields
        frame = logging.currentframe().f_back.f_back
        cls_name = frame.f_locals.get("self", None)
        extra["classname"] = cls_name.__class__.__name__ if cls_name else "N/A"

        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)


logging.setLoggerClass(CustomLogger)


class CustomLoggingHandler(logging.Handler):
    """A logging handler to output log messages to a prompt_toolkit TextArea."""

    def __init__(self, output_field) -> None:
        """Init Class."""
        super().__init__()
        self.output_field = output_field

    def emit(self, record):
        """Emit."""
        message = self.format(record)
        update_text_area(self.output_field, message + "\n")


# Function to update the log area
def update_text_area(output_field: TextArea, text):
    """Update the log area with new text."""
    output_field.text += text
    output_field.buffer.cursor_position = len(output_field.text)


def configure_logging(output_field, log_level):
    """Set up global logging with CustomLogger and CustomLoggingHandler."""
    logging_handler = CustomLoggingHandler(output_field)
    logging_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(classname)s - "
            "%(funcName)s - %(message)s"
        )
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(logging_handler)


class LumagenApp(LoggingMixin):
    """LumagenApp is a user interface application for interacting with the Lumagen device.

    It provides a text-based interface built using `prompt_toolkit` and facilitates
    communication with the Lumagen hardware via asynchronous commands.
    Inherits:
        LoggingMixin: A mixin that provides logging capabilities for the class.

    Attributes:
        device (AsyncDeviceDriver): The asynchronous driver responsible for handling
            communication with the Lumagen device.
        search_field (SearchToolbar): A `SearchToolbar` widget used for handling
            search functionality within the application.

    Methods:
        __init__(): Initializes the LumagenApp instance, including logging and
            UI components.
        run(): The main method to start the application. It sets up the user
            interface, handles user input, and manages device communication.

    """

    _fallback_logger = None

    def __init__(self) -> None:
        """Init."""
        super().__init__()
        self.device: DeviceManager = None
        self.search_field = SearchToolbar()
        self.output_field: TextArea = None
        self.input_field: TextArea = None

    async def run(self, args):
        "Implement main application logic."
        if self._fallback_logger is None:
            self._fallback_logger = logging.getLogger("FallbackLogger")
            self._fallback_logger.setLevel(args.log_level)
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            )
            self._fallback_logger.addHandler(console_handler)

        try:
            self.setup_ui()
            configure_logging(self.output_field, log_level=args.log_level)
            self.log.debug("Starting Application")

            try:
                await self.setup_connection()
            except KeyboardInterrupt:
                print()  # noqa: T201

            application = self.create_application(args)
            await application.run_async()

        except OSError as e:
            self._fallback_logger.error("OS error occurred: %s", e)
        except (KeyboardInterrupt, asyncio.CancelledError):
            self._fallback_logger.info("Keyboard interrupt received. Exiting...")
        finally:
            if self.device is not None:
                await self.device.close()
                self._fallback_logger.info("Device connection closed.")

    def setup_ui(self):
        """Set up the UI components."""
        self.output_field = TextArea(
            style="class:output-field",
            scrollbar=True,
            wrap_lines=True,
            read_only=True,
            focusable=True,
        )
        self.input_field = TextArea(
            height=1,
            prompt=">>> ",
            style="class:input-field",
            multiline=False,
            wrap_lines=False,
            search_field=self.search_field,
            complete_while_typing=True,
            completer=self.create_completer(),
        )
        self.input_field.accept_handler = self.accept

    async def setup_connection(self):
        """Prompt user for connection settings and return the appropriate connection object."""
        use_ip = (
            input(
                "Press Enter to use IP connection (default) or type 's' for Serial connection: "
            )
            .strip()
            .lower()
        )

        if use_ip == "s":
            port = (
                input("Enter serial port (default /dev/ttyS0): ").strip()
                or "/dev/ttyS0"
            )
            baudrate_input = input(
                f"Enter baud rate (default {DEFAULT_BAUDRATE}): "
            ).strip()
            baudrate = int(baudrate_input) if baudrate_input else DEFAULT_BAUDRATE
            self.device = DeviceManager(connection_type="serial")
            await self.device.open(port=port, baudrate=baudrate)
        else:
            ip = (
                input("Enter IP address (default 192.168.15.71): ").strip()
                or "192.168.15.71"
            )
            port_input = input(f"Enter port (default {DEFAULT_IP_PORT}): ").strip()
            port = int(port_input) if port_input else DEFAULT_IP_PORT
            self.device = DeviceManager(connection_type="ip")
            await self.device.open(host=ip, port=port)

    def create_application(self, args):
        """Create the application object."""
        body = self.create_body()
        key_bindings = self.setup_keybindings(args)
        return Application(
            layout=Layout(body, focused_element=self.input_field),
            key_bindings=key_bindings,
            style=Style(
                [
                    ("output-field", "bg:#000044 #ffffff"),
                    ("input-field", "bg:#000000 #ffffff"),
                    ("line", "#004400"),
                ]
            ),
            clipboard=InMemoryClipboard(),
            mouse_support=False,
            full_screen=True,
        )

    def accept(self, _):
        """Handle user input and execute the corresponding command."""
        commands = {
            "clear": lambda: setattr(self.output_field, "text", ""),
            "get_all": lambda: asyncio.create_task(self.device.executor.get_all()),
            "get_labels": lambda: asyncio.create_task(
                self.device.executor.get_labels()
            ),
            "set_labels": lambda: asyncio.create_task(
                self.device.executor.set_labels()
            ),
            "show_all": lambda: asyncio.create_task(self.device.show_all()),
            "show_info": lambda: asyncio.create_task(self.device.show_info()),
            "show_labels": lambda: asyncio.create_task(self.device.show_labels()),
            "show_source_list": lambda: asyncio.create_task(
                self.device.show_source_list()
            ),
            "power_on": lambda: asyncio.create_task(self.device.executor.power_on()),
            "power_off": lambda: asyncio.create_task(self.device.executor.standby()),
            "save": lambda: asyncio.create_task(
                self.device.send_command("ZY6SAVECONFIG")
            ),
            "show_state": lambda: asyncio.create_task(self.device.show_power_state()),
            "send_test": lambda: asyncio.create_task(self.device.test_command()),
        }
        command = self.input_field.text.strip()
        action = commands.get(
            command, lambda: asyncio.create_task(self.device.send_command(command))
        )
        action()

    def create_body(self):
        """Create the main body layout for the application."""

        def get_titlebar_text():
            """Return the formatted text for the title bar."""
            return [
                ("class:title", " Lumagen App "),
                ("class:title", " (Press [Ctrl-C] to exit.)"),
            ]

        return FloatContainer(
            content=HSplit(
                [
                    Window(
                        height=1,
                        content=FormattedTextControl(get_titlebar_text),
                        align=WindowAlign.CENTER,
                    ),
                    self.output_field,
                    Window(height=1, char="-", style="class:line"),
                    self.input_field,
                    self.search_field,
                ]
            ),
            floats=[
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(max_height=16, scroll_offset=1),
                )
            ],
        )

    def create_completer(self):
        """Create a word completer for input commands."""
        return WordCompleter(
            [
                "clear",
                "get_all",
                "get_labels",
                "power_on",
                "power_off",
                "save",
                "show_all",
                "show_info",
                "show_labels",
                "show_source_list",
                "show_state",
                "set_labels",
                "ZQI00",
                "ZQI01",
                "ZQI21",
                "ZQI22",
                "ZQI23",
                "ZQI24",
                "ZQI52",
                "ZQI53",
                "ZQI54",
                "ZQO00",
                "ZQO01",
                "ZQO02",
                "ZQS00",
                "ZQS01",
                "ZQS02",
                "ZQS1A0",
                "ZQS1A1",
                "ZQS1A2",
                "ZQS1A3",
                "ZQS1A4",
                "ZQS1A5",
                "ZQS1A6",
                "ZY520A",
            ],
            ignore_case=False,
        )

    async def query_labels(self):
        """Send label query commands for all relevant labels."""
        labels = [
            f"{chr(x)}{y}" for x in range(ord("A"), ord("D") + 1) for y in range(6)
        ]
        labels += [f"{x}{y}" for x in range(1, 4) for y in range(8)]
        for label in labels:
            await self.device.send_command(f"ZQS1{label}")

    async def set_labels(self):
        """Set Labels."""
        await self.device.executor.set_labels()

    def setup_keybindings(self, args):
        """Set up key bindings for the application."""
        kb = KeyBindings()
        kb.add("c-c")(lambda event: self.exit_app(event, args))
        kb.add("c-q")(lambda event: self.exit_app(event, args))
        kb.add("pageup")(self.page_up)
        kb.add("pagedown")(self.page_down)
        # kb.add("up")(lambda event: self.scroll_up_line())
        # kb.add("down")(lambda event: self.scroll_down_line())
        kb.add("c-space")(focus_next)

        return kb

    def scroll_up_line(self):
        """Scroll up by one line in the output field."""
        self.output_field.buffer.cursor_up(count=1)

    def scroll_down_line(self):
        """Scroll down by one line in the output field."""
        self.output_field.buffer.cursor_down(count=1)

    def exit_app(self, event: KeyPressEvent, args):
        """Gracefully exit the application on Ctrl-Q or Ctrl-C."""
        self.log.info("Closing connection and exiting application.")

        async def shutdown():
            if self.device is not None:
                await self.device.close()
            update_text_area(self.output_field, "Waiting ")
            for _ in range(args.exit_wait_timer):
                update_text_area(self.output_field, ".")
                await asyncio.sleep(1)
            event.app.exit()

        asyncio.create_task(shutdown())  # noqa: RUF006

    def page_up(self, event: KeyPressEvent):
        """Scroll up in the output field."""
        self._scroll(event, scroll_page_up)

    def page_down(self, event: KeyPressEvent):
        """Scroll down in the output field."""
        self._scroll(event, scroll_page_down)

    def _scroll(self, event: KeyPressEvent, scroll_func):
        "Define a helper function for scrolling actions."
        w = event.app.layout.current_window
        event.app.layout.focus(self.output_field.window)
        scroll_func(event)
        event.app.layout.focus(w)


def main():
    """Entry point for the Lumagen application.

    This function sets up and parses command-line arguments for configuring the
    application's logging level and exit wait timer. It then initializes the
    LumagenApp instance and runs it asynchronously.

    Command-line arguments:
        -l, --log-level: Set the logging level (default: INFO).
                         Choices: ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        -e, --exit-wait-timer: Set the wait timer in seconds before exiting (default: 4).

    The parsed arguments are passed to the LumagenApp instance, which is executed
    using asyncio.

    """

    parser = argparse.ArgumentParser(description="Lumagen Application")
    parser.add_argument(
        "-l",
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)",
    )

    parser.add_argument(
        "-e",
        "--exit-wait-timer",
        type=int,
        default=4,
        help="Set the wait timer in seconds before exiting (default: 4)",
    )

    parsed_args = parser.parse_args()

    app = LumagenApp()
    asyncio.run(app.run(args=parsed_args))


if __name__ == "__main__":
    main()
