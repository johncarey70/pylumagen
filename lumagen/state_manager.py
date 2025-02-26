"""state_manager.py.

This module defines the SystemState class for managing and caching system state
information in a structured manner. It includes device status, input/output settings,
and full device information, with mechanisms to track updates and avoid redundant changes.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from . import DeviceInfo
from .models import (
    BaseDeviceId,
    BaseFullInfo,
    BaseInputBasicInfo,
    BaseInputVideo,
    BaseOperationalState,
    BaseOutputBasicInfo,
    BaseOutputMode,
)
from .utils import LoggingMixin, flatten_dictionary


@dataclass
class Cache:
    """Encapsulates caching logic for SystemState."""

    data: dict[str, dict] = field(default_factory=dict)
    device_info: DeviceInfo = field(default_factory=DeviceInfo)


@dataclass
class SystemState(LoggingMixin):
    """A class to encapsulate the system state with caching for all attributes."""

    _cache: Cache = field(default_factory=Cache, init=False, repr=False)

    _update_callback: Callable[[DeviceInfo], None] | None = field(
        default=None, init=False, repr=False, compare=False
    )

    state_models: dict[str, BaseModel] = field(
        default_factory=lambda: {
            "basic_input_info": BaseInputBasicInfo(),
            "basic_output_info": BaseOutputBasicInfo(),
            "device_id": BaseDeviceId(),
            "full_info": BaseFullInfo(),
            "input_video": BaseInputVideo(),
            "operational_state": BaseOperationalState(),
            "output_mode": BaseOutputMode(),
        }
    )

    def __post_init__(self) -> None:
        """Ensure LoggingMixin is properly initialized."""
        super().__init__()

    @property
    def basic_input_info(self) -> BaseInputBasicInfo:
        """Return basic_input_info."""
        return self.state_models["basic_input_info"]

    @property
    def basic_output_info(self) -> BaseOutputBasicInfo:
        """Return basic_output_info."""
        return self.state_models["basic_output_info"]

    @property
    def device_id(self) -> BaseDeviceId:
        """Return device_id."""
        return self.state_models["device_id"]

    @property
    def full_info(self) -> BaseFullInfo:
        """Return full_info."""
        return self.state_models["full_info"]

    @property
    def input_video(self) -> BaseInputVideo:
        """Return input_video."""
        return self.state_models["input_video"]

    @property
    def operational_state(self) -> BaseOperationalState:
        """Return device_status."""
        return self.state_models["operational_state"]

    @property
    def output_mode(self) -> BaseOutputMode:
        """Return output_mode."""
        return self.state_models["output_mode"]

    def set_update_callback(self, callback: Callable[[DeviceInfo], None]) -> None:
        """Set the callback function that gets called when data updates."""
        if not callable(callback):
            raise TypeError("update_callback must be a callable function.")
        self._update_callback = callback

    def get_state_model(self, key: str) -> Any:
        """Get a state model safely."""
        return self.state_models.get(key, None)

    def reset_state(self, update=False) -> None:
        """Reset the system state to default values."""
        self.log.info("Resetting system state to default values.")

        self.state_models = {
            "basic_input_info": BaseInputBasicInfo(),
            "basic_output_info": BaseOutputBasicInfo(),
            "device_id": BaseDeviceId(),
            "full_info": BaseFullInfo(),
            "input_video": BaseInputVideo(),
            "operational_state": BaseOperationalState(),
            "output_mode": BaseOutputMode(),
        }

        self._cache.data.clear()
        self._cache.device_info = DeviceInfo()

        if update:
            self._update_device_info()

    def _update_field(self, field_name: str, new_value: Any) -> bool:
        """Update method for caching and preventing unnecessary updates."""

        if field_name in self.state_models:
            new_value_dict = (
                new_value.model_dump()
                if isinstance(new_value, BaseModel)
                else new_value
            )

            cache_key = f"_cached_{field_name}"
            if self._cache.data.get(cache_key, {}) == new_value_dict:
                return False

            self.state_models[field_name] = new_value
            self._cache.data[cache_key] = new_value_dict

            self._update_device_info()
            return True

        if hasattr(self, field_name):
            old_value = getattr(self, field_name)
            if old_value == new_value:
                return False

            setattr(self, field_name, new_value)
            self._update_device_info()
            return True

        self.log.warning("Attempted to update unknown field: %s", field_name)
        return False

    def update_state(self, **kwargs) -> bool:
        """Batch update multiple attributes and return True if any value changed."""
        changes_detected = False

        for field_name, new_value in kwargs.items():
            if hasattr(self, field_name):
                if self._update_field(field_name, new_value):
                    changes_detected = True

        return changes_detected

    def update_full_info(self, new_info: BaseFullInfo) -> bool:
        """Update full_info only if it has changed."""
        filtered_update = {
            k: v for k, v in new_info.model_dump().items() if v is not None
        }

        updated_full_info = self.state_models["full_info"].model_copy(
            update=filtered_update
        )

        if self._update_field("full_info", updated_full_info):
            self._update_device_info()
            return True
        return False

    def _update_device_info(self) -> None:
        """Merge system state data and update cached `DeviceInfo` instance.

        This method collects all system state attributes, creates a new
        `DeviceInfo` instance, and updates the cache. If any changes are
        detected, it dispatches an event.
        """

        merged_dict = flatten_dictionary(self.to_dict())
        new_device_info = DeviceInfo(**merged_dict)

        if self._cache.device_info != new_device_info:
            self._cache.device_info = new_device_info
            if self._update_callback is not None:
                self._update_callback(new_device_info)

    def to_dict(self) -> dict:
        """Convert the SystemState instance into a sorted dictionary."""
        unsorted_dict = {
            **{k: v.model_dump() for k, v in self.state_models.items()},
        }
        return dict(sorted(unsorted_dict.items()))
