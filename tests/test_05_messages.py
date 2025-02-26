"""Tests for the `lumagen.messages` module."""

from lumagen import constants
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
import pytest


@pytest.mark.parametrize(
    ("message", "expected_name", "expected_fields"),
    [
        ("POWER OFF.", "S02", ["0"]),
        ("Power-up complete.", "S02", ["1"]),
        ("#UNKNOWN", "", []),
        ("#ZQS1A9!S1A,Input", constants.DEVICE_LABEL_QUERY, ["A9", "Input"]),
    ],
)
def test_message_parser(message, expected_name, expected_fields) -> None:
    """Test parsing messages with MessageParser."""
    parser = MessageParser(message)
    assert parser.name == expected_name
    assert parser.fields == expected_fields


def test_message_parser_to_dict() -> None:
    """Test converting parsed message to dictionary."""
    parser = MessageParser("!NAME,FIELD1,FIELD2,FIELD3")
    expected_dict = {"field.0": "FIELD1", "field.1": "FIELD2", "field.2": "FIELD3"}
    assert parser.to_dict() == expected_dict


def test_message_parser_str_repr() -> None:
    """Test string and repr representation of MessageParser."""
    message = "!S02,1"
    parser = MessageParser(message)
    assert str(parser) == "!S02,1"
    assert "MessageParser" in repr(parser)


def test_response_factory_with_registered_class() -> None:
    """Test Response factory method with registered class."""
    message = f"!{constants.STATUS_ALIVE},Ok"
    response = Response.factory(message)
    assert isinstance(response, StatusAlive)
    assert response.field_is_alive is True


def test_response_factory_with_unregistered_class() -> None:
    """Test Response factory method with unregistered class."""
    message = "!UNKNOWN,DATA"
    response = Response.factory(message)
    assert isinstance(response, Response)
    assert response.fields == ["DATA"]


def test_status_alive() -> None:
    """Test parsing StatusAlive response."""
    message = f"!{constants.STATUS_ALIVE},Ok"
    response = StatusAlive(MessageParser(message))
    assert response.field_is_alive is True


def test_status_id() -> None:
    """Test parsing StatusID response."""
    message = f"!{constants.STATUS_ID},RadiancePro,101524,1018,001351"
    response = StatusID(MessageParser(message))
    assert response.name == constants.STATUS_ID
    assert response.model_name == "RadiancePro"
    assert response.software_revision == 101524
    assert response.model_number == 1018
    assert response.serial_number == 1351


def test_power_state() -> None:
    """Test parsing PowerState response."""
    message = f"!{constants.STATUS_POWER},On"
    response = PowerState(MessageParser(message))
    assert response.name == constants.STATUS_POWER
    assert response.field_device_status == "On"


def test_input_basic_info() -> None:
    """Test parsing InputBasicInfo response."""
    message = f"!{constants.INPUT_BASIC_INFO},2,A,5"
    response = InputBasicInfo(MessageParser(message))

    assert response.name == constants.INPUT_BASIC_INFO
    assert response.logical_input == 2
    assert response.input_memory == "A"
    assert response.physical_input == 5


def test_input_video() -> None:
    """Test parsing InputVideo response."""
    message = f"!{constants.INPUT_VIDEO},1,6000,1920,1080,1,2"
    response = InputVideo(MessageParser(message))

    assert response.name == constants.INPUT_VIDEO
    assert response.input_video_status == 1
    assert response.input_vertical_rate == 60.0
    assert response.input_horizontal_resolution == 1920
    assert response.input_vertical_resolution == 1080
    assert response.input_interlaced == "Interlaced"
    assert response.input_3d_type == 2


def test_full_info_v1() -> None:
    """Test parsing FullInfoV1 response."""
    message = f"!{constants.DEVICE_FULL_V1},1,059,1080,2,5,16,9,N,2,0,3,3,060,2160,16"
    response = FullInfoV1(MessageParser(message))

    assert response.name == constants.DEVICE_FULL_V1
    assert response.input_status == 1
    assert response.source_vertical_rate == 59.94
    assert response.source_vertical_resolution == 1080
    assert response.source_3d_mode == 2
    assert response.active_input_config_number == 5
    assert response.source_raster_aspect == 16
    assert response.current_source_content_aspect == 9
    assert response.nls_active == "NLS"
    assert response.output_3d_mode == 2
    assert response.output_on == {
        "video_out1": "Off",
        "video_out2": "Off",
        "video_out3": "Off",
        "video_out4": "Off",
    }
    assert response.active_output_cms == 3
    assert response.active_output_style == 3
    assert response.output_vertical_rate == 60.0
    assert response.output_vertical_resolution == 2160
    assert response.output_aspect == 16


def test_full_info_v2() -> None:
    """Test parsing FullInfoV2 response."""
    message = f"!{constants.DEVICE_FULL_V2},1,059,1080,2,5,16,9,N,2,0,3,3,060,2160,16,1,0,p,P,8,3,4,9"
    response = FullInfoV2(MessageParser(message))

    assert response.name == constants.DEVICE_FULL_V2
    assert response.input_status == 1
    assert response.source_vertical_rate == 59.94
    assert response.source_vertical_resolution == 1080
    assert response.source_3d_mode == 2
    assert response.active_input_config_number == 5
    assert response.source_raster_aspect == 16
    assert response.current_source_content_aspect == 9
    assert response.nls_active == "NLS"
    assert response.output_3d_mode == 2
    assert response.output_on == {
        "video_out1": "Off",
        "video_out2": "Off",
        "video_out3": "Off",
        "video_out4": "Off",
    }
    assert response.active_output_cms == 3
    assert response.active_output_style == 3
    assert response.output_vertical_rate == 60.0
    assert response.output_vertical_resolution == 2160
    assert response.output_aspect == 16
    assert response.output_colorspace == 709
    assert response.source_dynamic_range == "SDR"
    assert response.source_mode == "Progressive"
    assert response.output_mode == "Progressive"
    assert response.virtual_input_selected == 8
    assert response.physical_input_selected == 3
    assert response.detected_source_raster_aspect == 4
    assert response.detected_source_aspect == 9


def test_full_info_v3() -> None:
    """Test parsing FullInfoV3 response."""
    message = f"!{constants.DEVICE_FULL_V3},1,059,1080,2,5,16,9,N,2,2,3,3,060,2160,16,1,0,p,P,8,3"
    response = FullInfoV3(MessageParser(message))

    assert response.name == constants.DEVICE_FULL_V3
    assert response.input_status == 1
    assert response.source_vertical_rate == 59.94
    assert response.source_vertical_resolution == 1080
    assert response.source_3d_mode == 2
    assert response.active_input_config_number == 5
    assert response.source_raster_aspect == 16
    assert response.current_source_content_aspect == 9
    assert response.nls_active == "NLS"
    assert response.output_3d_mode == 2
    assert response.output_on == {
        "video_out1": "Off",
        "video_out2": "On",
        "video_out3": "Off",
        "video_out4": "Off",
    }
    assert response.active_output_cms == 3
    assert response.active_output_style == 3
    assert response.output_vertical_rate == 60.0
    assert response.output_vertical_resolution == 2160
    assert response.output_aspect == 16
    assert response.output_colorspace == 709
    assert response.source_dynamic_range == "SDR"
    assert response.source_mode == "Progressive"
    assert response.output_mode == "Progressive"
    assert response.virtual_input_selected == 8
    assert response.physical_input_selected == 3


def test_full_info_v4() -> None:
    """Test parsing FullInfoV4 response."""
    message = f"!{constants.DEVICE_FULL_V4},0,060,1080,4,4,178,240,-,4,1,4,4,059,2160,178,2,1,i,P,1,2,240,178"
    response = FullInfoV4(MessageParser(message))

    assert response.name == constants.DEVICE_FULL_V4
    assert response.input_status == 0
    assert response.source_vertical_rate == 60.0
    assert response.source_vertical_resolution == 1080
    assert response.source_3d_mode == 4
    assert response.active_input_config_number == 4
    assert response.source_raster_aspect == 178
    assert response.current_source_content_aspect == 240
    assert response.nls_active == "Normal"
    assert response.output_3d_mode == 4
    assert response.output_on == {
        "video_out1": "On",
        "video_out2": "Off",
        "video_out3": "Off",
        "video_out4": "Off",
    }
    assert response.active_output_cms == 4
    assert response.active_output_style == 4
    assert response.output_vertical_rate == 59.94
    assert response.output_vertical_resolution == 2160
    assert response.output_aspect == 178
    assert response.output_colorspace == 2020
    assert response.source_dynamic_range == "HDR"
    assert response.source_mode == "Interlaced"
    assert response.output_mode == "Progressive"
    assert response.virtual_input_selected == 1
    assert response.physical_input_selected == 2
    assert response.detected_source_raster_aspect == 240
    assert response.detected_source_aspect == 178


def test_auto_aspect() -> None:
    """Test parsing AutoAspect response."""
    message = f"!{constants.DEVICE_AUTOASPECT_QUERY},0"
    response = AutoAspect(MessageParser(message))

    assert response.name == constants.DEVICE_AUTOASPECT_QUERY
    assert response.field_auto_aspect == "0"


def test_game_mode() -> None:
    """Test parsing GameMode response."""
    message = f"!{constants.DEVICE_GAMEMODE_QUERY},1"
    response = GameMode(MessageParser(message))

    assert response.name == constants.DEVICE_GAMEMODE_QUERY
    assert response.field_game_mode == "1"


def test_output_basic_info() -> None:
    """Test parsing OutputBasicInfo response."""
    message = f"!{constants.DEVICE_BASIC_OUTPUT_INFO},5,3,0,3,0"
    response = OutputBasicInfo(MessageParser(message))

    assert response.name == constants.DEVICE_BASIC_OUTPUT_INFO
    assert response.output_config == 5
    assert response.video_out1 == "On"
    assert response.video_out2 == "On"
    assert response.video_out3 == "Off"
    assert response.video_out4 == "Off"
    assert response.audio_out1 == "On"
    assert response.audio_out2 == "On"
    assert response.audio_out3 == "Off"
    assert response.audio_out4 == "Off"


def test_output_mode() -> None:
    """Test parsing OutputMode response."""
    message = f"!{constants.DEVICE_OUTPUT_MODE},5994,1920,1080,0,0"
    response = OutputMode(MessageParser(message))

    assert response.name == constants.DEVICE_OUTPUT_MODE
    assert response.output_vertical_rate == 59.94
    assert response.output_vertical_resolution == 1080
    assert response.output_interlaced == "Progressive"
    assert response.output_3d_mode == constants.Frame3DTypeEnum.OFF


def test_output_color_format() -> None:
    """Test parsing OutputColorFormat response."""
    message = f"!{constants.DEVICE_OUTPUT_COLOR_FORMAT},2"
    response = OutputColorFormat(MessageParser(message))

    assert response.name == constants.DEVICE_OUTPUT_COLOR_FORMAT
    assert (
        response.field_output_color_format
        == constants.OUTPUT_COLOR_FORMAT_RGB_VIDEO_LEVEL
    )


def test_label_query() -> None:
    """Test parsing LabelQuery response."""
    message = "#ZQS1A0!S1A,HDMI A0"
    response = LabelQuery(MessageParser(message))

    assert response.name == constants.DEVICE_LABEL_QUERY
    assert response.field_label_index == "A0"
    assert response.field_label_name == "HDMI A0"
