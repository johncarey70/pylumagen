"""Tests for the `lumagen.state_manager` module."""

from unittest.mock import Mock

from lumagen.state_manager import (
    BaseFullInfo,
    BaseInputBasicInfo,
    BaseInputVideo,
    BaseOutputBasicInfo,
    BaseOutputMode,
    DeviceInfo,
    SystemState,
)
import pytest


@pytest.fixture
def system_state():
    """Fixture for SystemState instance."""
    return SystemState()


def test_initial_state(system_state: SystemState) -> None:
    """Test that SystemState initializes correctly."""
    assert system_state.device_id is not None
    assert system_state.full_info is not None
    assert system_state.operational_state is not None


def test_set_update_callback(system_state: SystemState) -> None:
    """Test that update callback is set correctly."""
    mock_callback = Mock()
    system_state.set_update_callback(mock_callback)

    # Attempting to set a non-callable should raise an error
    with pytest.raises(TypeError):
        system_state.set_update_callback("not a function")


def test_get_state_model(system_state: SystemState) -> None:
    """Test retrieving state models."""
    assert system_state.get_state_model("device_id") is not None
    assert system_state.get_state_model("non_existent") is None

    # Test if _update_device_info is called when update=True
    system_state._update_device_info = Mock()  # noqa: SLF001
    system_state.reset_state(update=True)
    system_state._update_device_info.assert_called_once()  # noqa: SLF001


def test_reset_state(system_state: SystemState) -> None:
    """Test resetting system state."""
    system_state.reset_state()
    assert system_state.device_id is not None  # Should be re-initialized
    assert system_state.full_info is not None


def test_update_state(system_state: SystemState) -> None:
    """Test updating system state attributes."""
    mock_info = Mock(spec=BaseFullInfo)
    assert system_state.update_state(full_info=mock_info) is True
    assert system_state.full_info == mock_info


def test_update_full_info(system_state: SystemState) -> None:
    """Test updating full_info state."""
    mock_info = Mock(spec=BaseFullInfo)
    mock_info.model_dump.return_value = {"new": "data"}

    # Ensure update_full_info can accept and update the state
    assert system_state.update_full_info(mock_info) is True  # Should update

    # Calling with the same data should return False (no change)
    assert system_state.update_full_info(mock_info) is False


def test_to_dict(system_state: SystemState) -> None:
    """Test conversion of state to dictionary."""
    state_dict = system_state.to_dict()
    assert isinstance(state_dict, dict)
    assert "device_id" in state_dict


def test_basic_input_info(system_state: SystemState) -> None:
    """Test that basic_input_info property returns expected type."""
    assert isinstance(system_state.basic_input_info, BaseInputBasicInfo)


def test_basic_output_info(system_state: SystemState) -> None:
    """Test that basic_output_info property returns expected type."""
    assert isinstance(system_state.basic_output_info, BaseOutputBasicInfo)


def test_input_video(system_state: SystemState) -> None:
    """Test that input_video property returns expected type."""
    assert isinstance(system_state.input_video, BaseInputVideo)


def test_output_mode(system_state: SystemState) -> None:
    """Test that output_mode property returns expected type."""
    assert isinstance(system_state.output_mode, BaseOutputMode)


def test_update_field_hasattr(system_state: SystemState) -> None:
    """Test updating a field that exists in the SystemState object itself."""
    mock_value = Mock()
    system_state.some_field = None  # Add an attribute dynamically

    assert system_state._update_field("some_field", mock_value) is True  # noqa: SLF001
    assert system_state.some_field == mock_value

    # Updating with the same value should return False
    assert system_state._update_field("some_field", mock_value) is False  # noqa: SLF001


def test_update_field_unknown(system_state, caplog: pytest.LogCaptureFixture) -> None:
    """Test updating an unknown field logs a warning and returns False."""
    with caplog.at_level("WARNING"):
        assert system_state._update_field("unknown_field", "value") is False  # noqa: SLF001
        assert "Attempted to update unknown field" in caplog.text


def test_update_device_info_callback(system_state: SystemState) -> None:
    """Test that _update_device_info calls update callback when device info changes."""
    mock_callback = Mock()
    system_state.set_update_callback(mock_callback)

    # Capture the initial state of _cache.device_info
    initial_device_info = system_state._cache.device_info  # noqa: SLF001

    # Clear initial calls if any (depends on constructor behavior)
    mock_callback.reset_mock()

    system_state._update_device_info()  # First call  # noqa: SLF001
    if system_state._cache.device_info != initial_device_info:  # noqa: SLF001
        # If the cache was updated, allow the callback to be triggered
        mock_callback.assert_called_once()

    # Modify system state to trigger an update with a real DeviceInfo instance
    modified_device_info = DeviceInfo(model_name="Updated Model")
    system_state._cache.device_info = modified_device_info  # noqa: SLF001
    system_state._update_device_info()  # noqa: SLF001

    mock_callback.assert_called()  # Now the callback must be triggered
