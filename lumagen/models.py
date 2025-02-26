"""Data Models and Enumerations for the Device.

This module defines structured data representations used throughout the system.
It provides type-safe models for device metadata, input/output configurations, and status tracking.

Main Components:
----------------
- `BaseDeviceId`: Stores essential device identification details.
- `BaseInputBasicInfo`: Represents the basic configuration of input sources.
- `BaseInputVideo`: Captures input video details (resolution, refresh rate, etc.).
- `BaseFullInfo`: Aggregates multiple device information fields.
- `DeviceInfo`: Stores and manages real-time device status.

Dependencies:
-------------
- Uses `pydantic` for robust data validation.
- Provides enums for standardized status representation.
"""

from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from .constants import (
    DeviceStatus,
    Frame3DTypeEnum,
    InputMemoryEnum,
    InputStatus,
    StateStatus,
)


class BaseOperationalState(BaseModel):
    """Represents the device operational state."""

    auto_aspect: Annotated[StateStatus | None, Field(title="Auto Aspect")] = None
    game_mode: Annotated[StateStatus | None, Field(title="Game Mode")] = None
    output_color_format: Annotated[str | None, Field(title="Output Color Format")] = (
        None
    )

    device_status: Annotated[DeviceStatus | None, Field(title="Device Status")] = None

    is_alive: Annotated[bool, Field(title="Is Alive")] = False

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }

    STATE_STATUS_MAPPING: ClassVar[dict[str, StateStatus]] = {
        "1": StateStatus.ENABLED,
        "0": StateStatus.DISABLED,
        "Enabled": StateStatus.ENABLED,
        "Disabled": StateStatus.DISABLED,
    }

    DEVICE_STATUS_MAPPING: ClassVar[dict[str, DeviceStatus]] = {
        "1": DeviceStatus.ACTIVE,
        "0": DeviceStatus.STANDBY,
        "Active": DeviceStatus.ACTIVE,
        "Standby": DeviceStatus.STANDBY,
    }

    @field_validator("auto_aspect", "game_mode", "device_status", mode="before")
    @classmethod
    def convert_status(
        cls, value: str | int | None, info: ValidationInfo
    ) -> StateStatus | DeviceStatus | None:
        """Convert string/number values to corresponding Enums dynamically, allowing None."""
        if value is None:
            return None

        field_name = info.field_name

        mapping = (
            cls.STATE_STATUS_MAPPING
            if field_name in {"auto_aspect", "game_mode"}
            else cls.DEVICE_STATUS_MAPPING
        )

        if isinstance(value, (int, str)) and str(value) in mapping:
            return mapping[str(value)]
        if isinstance(value, (StateStatus, DeviceStatus)):
            return value

        raise ValueError(
            f"Invalid value: {value} for {field_name}. "
            f"Expected one of {list(mapping.keys())}, or None."
        )


class BaseDeviceId(BaseModel):
    """Represents the base device identification information.

    This model is used to store and validate the essential
    details of a device, including its model name, software revision,
    model number, and serial number.
    """

    model_name: Annotated[
        str | None, Field(alias="field.0", max_length=100, title="Model Name")
    ] = None
    software_revision: Annotated[
        int | None, Field(alias="field.1", ge=0, title="Software revision")
    ] = None
    model_number: Annotated[
        int | None, Field(alias="field.2", ge=0, title="Model number")
    ] = None
    serial_number: Annotated[
        int | None, Field(alias="field.3", ge=0, title="Serial number")
    ] = None

    model_config = {"populate_by_name": True}


class BaseInputBasicInfo(BaseModel):
    """Represents the basic information for an input configuration.

    This model captures details about the logical input, input memory,
    and physical input, ensuring they meet specified constraints.

    Attributes:
        logical_input (int | None): The logical input identifier. Must be a
            non-negative integer if provided.
        input_memory (InputMemoryEnum | None): The memory identifier for the
            input. Must be one of "A", "B", "C", or "D" if provided.
        physical_input (int | None): The physical input identifier. Must be
            a non-negative integer if provided.

    """

    logical_input: Annotated[
        int | None, Field(alias="field.0", ge=0, title="Logical Input")
    ] = None
    input_memory: Annotated[
        InputMemoryEnum | None, Field(alias="field.1", title="Input Memory")
    ] = None
    physical_input: Annotated[
        int | None, Field(alias="field.2", ge=1, le=10, title="Physical Input")
    ] = None

    model_config = {
        "populate_by_name": True,  # Allows fields to be populated using their aliases
        "use_enum_values": True,  # Ensures Enum fields are serialized using their values
    }


class BaseInputVideo(BaseModel):
    """Represents the input video configuration.

    Attributes:
        input_video_status (VideoStatusEnum | None): Video status. Must be one of:
            - NONE: 0
            - VIDEO_ACTIVE: 1
            - TEST_PATTERN_ACTIVE: 2
        input_vertical_rate (int | None): Vertical refresh rate multiplied by 100.
        input_horizontal_resolution (int | None): Horizontal resolution of the video.
        input_vertical_resolution (int | None): Vertical resolution of the video.
        input_interlaced (bool | None): True if the video is interlaced, False otherwise.
        input_3d_type (Input3DTypeEnum | None): Input 3D type. Must be one of:
            - OFF: 0
            - FRAME_PACKED: 2
            - TOP_BOTTOM: 4
            - SIDE_BY_SIDE: 8

    """

    input_video_status: Annotated[
        InputStatus | None, Field(alias="field.0", title="Video Status")
    ] = None
    input_vertical_rate: Annotated[
        float | None,
        Field(
            alias="field.1",
            ge=0,
            title="Vertical Rate",
            description="Vertical refresh rate in Hz",
        ),
    ] = None
    input_horizontal_resolution: Annotated[
        int | None,
        Field(
            alias="field.2",
            ge=0,
            title="Horizontal Resolution",
            description="Horizontal resolution of the video",
        ),
    ] = None
    input_vertical_resolution: Annotated[
        int | None,
        Field(
            alias="field.3",
            ge=0,
            title="Vertical Resolution",
            description="Vertical resolution of the video",
        ),
    ] = None
    input_interlaced: Annotated[
        str | None, Field(alias="field.4", title="Interlaced")
    ] = None
    input_3d_type: Annotated[
        Frame3DTypeEnum | None, Field(alias="field.5", title="Input 3D Type")
    ] = None

    @field_validator("input_vertical_rate", mode="before")
    @classmethod
    def transform_input_vertical_rate(cls, value) -> float | None:
        """Convert vertical rate from a string or integer (e.g., '6000') to a float (e.g., 60.0)."""
        if value is None:
            return value

        if isinstance(value, bool):  # Explicitly reject booleans
            raise TypeError(f"Invalid type for vertical_rate: {type(value).__name__}")

        if isinstance(value, float):
            # If it's already a float, assume it's already transformed
            return value

        if isinstance(value, str):
            # Ensure the string contains only digits
            if not value.isdigit():
                raise ValueError(f"Invalid input_vertical_rate string: {value}")
            value = int(value)  # Convert string to integer

        if isinstance(value, int):
            return value / 100  # Perform the division

        raise ValueError(f"Invalid type for vertical_rate: {type(value).__name__}")

    @field_validator("input_interlaced", mode="before")
    @classmethod
    def validate_input_interlaced(cls, value: str) -> str:
        """Validate and map `input_interlaced` based on the Lookup map."""
        lookup_map = {"1": "Interlaced", "0": "Progressive"}
        if value not in lookup_map:
            return value
        return lookup_map[value]

    model_config = {
        "populate_by_name": True,
        "use_enum_values": False,
    }


class BaseFullInfo(BaseModel):
    """Represents the full version 1 information properties.

    This class encapsulates various input, output, and source properties with detailed metadata.
    It supports population of fields using their alias or name, enabled via the model configuration.
    """

    input_status: Annotated[
        InputStatus | None, Field(alias="field.0", title="Input Status")
    ] = None

    source_vertical_rate: Annotated[
        float | None, Field(alias="field.1", title="Vertical Rate")
    ] = None

    source_vertical_resolution: Annotated[
        int | None, Field(alias="field.2", title="Vertical Resolution")
    ] = None

    source_3d_mode: Annotated[
        Frame3DTypeEnum | None, Field(alias="field.3", title="Source 3D Mode")
    ] = None

    active_input_config_number: Annotated[
        int | None, Field(alias="field.4", title="Input Config")
    ] = None

    source_raster_aspect: Annotated[
        int | None, Field(alias="field.5", title="Raster Aspect")
    ] = None

    current_source_content_aspect: Annotated[
        int | None, Field(alias="field.6", title="Content Aspect")
    ] = None

    nls_active: Annotated[str | None, Field(alias="field.7", title="NLS Active")] = None

    output_3d_mode: Annotated[
        Frame3DTypeEnum | None, Field(alias="field.8", title="Output 3D Mode")
    ] = None

    output_on: Annotated[
        dict[str, str] | None, Field(alias="field.9", title="Output On")
    ] = None

    active_output_cms: Annotated[
        int | None, Field(alias="field.10", ge=0, le=7, title="Output CMS")
    ] = None

    active_output_style: Annotated[
        int | None, Field(alias="field.11", ge=0, le=7, title="Output Style")
    ] = None

    output_vertical_rate: Annotated[
        float | None, Field(alias="field.12", title="Output Rate")
    ] = None

    output_vertical_resolution: Annotated[
        int | None, Field(alias="field.13", title="Output Resolution")
    ] = None

    output_aspect: Annotated[
        int | None, Field(alias="field.14", title="Output Aspect")
    ] = None

    # Additional V2 attributes
    output_colorspace: Annotated[
        int | None, Field(alias="field.15", title="Output Colorspace")
    ] = None

    source_dynamic_range: Annotated[
        str | None, Field(alias="field.16", title="Current Input Dynamic Range")
    ] = None

    source_mode: Annotated[
        str | None, Field(alias="field.17", title="Current Input Mode")
    ] = None

    output_mode: Annotated[str | None, Field(alias="field.18", title="Output Mode")] = (
        None
    )

    # Additional V3 attributes
    virtual_input_selected: Annotated[
        int | None, Field(alias="field.19", ge=1, le=19, title="Virtual Input Selected")
    ] = None

    physical_input_selected: Annotated[
        int | None,
        Field(alias="field.20", ge=1, le=19, title="Physical Input Selected"),
    ] = None

    # Additional V4 attributes
    detected_source_raster_aspect: Annotated[
        int | None,
        Field(alias="field.21", title="Detected Source Raster Aspect"),
    ] = None

    detected_source_aspect: Annotated[
        int | None,
        Field(alias="field.22", title="Detected Source Aspect"),
    ] = None

    model_config = {"populate_by_name": True}

    @field_validator("output_vertical_rate", "source_vertical_rate", mode="before")
    @classmethod
    def validate_vertical_rate(cls, value: str) -> float:
        """If value is '059', change it to 59.94; otherwise, convert it to a float."""
        if value == "059":
            return 59.94
        return float(value)

    @field_validator("output_on", mode="before")
    @classmethod
    def validate_output_on(cls, value: str) -> dict:
        """Validate and transform `output_on` to a dictionary representation."""
        if isinstance(value, dict):
            return value

        if not isinstance(value, str):
            raise TypeError("Expected a hexadecimal string for output_on.")

        try:
            binary = f"{int(value, 16):04b}"  # Convert to 4-bit binary
        except ValueError as ve:
            raise ValueError(f"Invalid hexadecimal value: {value}") from ve

        return {
            f"video_out{i+1}": "On" if bit == "1" else "Off"
            for i, bit in enumerate(reversed(binary[:4]))
        }

    @field_validator("nls_active", mode="before")
    @classmethod
    def validate_nls_active(cls, value: str) -> str:
        """Validate and map `nls_active` based on the Lookup map."""
        lookup_map = {"-": "Normal", "N": "NLS"}
        if value not in lookup_map:
            return None
        return lookup_map[value]

    @field_validator("output_colorspace", mode="before")
    @classmethod
    def validate_output_colorspace(cls, value: str) -> int:
        """Validate and convert `output_colorspace` from string to integer."""
        if isinstance(value, int):
            value = str(value)
        value_map = {"0": 601, "1": 709, "2": 2020, "3": 2100}
        if value not in value_map:
            raise ValueError(
                f"Invalid colorspace value: {value}. Must be one of {list(value_map.keys())}."
            )
        return value_map[value]

    @field_validator("source_dynamic_range", mode="before")
    @classmethod
    def validate_source_dynamic_range(cls, value: str) -> str:
        """Validate and map `source_dynamic_range` based on the Lookup map."""
        lookup_map = {"0": "SDR", "1": "HDR"}
        if value not in lookup_map:
            return None
        return lookup_map[value]

    @field_validator("source_mode", mode="before")
    @classmethod
    def validate_source_mode(cls, value: str) -> str:
        """Validate and map `source_mode` based on the Lookup map."""
        lookup_map = {"i": "Interlaced", "p": "Progressive", "n": "No Source"}
        if value not in lookup_map:
            return None
        return lookup_map[value]

    @field_validator("output_mode", mode="before")
    @classmethod
    def validate_output_mode(cls, value: str) -> str:
        """Validate and map `output_mode` based on the Lookup map."""
        lookup_map = {"I": "Interlaced", "P": "Progressive"}
        if value not in lookup_map:
            return None
        return lookup_map[value]


class BaseOutputBasicInfo(BaseModel):
    """Represents basic output information.

    Attributes:
        output_config: Current output configuration (0-7).
        video_out1: Video on/off state for output 1.
        video_out2: Video on/off state for output 2.
        video_out3: Video on/off state for output 3.
        video_out4: Video on/off state for output 4.
        audio_out1: Audio on/off state for output 1.
        audio_out2: Audio on/off state for output 2.
        audio_out3: Audio on/off state for output 3.
        audio_out4: Audio on/off state for output 4.

    """

    # Raw fields
    field_1: Annotated[
        str | None, Field(alias="field.1", title="Raw Video State 1")
    ] = None
    field_2: Annotated[
        str | None, Field(alias="field.2", title="Raw Video State 2")
    ] = None
    field_3: Annotated[
        str | None, Field(alias="field.3", title="Raw Audio State 1")
    ] = None
    field_4: Annotated[
        str | None, Field(alias="field.4", title="Raw Audio State 2")
    ] = None

    # Processed fields
    output_config: Annotated[
        int | None, Field(alias="field.0", ge=0, le=7, title="Output Config")
    ] = None
    video_out1: Annotated[
        Literal["Off", "On"] | None, Field(title="Video Output 1")
    ] = None
    video_out2: Annotated[
        Literal["Off", "On"] | None, Field(title="Video Output 2")
    ] = None
    video_out3: Annotated[
        Literal["Off", "On"] | None, Field(title="Video Output 3")
    ] = None
    video_out4: Annotated[
        Literal["Off", "On"] | None, Field(title="Video Output 4")
    ] = None
    audio_out1: Annotated[
        Literal["Off", "On"] | None, Field(title="Audio Output 1")
    ] = None
    audio_out2: Annotated[
        Literal["Off", "On"] | None, Field(title="Audio Output 2")
    ] = None
    audio_out3: Annotated[
        Literal["Off", "On"] | None, Field(title="Audio Output 3")
    ] = None
    audio_out4: Annotated[
        Literal["Off", "On"] | None, Field(title="Audio Output 4")
    ] = None

    model_config = {"populate_by_name": True}

    @model_validator(mode="before")
    @classmethod
    def validate_fields(cls, values: dict) -> dict:
        """Ensure that field_1 through field_4 are within the range 0-3."""
        allowed_values = {"0", "1", "2", "3", None}

        for field in ["field.1", "field.2", "field.3", "field.4"]:
            if values.get(field) not in allowed_values:
                raise ValueError(f"{field} must be one of {allowed_values - {None}}.")

        return values

    @model_validator(mode="before")
    @classmethod
    def transform_fields(cls, values: dict) -> dict:
        """Transform raw fields into corresponding On/Off states using a dictionary comprehension.

        Handles:
        - Raw values: `0`, `1`, `2`, `3`.
        - Already valid states: `On`, `Off`.
        """

        # State mapping
        state_map = {
            "0": ("Off", "Off"),
            "1": ("On", "Off"),
            "2": ("Off", "On"),
            "3": ("On", "On"),
        }

        # Dictionary comprehension for transformation
        transformed_values = {
            output: (
                None
                if values.get(field) is None
                else (
                    state_map.get(values[field], ("Off", "Off"))
                    if values.get(field) not in {"On", "Off"}
                    else (values[field],) * len(outputs)
                )[i]
            )
            for field, outputs in [
                ("field.1", ["video_out1", "video_out2"]),
                ("field.2", ["video_out3", "video_out4"]),
                ("field.3", ["audio_out1", "audio_out2"]),
                ("field.4", ["audio_out3", "audio_out4"]),
            ]
            if field in values  # Ensure the field exists in the input
            for i, output in enumerate(outputs)
        }

        # Merge transformed values into the original dictionary
        values.update(transformed_values)
        return values

    def model_dump(self, *, exclude_raw_fields: bool = True, **kwargs) -> dict:
        """Override `model_dump` to exclude raw fields by default."""
        exclude = (
            {"field_1", "field_2", "field_3", "field_4"} if exclude_raw_fields else {}
        )
        return super().model_dump(exclude=exclude, **kwargs)


class BaseOutputMode(BaseModel):
    """Represents base output mode."""

    # Processed fields
    output_vertical_rate: Annotated[
        float | None, Field(alias="field.0", title="Vertical Rate")
    ] = None
    output_horizontal_resolution: Annotated[
        int | None, Field(alias="field.1", title="Horizontal Resolution")
    ] = None
    output_vertical_resolution: Annotated[
        int | None, Field(alias="field.2", title="Vertical Resolution")
    ] = None
    output_interlaced: Annotated[
        str | None, Field(alias="field.3", title="Interlaced")
    ] = None
    output_3d_mode: Annotated[
        Frame3DTypeEnum | None, Field(alias="field.4", title="3D Mode")
    ] = None

    model_config = {
        "populate_by_name": True,
        "use_enum_values": False,
    }

    @field_validator("output_vertical_rate", mode="before")
    @classmethod
    def transform_output_vertical_rate(cls, value: str) -> float:
        """Convert vertical rate from an integer (6000) to a float (60.0)."""
        if value is None:
            return value

        if isinstance(value, float):
            # If it's already a float, assume it's already transformed
            return value

        if isinstance(value, str):
            # Ensure the string contains only digits
            if not value.isdigit():
                raise ValueError(f"Invalid vertical_rate string: {value}")
            value = int(value)  # Convert string to integer

        if isinstance(value, int):
            return value / 100  # Perform the division

        raise ValueError(f"Invalid type for vertical_rate: {type(value).__name__}")

    @field_validator("output_interlaced", mode="before")
    @classmethod
    def validate_output_interlaced(cls, value: str) -> str:
        """Validate and map `output_interlaced` based on the Lookup map."""
        lookup_map = {"1": "Interlaced", "0": "Progressive"}
        if value not in lookup_map:
            return value
        return lookup_map[value]


class DeviceInfo(BaseModel):
    """A structured model for device information with validation and serialization."""

    active_input_config_number: int | None = Field(
        None, title="Active Input Config Number"
    )
    active_output_cms: int | None = Field(None, title="Active Output CMS")
    active_output_style: int | None = Field(None, title="Active Output Style")

    audio_out1: str | None = Field(None, title="Audio Output 1")
    audio_out2: str | None = Field(None, title="Audio Output 2")
    audio_out3: str | None = Field(None, title="Audio Output 3")
    audio_out4: str | None = Field(None, title="Audio Output 4")

    auto_aspect: str | None = None
    current_source_content_aspect: int | None = None
    detected_source_aspect: int | None = None
    detected_source_raster_aspect: int | None = None
    device_status: str | None = None
    game_mode: str | None = None
    input_3d_type: str | None = None
    input_horizontal_resolution: int | None = None
    input_interlaced: str | None = None
    input_memory: str | None = None
    input_status: str | None = None
    input_vertical_rate: float | None = None
    input_vertical_resolution: int | None = None
    input_video_status: str | None = None
    is_alive: bool | None = None
    logical_input: int | None = None

    model_name: str | None = None
    model_number: int | None = Field(None, ge=0, title="Model Number")
    nls_active: str | None = None

    output_3d_mode: str | None = None
    output_aspect: int | None = None
    output_color_format: str | None = None
    output_colorspace: int | None = None
    output_config: int | None = None
    output_horizontal_resolution: int | None = None
    output_interlaced: str | None = None
    output_mode: str | None = None
    output_vertical_rate: float | None = None
    output_vertical_resolution: int | None = None

    physical_input: int | None = None
    physical_input_selected: int | None = None
    serial_number: int | None = Field(None, ge=0, title="Serial Number")
    software_revision: int | None = None

    source_3d_mode: str | None = None
    source_dynamic_range: str | None = None
    source_mode: str | None = None
    source_raster_aspect: int | None = None
    source_vertical_rate: float | None = None
    source_vertical_resolution: int | None = None

    video_out1: str | None = None
    video_out2: str | None = None
    video_out3: str | None = None
    video_out4: str | None = None

    virtual_input_selected: int | None = None

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }
