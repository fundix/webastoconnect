"""Support for number entities in Webasto Connect."""

import logging
from typing import cast

from homeassistant.components import number
from homeassistant.components.number import NumberEntity
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import slugify as util_slugify
from pywebasto import WebastoConnect, WebastoDevice

from . import WebastoConfigEntry
from .api import WebastoConnectUpdateCoordinator
from .base import WebastoBaseEntity, WebastoConnectNumberEntityDescription

LOGGER = logging.getLogger(__name__)

NUMBERS = [
    WebastoConnectNumberEntityDescription(
        key="low_voltage_cutoff",
        name="Low Voltage Cutoff",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda webasto: webasto.low_voltage_cutoff,
        set_fn=lambda webasto, device, state: webasto.set_low_voltage_cutoff(
            device, state
        ),
        native_min_value=0,
        native_max_value=30,
        native_step=0.1,
        native_unit_of_measurement="V",
        entity_registry_enabled_default=False,
        icon="mdi:battery-off",
    ),
    WebastoConnectNumberEntityDescription(
        key="ext_temp_comp",
        name="Temperature Compensation",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda webasto: webasto.temperature_compensation,
        set_fn=lambda webasto, device, state: webasto.set_temperature_compensation(
            device, state
        ),
        native_min_value=-10,
        native_max_value=10,
        native_step=0.5,
        unit_fn=lambda webasto: webasto.temperature_unit,
        entity_registry_enabled_default=False,
        icon="mdi:thermometer-alert",
    ),
    WebastoConnectNumberEntityDescription(
        key="heater_run_time",
        name="Heater run time",
        entity_category=None,
        value_fn=lambda webasto: _seconds_to_minutes(webasto.timeout_heat),
        set_fn=lambda webasto, device, state: _set_main_timeout(
            webasto, device, heater=state
        ),
        native_min_value=1,
        native_max_value=240,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        entity_registry_enabled_default=True,
        icon="mdi:radiator",
    ),
    WebastoConnectNumberEntityDescription(
        key="ventilation_run_time",
        name="Ventilation run time",
        entity_category=None,
        value_fn=lambda webasto: _seconds_to_minutes(webasto.timeout_vent),
        set_fn=lambda webasto, device, state: _set_main_timeout(
            webasto, device, ventilation=state
        ),
        native_min_value=1,
        native_max_value=240,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        entity_registry_enabled_default=True,
        icon="mdi:fan-clock",
    ),
]


def _seconds_to_minutes(seconds: int | None) -> int | None:
    """Convert a Webasto timeout in seconds to minutes."""
    if not seconds:
        return None
    return int(seconds) // 60


async def _set_main_timeout(
    webasto: WebastoConnect,
    device: WebastoDevice,
    heater: float | None = None,
    ventilation: float | None = None,
) -> None:
    """Set heater/ventilation run time in minutes.

    pywebasto always writes both timeouts, so refuse when the other one is
    unknown instead of silently resetting it to 0.
    """
    if not device.timeout_heat or not device.timeout_vent:
        raise HomeAssistantError(
            "Current run times are not known yet, try again after the next update"
        )
    await webasto.set_main_timeout(
        device,
        heater=int(heater * 60) if heater is not None else None,
        ventilation=int(ventilation * 60) if ventilation is not None else None,
    )


async def async_setup_entry(hass, entry: WebastoConfigEntry, async_add_devices):
    """Set up numbers."""
    numbers_list = []

    coordinator = entry.runtime_data.coordinator

    for id, device in coordinator.cloud.devices.items():
        LOGGER.debug("Setting up numbers for device: %s", device.name)
        for num in NUMBERS:
            entity = WebastoConnectNumber(id, num, coordinator)
            LOGGER.debug(
                "Adding number '%s' with entity_id '%s'", num.name, entity.entity_id
            )
            numbers_list.append(entity)

    async_add_devices(numbers_list)


class WebastoConnectNumber(WebastoBaseEntity, NumberEntity):
    """Representation of a Webasto Connect number."""

    def __init__(
        self,
        device_id: int,
        description: WebastoConnectNumberEntityDescription,
        coordinator: WebastoConnectUpdateCoordinator,
    ) -> None:
        """Initialize a Webasto Connect number."""
        super().__init__(device_id, coordinator, description)

        if not isinstance(description.unit_fn, type(None)):
            self._attr_native_unit_of_measurement = description.unit_fn(
                self._cloud.devices[self._device_id]
            )

        self.entity_id = number.ENTITY_ID_FORMAT.format(
            util_slugify(f"{self._device_name} {self._attr_name}")
        )

    @property
    def native_value(self) -> float | None:
        """Get the native value."""
        return cast(
            float,
            self.entity_description.value_fn(self._device),  # type: ignore
        )

    @property
    def available(self) -> bool:
        """Return False when the device is explicitly disconnected."""
        self._attr_available = self._is_device_connected
        return self._attr_available

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        LOGGER.debug("Setting '%s' to '%s'", self.entity_id, value)
        await self.coordinator.async_execute_command(
            self.entity_description.set_fn,  # type: ignore[arg-type]
            self._cloud,
            self._device,
            value,
        )
        self.coordinator.async_update_listeners()
