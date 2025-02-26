"""Class for handling messages from the hardware device."""

from __future__ import annotations

from typing import ClassVar

from . import constants
from .models import (
    BaseDeviceId,
    BaseFullInfo,
    BaseInputBasicInfo,
    BaseInputVideo,
    BaseOutputBasicInfo,
    BaseOutputMode,
)
from .utils import LoggingMixin

MESSAGE_TYPE_REQUEST = "request"
MESSAGE_TYPE_RESPONSE = "response"
MESSAGE_TYPE_EVENT = "event"

registry = {}


def register(cls):
    """Register a message response class for factory use."""
    registry[cls.name] = cls
    return cls


class MessageParser(LoggingMixin):
    """Class for parsing messages from the hardware device."""

    def __init__(self, message: str) -> None:
        """Parse string message into its fields."""
        super().__init__()
        self.fields: list[str] = []
        self.message = message
        self.name: str = ""

        if "POWER OFF." in self.message:
            self.message = "!S02,0"
        elif "Power-up complete." in self.message:
            self.message = "!S02,1"
        elif self.message.startswith("#ZQS1"):
            self.name = constants.DEVICE_LABEL_QUERY
            fields = self.message.split("!")
            label_id = fields[0][5:]
            value = fields[1].split(",")[1]
            self.fields = [label_id, value]

        if self.name == "":
            self._parse_fields()
            if len(self.fields) > 0:
                self._parse_name()

    def _parse_fields(self) -> None:
        pos = self.message.rfind("!")
        if pos != -1:
            self.fields = self.message[pos + 1 :].split(",")
            self.message = self.message[pos:]

    def _parse_name(self) -> None:
        self.name = self.fields[0]
        self.fields.pop(0)

    def to_dict(self) -> dict[str, str]:
        """Convert fields into a dict with dynamic keys like field.0, field.1, etc."""
        return {f"field.{i}": value for i, value in enumerate(self.fields)}

    def __str__(self) -> str:
        """Str."""
        return self.message

    def __repr__(self) -> str:
        """Repr."""
        return (
            f"{type(self).__name__}("
            f"message='{self.message}', "
            f"name='{self.name}', "
            f"fields={self.fields}, "
            ")"
        )


class Response:
    """Represents a command response from the hardware device."""

    name: str = ""

    def __init__(self, parsed: MessageParser) -> None:
        """Initialize the response."""
        self._fields = parsed.fields

    @classmethod
    def factory(cls, message: str) -> Response:
        """Create a new response object based on the message type."""
        parsed = MessageParser(message)
        if parsed.name in registry:
            return registry[parsed.name](parsed)
        return cls(parsed)

    @property
    def fields(self) -> list:
        """Return the fields in the message."""
        return self._fields


@register
class StatusAlive(Response):
    """Class for DEVICE ALIVE messages."""

    name = constants.STATUS_ALIVE

    @property
    def field_is_alive(self) -> str:
        """Returns alive status."""
        return self.fields[0] == "Ok"


@register
class StatusID(BaseDeviceId):
    """StatusID."""

    name: ClassVar[str] = constants.STATUS_ID

    def __init__(self, parsed: MessageParser) -> None:
        """Initialize."""
        super().__init__(**parsed.to_dict())


@register
class PowerState(Response):
    """Class for Device Power State messages."""

    name = constants.STATUS_POWER

    @property
    def field_device_status(self) -> str:
        """Returns power status."""
        return self.fields[0]


@register
class InputBasicInfo(BaseInputBasicInfo):
    """Class for Device Basic Input Info messages."""

    name: ClassVar[str] = constants.INPUT_BASIC_INFO

    def __init__(self, parsed: MessageParser) -> None:
        """Initialize."""
        super().__init__(**parsed.to_dict())


@register
class InputVideo(BaseInputVideo):
    """Class for Device Basic Input Info messages."""

    name: ClassVar[str] = constants.INPUT_VIDEO

    def __init__(self, parsed: MessageParser) -> None:
        """Initialize."""
        super().__init__(**parsed.to_dict())


@register
class FullInfoV1(BaseFullInfo):
    """Class for Device Full Info V1 messages."""

    name: ClassVar[str] = constants.DEVICE_FULL_V1

    def __init__(self, parsed: MessageParser) -> None:
        """Initialize."""
        super().__init__(**parsed.to_dict())


@register
class FullInfoV2(BaseFullInfo):
    """Class for Device Full Info V2 messages."""

    name: ClassVar[str] = constants.DEVICE_FULL_V2

    def __init__(self, parsed: MessageParser) -> None:
        """Initialize."""
        super().__init__(**parsed.to_dict())


@register
class FullInfoV3(BaseFullInfo):
    """Class for Device Full Info V3 messages."""

    name: ClassVar[str] = constants.DEVICE_FULL_V3

    def __init__(self, parsed: MessageParser) -> None:
        """Initialize."""
        super().__init__(**parsed.to_dict())


@register
class FullInfoV4(BaseFullInfo):
    """Class for Device Full Info V4 messages."""

    name: ClassVar[str] = constants.DEVICE_FULL_V4

    def __init__(self, parsed: MessageParser) -> None:
        """Initialize."""
        super().__init__(**parsed.to_dict())


@register
class AutoAspect(Response):
    """Class for DEVICE_AUTOASPECT_QUERY messages."""

    name = constants.DEVICE_AUTOASPECT_QUERY

    @property
    def field_auto_aspect(self) -> str:
        """Returns AutoAspect Mode."""
        return self._fields[0]


@register
class GameMode(Response):
    """Class for DEVICE_GAMEMODE_QUERY messages."""

    name = constants.DEVICE_GAMEMODE_QUERY

    @property
    def field_game_mode(self) -> str:
        """Returns Game Mode."""
        return self._fields[0]


@register
class OutputBasicInfo(BaseOutputBasicInfo):
    """Class for Device Basic Output Info messages."""

    name: ClassVar[str] = constants.DEVICE_BASIC_OUTPUT_INFO

    def __init__(self, parsed: MessageParser) -> None:
        """Initialize."""
        super().__init__(**parsed.to_dict())


@register
class OutputMode(BaseOutputMode):
    """Class for Device Output Mode messages."""

    name: ClassVar[str] = constants.DEVICE_OUTPUT_MODE

    def __init__(self, parsed: MessageParser) -> None:
        """Initialize."""
        super().__init__(**parsed.to_dict())


@register
class OutputColorFormat(Response):
    """Class for DEVICE_OUTPUT_COLOR_FORMAT messages."""

    name = constants.DEVICE_OUTPUT_COLOR_FORMAT

    index = {
        "output_color_format": {
            0: constants.OUTPUT_COLOR_FORMAT_422,
            1: constants.OUTPUT_COLOR_FORMAT_444,
            2: constants.OUTPUT_COLOR_FORMAT_RGB_VIDEO_LEVEL,
            3: constants.OUTPUT_COLOR_FORMAT_RGB_PC_LEVEL,
            4: constants.OUTPUT_COLOR_FORMAT_420,
        }
    }

    @property
    def field_output_color_format(self) -> str:
        """Returns Output Color Format."""
        return self.index["output_color_format"][int(self._fields[0])]


@register
class LabelQuery(Response):
    """Class for LABEL QUERY messages."""

    name = constants.DEVICE_LABEL_QUERY

    @property
    def field_label_index(self) -> str:
        """Returns Label Index."""
        return self._fields[0]

    @property
    def field_label_name(self) -> str:
        """Returns Label Name."""
        return self._fields[1]
