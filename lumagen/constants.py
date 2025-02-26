"""constants.py.

This module defines global constants for the device driver, including
default configurations and command formatting.
"""

from enum import Enum, IntEnum

# Default configuration for serial communication
DEFAULT_BAUDRATE = 9600
DEFAULT_BUFFER_SIZE = 1024

# Default IP port configuration
DEFAULT_IP_PORT = 4999

DEFAULT_HEALTH_CHECK_INTERVAL = 30


class EventType(Enum):
    """Enum for valid event types."""

    CONNECTION_STATE = "connection_state"
    DATA_RECEIVED = "data_received"


class InputMemoryEnum(str, Enum):
    """Enum for input memory."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"


class ConnectionStatus(Enum):
    """Enum for connection statuses."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


class DeviceStatus(str, Enum):
    """Enum for device status (whether it's on or in standby)."""

    STANDBY = "Standby"
    ACTIVE = "Active"


class Frame3DTypeEnum(IntEnum):
    """Enum for frame format and input 3D type."""

    OFF = 0
    FRAME_PACKED = 2
    TOP_BOTTOM = 4
    SIDE_BY_SIDE = 8

    def __str__(self):
        """Return a human-readable string for the enum."""
        return {
            Frame3DTypeEnum.OFF: "Off",
            Frame3DTypeEnum.FRAME_PACKED: "Frame Packed",
            Frame3DTypeEnum.TOP_BOTTOM: "Top-Bottom",
            Frame3DTypeEnum.SIDE_BY_SIDE: "Side-by-Side",
        }[self]


class InputStatus(IntEnum):
    """Enum for video status."""

    NONE = 0
    VIDEO_ACTIVE = 1
    TEST_PATTERN_ACTIVE = 2

    def __str__(self):
        """Return String."""
        return {
            InputStatus.NONE: "No Source",
            InputStatus.VIDEO_ACTIVE: "Active Video",
            InputStatus.TEST_PATTERN_ACTIVE: "Internal Pattern",
        }[self]


class StateStatus(str, Enum):
    """Enum representing possible state statuses."""

    DISABLED = "Disabled"
    ENABLED = "Enabled"


CMD_START = b"#"
CMD_TERMINATOR = b"{"
CMD_DEVICE_START = "ZQ"

INPUT_BASIC_INFO = "I00"
INPUT_VIDEO = "I01"
DEVICE_FULL_V1 = "I21"
DEVICE_FULL_V2 = "I22"
DEVICE_FULL_V3 = "I23"
DEVICE_FULL_V4 = "I24"
DEVICE_GAMEMODE_QUERY = "I53"
DEVICE_AUTOASPECT_QUERY = "I54"

STATUS_ALIVE = "S00"
STATUS_ID = "S01"
STATUS_POWER = "S02"

DEVICE_DISPLAY_CLEAR = "ZC"
DEVICE_DISPLAY_MSG = "ZT"
DEVICE_DISPLAY_INPUT_ASPECT = "ZY811"
DEVICE_HOTPLUG = "ZY520"
DEVICE_GAMEMODE = "ZY551"
DEVICE_FAN_SPEED = "ZY522"

DEVICE_LABEL_QUERY = "S1"
DEVICE_SET_LABEL = "ZY524"

DEVICE_BASIC_OUTPUT_INFO = "O00"
DEVICE_OUTPUT_MODE = "O01"
DEVICE_OUTPUT_COLOR_FORMAT = "O18"

OUTPUT_COLOR_FORMAT_422 = "422"
OUTPUT_COLOR_FORMAT_444 = "444"
OUTPUT_COLOR_FORMAT_RGB_VIDEO_LEVEL = "RGB video level"
OUTPUT_COLOR_FORMAT_RGB_PC_LEVEL = "RGB PC level"
OUTPUT_COLOR_FORMAT_420 = "420"

# pylint: disable=line-too-long
ASCII_COMMAND_LIST = {
    "%": {"remote": "ON", "desc": "Power on"},
    "$": {"remote": "STBY", "desc": "Power to standby"},
    "M": {"remote": "MENU", "desc": "Activate menu"},
    "X": {"remote": "EXIT", "desc": "Exit. Often acts as a cancel key"},
    "U": {
        "remote": "HELP",
        "desc": "Displays on-screen help for highlighted menu item.",
    },
    "!": {
        "remote": "CLR",
        "desc": "(exclamation point) Force menu off (i.e. can use to assure menu is off for input selection)",
    },
    "i": {
        "remote": "INPUT",
        "desc": "(lower-case i as in igloo) Choose input (i.e. i2 for input 2 and i+2 for input 12)",
    },
    "L": {"remote": "ZONE", "desc": "Output zone select"},
    ":": {
        "remote": "ALT",
        "desc": "Alternate use of key. Example: ALT then 2.35 for 2.40 input aspect.",
    },
    "P": {"remote": "PREV", "desc": "Display previous input"},
    "e": {"remote": "PIP-OFF", "desc": "PIP off"},
    "p": {"remote": "PIP-SEL", "desc": "PIP select"},
    "r": {"remote": "PIP-SWAP", "desc": "PIP swap"},
    "m": {"remote": "PIP-MODE", "desc": "PIP mode"},
    "k": {"remote": "OK", "desc": "Accept command"},
    "<CR>": {
        "remote": "OK",
        "desc": 'Accept command (uses the PC "Enter" key notated as <CR>)',
    },
    "<": {"remote": "<", "desc": 'Left arrow ("less-than" key on keyboard)'},
    ">": {"remote": ">", "desc": 'Right arrow ("greater-than" key on keyboard)'},
    "v": {"remote": "v", "desc": 'Down arrow (lower-case v, as in "vote")'},
    "^": {"remote": "^", "desc": "Up arrow (shift 6 key on keyboard)"},
    "0": {"remote": "0", "desc": "Enter the digit 0"},
    "1": {"remote": "1", "desc": "Enter the digit 1"},
    "2": {"remote": "2", "desc": "Enter the digit 2"},
    "3": {"remote": "3", "desc": "Enter the digit 3"},
    "4": {"remote": "4", "desc": "Enter the digit 4"},
    "5": {"remote": "5", "desc": "Enter the digit 5"},
    "6": {"remote": "6", "desc": "Enter the digit 6"},
    "7": {"remote": "7", "desc": "Enter the digit 7"},
    "8": {"remote": "8", "desc": "Enter the digit 8"},
    "9": {"remote": "9", "desc": "Enter the digit 9"},
    "+": {"remote": "10+", "desc": "Add 10 to the next digit entered"},
    "N": {
        "remote": "NLS",
        "desc": "Non-Linear-Stretch. Send source aspect first, then send NLS",
    },
    "n": {
        "remote": "4:3",
        "desc": "Select 4:3 input source aspect. Use previous zoom setting.",
    },
    "[": {"remote": "4:3NZ", "desc": "Select 4:3 input source aspect. No zoom."},
    "l": {
        "remote": "LBOX",
        "desc": "(lower case l as in link) Select 4:3 letterbox input source aspect. Use previous zoom setting.",
    },
    "]": {
        "remote": "LBOXNZ",
        "desc": "Select 4:3 letterbox input source aspect. No zoom",
    },
    "w": {
        "remote": "16:9",
        "desc": "Select 16:9 input source aspect. Use previous zoom setting.",
    },
    "*": {"remote": "16:9NZ", "desc": "Select 16:9 input source aspect. No zoom."},
    "j": {
        "remote": "1.85",
        "desc": "Select 1.85 input source aspect. Use previous zoom setting.",
    },
    "/": {"remote": "1.85NZ", "desc": "Select 1.85 input source aspect. No zoom."},
    "A": {
        "remote": "1.90",
        "desc": "Select 1.90 input source aspect. (Radiance Pro only)",
    },
    "C": {
        "remote": "2.00",
        "desc": "Select 2.00 input source aspect. (Radiance Pro only)",
    },
    "E": {
        "remote": "2.20",
        "desc": "Select 2.20 input source aspect. (Radiance Pro only)",
    },
    "W": {
        "remote": "2.35",
        "desc": "Select 2.35 input source aspect. Use previous zoom setting.",
    },
    "K": {"remote": "2.35NZ", "desc": "Select 2.35 input source aspect. No zoom."},
    "G": {
        "remote": "2.40",
        "desc": "Select 2.40 input source aspect. (Radiance Pro only)",
    },
    "a": {"remote": "MEMA", "desc": "Select MEMA"},
    "b": {"remote": "MEMB", "desc": "Select MEMB"},
    "c": {"remote": "MEMC", "desc": "Select MEMC"},
    "d": {"remote": "MEMD", "desc": "Select MEMD"},
    "g": {"remote": "NA", "desc": "Onscreen messages on"},
    "s": {"remote": "NA", "desc": "Onscreen messages off"},
    "V": {"remote": "AAD", "desc": "Auto Aspect Disable (Radiance Pro only)"},
    "?": {"remote": "AAE", "desc": "Auto Aspect Enable (Radiance Pro only)"},
    "S": {
        "remote": "Save",
        "desc": "Shortcut to do a Save. To save, send Save and then OK",
    },
    "Y": {
        "remote": "HDR_Setup",
        "desc": "Show HDR Parameter menu. (Radiance Pro only)",
    },
    "H": {"remote": "Pattern", "desc": "Show test pattern. (Radiance Pro only)"},
    "_": {
        "remote": "NA",
        "desc": "(underscore) Underscore is a no-operation character and is always ignored",
    },
}
