"""Tests for the `lumagen.models` module."""

from unittest.mock import MagicMock

from lumagen.constants import DeviceStatus, StateStatus
from lumagen.models import (
    BaseDeviceId,
    BaseFullInfo,
    BaseInputBasicInfo,
    BaseInputVideo,
    BaseOperationalState,
    BaseOutputBasicInfo,
    BaseOutputMode,
    DeviceInfo,
    Frame3DTypeEnum,
    InputStatus,
)
from pydantic import ValidationError
import pytest


@pytest.mark.parametrize(
    ("software_revision", "model_number", "serial_number"),
    [
        (1, 100, 12345),  # Standard valid input
        (None, None, None),  # Allowing None values
        (999, 500, 67890),  # Different valid values
    ],
)
def test_base_device_id(software_revision, model_number, serial_number) -> None:
    """Test instantiation of BaseDeviceId with various valid data inputs."""
    device = BaseDeviceId(
        software_revision=software_revision,
        model_number=model_number,
        serial_number=serial_number,
    )

    assert device.software_revision == software_revision
    assert device.model_number == model_number
    assert device.serial_number == serial_number


@pytest.mark.parametrize(
    ("software_revision", "model_number", "serial_number"),
    [
        (-1, None, None),  # Negative software_revision should fail
        (None, -100, None),  # Negative model_number should fail
        (None, None, -12345),  # Negative serial_number should fail
    ],
)
def test_base_device_id_invalid(software_revision, model_number, serial_number) -> None:
    """Test validation errors for BaseDeviceId with invalid data."""
    with pytest.raises(ValidationError):
        BaseDeviceId(
            software_revision=software_revision,
            model_number=model_number,
            serial_number=serial_number,
        )


@pytest.mark.parametrize(
    ("logical_input", "physical_input"),
    [
        (2, 5),  # Valid case
        (0, 1),  # Edge case: lowest valid values
        (10, 10),  # Edge case: highest valid values
        (None, None),  # None values should be accepted
    ],
)
def test_base_input_basic_info(logical_input, physical_input) -> None:
    """Test BaseInputBasicInfo with various valid inputs."""
    input_info = BaseInputBasicInfo(
        logical_input=logical_input, physical_input=physical_input
    )

    assert input_info.logical_input == logical_input
    assert input_info.physical_input == physical_input


@pytest.mark.parametrize(
    ("logical_input", "physical_input"),
    [
        (-1, None),  # Negative logical_input should fail
        (None, 20),  # Out-of-range physical_input (valid range: 1-10) should fail
        (-5, 15),  # Both values invalid
    ],
)
def test_base_input_basic_info_invalid(logical_input, physical_input) -> None:
    """Test invalid values in BaseInputBasicInfo."""
    with pytest.raises(ValidationError):
        BaseInputBasicInfo(logical_input=logical_input, physical_input=physical_input)


@pytest.mark.parametrize(
    ("input_vertical_rate", "expected_vertical_rate"),
    [
        (6000, 60.0),  # Integer input
        (60.0, 60.0),  # Float input (unchanged)
        ("6000", 60.0),  # String input (converted)
        (None, None),  # None should remain None
    ],
)
def test_base_input_video_vertical_rate(
    input_vertical_rate, expected_vertical_rate
) -> None:
    """Test BaseInputVideo input_vertical_rate validation."""
    video = BaseInputVideo(input_vertical_rate=input_vertical_rate)
    assert video.input_vertical_rate == expected_vertical_rate


@pytest.mark.parametrize(
    ("input_interlaced", "expected_interlaced"),
    [
        ("1", "Interlaced"),  # Known conversion
        ("0", "Progressive"),  # Known conversion
        ("Unknown", "Unknown"),  # Unknown values should remain unchanged
        (None, None),  # None should remain None
    ],
)
def test_base_input_video_interlaced(input_interlaced, expected_interlaced) -> None:
    """Test BaseInputVideo input_interlaced validation."""
    assert (
        BaseInputVideo(input_interlaced=input_interlaced).input_interlaced
        == expected_interlaced
    )

    with pytest.raises(ValidationError, match="Invalid type for vertical_rate: list"):
        BaseInputVideo(input_vertical_rate=[6000])

    with pytest.raises(ValidationError, match="Invalid type for vertical_rate: dict"):
        BaseInputVideo(input_vertical_rate={"rate": 6000})  # Passing a dict

    with pytest.raises(TypeError, match="Invalid type for vertical_rate: bool"):
        BaseInputVideo(input_vertical_rate=True)  # Passing a boolean


@pytest.mark.parametrize(
    ("input_3d_type", "expected_value"),
    [
        (Frame3DTypeEnum.OFF, Frame3DTypeEnum.OFF),  # Valid case
        (Frame3DTypeEnum.FRAME_PACKED, Frame3DTypeEnum.FRAME_PACKED),
        (Frame3DTypeEnum.TOP_BOTTOM, Frame3DTypeEnum.TOP_BOTTOM),
        (Frame3DTypeEnum.SIDE_BY_SIDE, Frame3DTypeEnum.SIDE_BY_SIDE),
        (None, None),  # None should remain None
    ],
)
def test_base_input_video_3d_type_valid(input_3d_type, expected_value) -> None:
    """Test valid input_3d_type values in BaseInputVideo."""
    video = BaseInputVideo(input_3d_type=input_3d_type)
    assert video.input_3d_type == expected_value


@pytest.mark.parametrize(
    "invalid_value",
    [
        "invalid",  # String not in Enum
        10,  # Integer not defined in Enum
        [],  # List type
        {},  # Dict type
        True,  # Boolean type
    ],
)
def test_base_input_video_3d_type_invalid(invalid_value) -> None:
    """Test invalid input_3d_type values in BaseInputVideo."""
    with pytest.raises(ValidationError):
        BaseInputVideo(input_3d_type=invalid_value)


@pytest.mark.parametrize(
    ("input_video_status", "expected_value"),
    [
        (InputStatus.NONE, InputStatus.NONE),  # Valid case
        (InputStatus.VIDEO_ACTIVE, InputStatus.VIDEO_ACTIVE),
        (InputStatus.TEST_PATTERN_ACTIVE, InputStatus.TEST_PATTERN_ACTIVE),
        (None, None),  # None should remain None
    ],
)
def test_base_input_video_status_valid(input_video_status, expected_value) -> None:
    """Test valid input_video_status values in BaseInputVideo."""
    video = BaseInputVideo(input_video_status=input_video_status)
    assert video.input_video_status == expected_value


@pytest.mark.parametrize(
    ("input_vertical_rate", "expected"),
    [
        (None, None),  # None should remain None
    ],
)
def test_base_input_video_none(input_vertical_rate, expected) -> None:
    """Test None values in BaseInputVideo."""
    video_info = BaseInputVideo(input_vertical_rate=input_vertical_rate)
    assert video_info.input_vertical_rate == expected


@pytest.mark.parametrize(
    "invalid_input",
    [
        "invalid",  # Non-numeric string should fail
        {},  # Dictionary should fail
        [],  # List should fail
    ],
)
def test_base_input_video_invalid(invalid_input) -> None:
    """Test invalid values in BaseInputVideo."""
    with pytest.raises(ValidationError):
        BaseInputVideo(input_vertical_rate=invalid_input)


@pytest.mark.parametrize("invalid_boolean", [True, False])
def test_base_input_video_invalid_boolean(invalid_boolean) -> None:
    """Test invalid boolean values in BaseInputVideo."""
    with pytest.raises(TypeError, match="Invalid type for vertical_rate: bool"):
        BaseInputVideo(input_vertical_rate=invalid_boolean)


@pytest.mark.parametrize(
    ("valid_data", "expected_values"),
    [
        (
            {
                "field.0": 1,
                "field.1": "059",
                "field.2": 1080,
                "field.3": 2,
                "field.4": 5,
                "field.5": 16,
                "field.6": 9,
                "field.7": "N",
                "field.8": 2,
                "field.9": "F",
                "field.10": 3,
                "field.11": 3,
                "field.12": "059",
                "field.13": 2160,
                "field.14": 16,
                "field.15": "1",
                "field.16": "0",
                "field.17": "p",
                "field.18": "P",
                "field.19": 8,
                "field.20": 3,
                "field.21": 4,
                "field.22": 9,
            },
            {
                "input_status": 1,
                "source_vertical_rate": 59.94,  # Transformed
                "source_vertical_resolution": 1080,
                "source_3d_mode": 2,
                "active_input_config_number": 5,
                "source_raster_aspect": 16,
                "current_source_content_aspect": 9,
                "nls_active": "NLS",  # Transformed
                "output_3d_mode": 2,
                "output_on": {
                    "video_out1": "On",
                    "video_out2": "On",
                    "video_out3": "On",
                    "video_out4": "On",
                },  # Hex "F" -> all On
                "active_output_cms": 3,
                "active_output_style": 3,
                "output_vertical_rate": 59.94,  # Transformed
                "output_vertical_resolution": 2160,
                "output_aspect": 16,
                "output_colorspace": 709,  # Transformed
                "source_dynamic_range": "SDR",  # Transformed
                "source_mode": "Progressive",  # Transformed
                "output_mode": "Progressive",  # Transformed
                "virtual_input_selected": 8,
                "physical_input_selected": 3,
                "detected_source_raster_aspect": 4,
                "detected_source_aspect": 9,
            },
        )
    ],
)
def test_base_full_info_valid(valid_data, expected_values) -> None:
    """Test BaseFullInfo with valid data."""
    response = BaseFullInfo(**valid_data)

    for field, expected_value in expected_values.items():
        assert getattr(response, field) == expected_value, f"Mismatch in {field}"


@pytest.mark.parametrize(
    ("input_value", "expected_output"),
    [
        (
            {"video_out1": "On", "video_out2": "Off"},
            {"video_out1": "On", "video_out2": "Off"},
        ),  # Already a dictionary
    ],
)
def test_validate_output_on_valid_dict(input_value, expected_output) -> None:
    """Test validate_output_on when input is already a valid dictionary."""
    assert BaseFullInfo.validate_output_on(input_value) == expected_output


@pytest.mark.parametrize(
    ("input_value", "expected_output"),
    [
        ("X", None),  # Invalid value not in lookup map
        ("", None),  # Empty string should return None
        (None, None),  # None input should return None
    ],
)
def test_validate_nls_active_returns_none(input_value, expected_output) -> None:
    """Test validate_nls_active returns None for values not in the lookup map."""
    assert BaseFullInfo.validate_nls_active(input_value) == expected_output


@pytest.mark.parametrize(
    ("input_value", "expected_output"),
    [
        (0, 601),  # Integer input should be converted to string and mapped correctly
        (1, 709),
        (2, 2020),
        (3, 2100),
    ],
)
def test_validate_output_colorspace_int_input(input_value, expected_output) -> None:
    """Test validate_output_colorspace with integer inputs."""
    assert BaseFullInfo.validate_output_colorspace(input_value) == expected_output


@pytest.mark.parametrize(
    ("input_value", "expected_output"),
    [
        ("X", None),  # Invalid value not in lookup map
        ("", None),  # Empty string should return None
        (None, None),  # None input should return None
    ],
)
def test_validate_source_dynamic_range_returns_none(
    input_value, expected_output
) -> None:
    """Test validate_source_dynamic_range returns None for values not in the lookup map."""
    assert BaseFullInfo.validate_source_dynamic_range(input_value) == expected_output


@pytest.mark.parametrize(
    ("input_value", "expected_output"),
    [
        ("X", None),  # Invalid value not in lookup map
        ("", None),  # Empty string should return None
        (None, None),  # None input should return None
    ],
)
def test_validate_source_mode_returns_none(input_value, expected_output) -> None:
    """Test validate_source_mode returns None for values not in the lookup map."""
    assert BaseFullInfo.validate_source_mode(input_value) == expected_output


@pytest.mark.parametrize(
    ("input_value", "expected_output"),
    [
        ("X", None),  # Invalid value not in lookup map
        ("", None),  # Empty string should return None
        (None, None),  # None input should return None
    ],
)
def test_validate_output_mode_returns_none(input_value, expected_output) -> None:
    """Test validate_output_mode returns None for values not in the lookup map."""
    assert BaseFullInfo.validate_output_mode(input_value) == expected_output


@pytest.mark.parametrize(
    ("invalid_data", "expected_error_part"),
    [
        ({"source_vertical_rate": "invalid"}, "could not convert string to float"),
        ({"output_on": "ZZ"}, "Invalid hexadecimal value"),
        ({"output_on": 123}, "Expected a hexadecimal string for output_on"),
        ({"output_colorspace": "9"}, "Invalid colorspace value"),
        ({"output_vertical_rate": "invalid"}, "could not convert string to float"),
        ({"active_output_cms": 10}, "Input should be less than or equal to 7"),
        ({"virtual_input_selected": 0}, "Input should be greater than or equal to 1"),
        ({"physical_input_selected": 20}, "Input should be less than or equal to 19"),
    ],
)
def test_base_full_info_invalid(invalid_data, expected_error_part) -> None:
    """Test BaseFullInfo with invalid values (should raise ValidationError or TypeError)."""
    with pytest.raises((ValidationError, TypeError)) as exc_info:
        BaseFullInfo(**invalid_data)

    # Extract the actual error message
    actual_error_message = str(exc_info.value)

    # Ensure the expected error part is in the actual error message
    assert (
        expected_error_part in actual_error_message
    ), f"Expected '{expected_error_part}', but got:\n{actual_error_message}"


@pytest.mark.parametrize(
    ("auto_aspect", "game_mode", "device_status"),
    [
        ("Enabled", "Enabled", "Active"),  # Valid inputs
        (None, None, None),  # None values should remain None
    ],
)
def test_base_operational_state_valid(auto_aspect, game_mode, device_status) -> None:
    """Test BaseOperationalState with valid and None inputs."""
    state = BaseOperationalState(
        auto_aspect=auto_aspect,
        game_mode=game_mode,
        device_status=device_status,
    )

    assert state.auto_aspect == auto_aspect
    assert state.game_mode == game_mode
    assert state.device_status == device_status


def test_base_operational_status_with_enum() -> None:
    """Test that convert_status returns the same instance if it's already a valid Enum."""

    info_mock = MagicMock()

    # Test with StateStatus
    info_mock.field_name = "auto_aspect"
    state_instance = StateStatus.ENABLED
    result = BaseOperationalState.convert_status(state_instance, info_mock)
    assert (
        result is state_instance
    ), "Expected function to return the same StateStatus instance"

    # Test with DeviceStatus
    info_mock.field_name = "device_status"
    device_instance = DeviceStatus.ACTIVE
    result = BaseOperationalState.convert_status(device_instance, info_mock)
    assert (
        result is device_instance
    ), "Expected function to return the same DeviceStatus instance"


@pytest.mark.parametrize(
    "invalid_data",
    [
        {"auto_aspect": "invalid"},  # Invalid auto_aspect
        {"game_mode": "invalid"},  # Invalid game_mode
        {"device_status": "invalid"},  # Invalid device_status
        {"auto_aspect": 123},  # Invalid type (should be string or None)
        {"game_mode": []},  # Invalid type (list)
        {"device_status": {}},  # Invalid type (dict)
    ],
)
def test_base_operational_state_invalid(invalid_data) -> None:
    """Test BaseOperationalState with invalid values (should raise ValidationError)."""
    with pytest.raises(ValidationError):
        BaseOperationalState(**invalid_data)


@pytest.mark.parametrize(
    ("input_data", "expected_output"),
    [
        # Valid transformation test
        (
            {
                "field.0": "3",
                "field.1": "1",
                "field.2": "0",
                "field.3": "2",
                "field.4": "3",
            },
            {
                "video_out1": "On",
                "video_out2": "Off",
                "video_out3": "Off",
                "video_out4": "Off",
                "audio_out1": "Off",
                "audio_out2": "On",
                "audio_out3": "On",
                "audio_out4": "On",
            },
        ),
        # Another valid case with different inputs
        (
            {
                "field.0": "0",
                "field.1": "3",
                "field.2": "2",
                "field.3": "1",
                "field.4": "0",
            },
            {
                "video_out1": "On",
                "video_out2": "On",
                "video_out3": "Off",
                "video_out4": "On",
                "audio_out1": "On",
                "audio_out2": "Off",
                "audio_out3": "Off",
                "audio_out4": "Off",
            },
        ),
        # Test case with None values
        (
            {
                "field.1": "1",
                "field.2": None,
                "field.3": None,
                "field.4": "3",
            },
            {
                "video_out1": "On",
                "video_out2": "Off",
                "video_out3": None,
                "video_out4": None,
                "audio_out1": None,
                "audio_out2": None,
                "audio_out3": "On",
                "audio_out4": "On",
            },
        ),
    ],
)
def test_base_output_basic_info(input_data, expected_output) -> None:
    """Test BaseOutputBasicInfo with valid transformations and None values."""
    output_info = BaseOutputBasicInfo(**input_data)

    for key, expected_value in expected_output.items():
        actual_value = getattr(output_info, key)
        assert (
            actual_value == expected_value
        ), f"Expected {key} to be {expected_value}, but got {actual_value}"


@pytest.mark.parametrize(
    "invalid_data",
    [
        {"field.0": -1},  # Out of range (should be between 0-7)
        {"field.0": 8},  # Out of range (should be between 0-7)
        {"field.2": "5"},  # Wrong type (should be int, but given as string)
        {"field.1": "invalid"},  # Completely invalid value
    ],
)
def test_base_output_basic_info_invalid(invalid_data) -> None:
    """Test BaseOutputBasicInfo with invalid values (should raise ValidationError)."""
    with pytest.raises(ValidationError):
        BaseOutputBasicInfo(**invalid_data)


@pytest.fixture
def base_output_instance():
    """Fixture to create a BaseOutputBasicInfo instance with test data."""
    return BaseOutputBasicInfo(
        field_1="raw1",
        field_2="raw2",
        field_3="raw3",
        field_4="raw4",
        output_config=3,
        video_out1="On",
        video_out2="Off",
    )


@pytest.mark.parametrize(
    ("exclude_raw_fields", "expected_raw_fields"),
    [
        (
            True,
            {"field_1": False, "field_2": False, "field_3": False, "field_4": False},
        ),
        (
            False,
            {
                "field_1": "raw1",
                "field_2": "raw2",
                "field_3": "raw3",
                "field_4": "raw4",
            },
        ),
    ],
)
def test_model_dump(
    exclude_raw_fields, expected_raw_fields, base_output_instance
) -> None:  # pylint: disable=redefined-outer-name
    """Test model_dump behavior with and without raw fields."""
    dumped_data = base_output_instance.model_dump(exclude_raw_fields=exclude_raw_fields)

    # Check raw fields presence
    for field, expected_value in expected_raw_fields.items():
        if expected_value is False:
            assert field not in dumped_data
        else:
            assert dumped_data[field] == expected_value

    # Ensure other fields exist
    assert dumped_data["output_config"] == 3
    assert dumped_data["video_out1"] == "On"
    assert dumped_data["video_out2"] == "Off"


@pytest.mark.parametrize(
    ("input_rate", "input_interlaced", "expected_rate", "expected_interlaced"),
    [
        ("6000", "1", 60.0, "Interlaced"),  # String input should convert
        (None, None, None, None),  # None should remain None
        (60.0, None, 60.0, None),  # Float input should remain unchanged
    ],
)
def test_base_output_mode_valid(
    input_rate, input_interlaced, expected_rate, expected_interlaced
) -> None:
    """Test BaseOutputMode transformations."""
    output_mode = BaseOutputMode(
        output_vertical_rate=input_rate, output_interlaced=input_interlaced
    )

    assert output_mode.output_vertical_rate == expected_rate
    assert output_mode.output_interlaced == expected_interlaced


@pytest.mark.parametrize(
    "invalid_data",
    [
        {"output_vertical_rate": "invalid"},  # Non-numeric string
        {"output_vertical_rate": ["invalid"]},  # List instead of number
        {"output_vertical_rate": {"rate": 60}},  # Dictionary instead of number
    ],
)
def test_base_output_mode_invalid(invalid_data) -> None:
    """Test BaseOutputMode with invalid values (should raise ValidationError)."""
    with pytest.raises(ValidationError):
        BaseOutputMode(**invalid_data)


@pytest.mark.parametrize(
    ("input_data", "expected_data"),
    [
        (
            {
                "model_name": "TestDevice",
                "serial_number": 12345,
                "input_vertical_rate": 6000,
            },
            {
                "model_name": "TestDevice",
                "serial_number": 12345,
                "input_vertical_rate": 6000,
            },
        ),
        (
            {
                "model_name": "AnotherDevice",
                "serial_number": 98765,
                "input_vertical_rate": 5999,
            },
            {
                "model_name": "AnotherDevice",
                "serial_number": 98765,
                "input_vertical_rate": 5999,
            },
        ),
    ],
)
def test_device_info_valid(input_data, expected_data) -> None:
    """Test valid DeviceInfo instances."""
    device = DeviceInfo(**input_data)

    for key, expected_value in expected_data.items():
        actual_value = getattr(device, key)
        assert (
            actual_value == expected_value
        ), f"Expected {key} to be {expected_value}, but got {actual_value}"


@pytest.mark.parametrize(
    "invalid_data",
    [
        {"serial_number": -1},  # Serial number should be non-negative
        {"input_vertical_rate": "invalid"},  # Invalid type
        {"serial_number": "not_a_number"},  # Invalid type
    ],
)
def test_device_info_invalid(invalid_data) -> None:
    """Test DeviceInfo with invalid values (should raise ValidationError)."""
    with pytest.raises(ValidationError):
        DeviceInfo(**invalid_data)
