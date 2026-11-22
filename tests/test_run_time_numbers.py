"""Tests for heater/ventilation run time number entities."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

from homeassistant.exceptions import HomeAssistantError
import pytest

from custom_components.webastoconnect.number import NUMBERS


def _desc(key: str):
    return next(n for n in NUMBERS if n.key == key)


def test_run_time_values_are_minutes() -> None:
    """Timeouts are reported in minutes."""
    device = SimpleNamespace(timeout_heat=3600, timeout_vent=1800)
    assert _desc("heater_run_time").value_fn(device) == 60
    assert _desc("ventilation_run_time").value_fn(device) == 30


def test_run_time_unknown_is_none() -> None:
    """Missing timeouts are reported as unknown."""
    device = SimpleNamespace(timeout_heat=0, timeout_vent=0)
    assert _desc("heater_run_time").value_fn(device) is None


@pytest.mark.asyncio
async def test_set_heater_run_time_converts_to_seconds() -> None:
    """Setting minutes writes seconds and keeps the other timeout."""
    device = SimpleNamespace(timeout_heat=3600, timeout_vent=1800)
    cloud = SimpleNamespace(set_main_timeout=AsyncMock())
    await _desc("heater_run_time").set_fn(cloud, device, 25.0)
    cloud.set_main_timeout.assert_awaited_once_with(
        device, heater=1500, ventilation=None
    )


@pytest.mark.asyncio
async def test_set_ventilation_run_time_converts_to_seconds() -> None:
    """Ventilation run time is written in seconds."""
    device = SimpleNamespace(timeout_heat=3600, timeout_vent=1800)
    cloud = SimpleNamespace(set_main_timeout=AsyncMock())
    await _desc("ventilation_run_time").set_fn(cloud, device, 10.0)
    cloud.set_main_timeout.assert_awaited_once_with(
        device, heater=None, ventilation=600
    )


@pytest.mark.asyncio
async def test_set_run_time_refuses_when_other_timeout_unknown() -> None:
    """Do not overwrite an unknown timeout with 0."""
    device = SimpleNamespace(timeout_heat=3600, timeout_vent=0)
    cloud = SimpleNamespace(set_main_timeout=AsyncMock())
    with pytest.raises(HomeAssistantError):
        await _desc("heater_run_time").set_fn(cloud, device, 25.0)
    cloud.set_main_timeout.assert_not_awaited()
