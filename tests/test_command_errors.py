"""Tests for user-triggered command error handling and default entities."""

import asyncio
from unittest.mock import Mock

from homeassistant.exceptions import HomeAssistantError
import pytest
from pywebasto.exceptions import InvalidRequestException, UnauthorizedException

from custom_components.webastoconnect.api import WebastoConnectUpdateCoordinator
from custom_components.webastoconnect.switch import SWITCHES


def _build_coordinator() -> WebastoConnectUpdateCoordinator:
    """Create a coordinator with only the state needed for tests."""
    coordinator = object.__new__(WebastoConnectUpdateCoordinator)
    coordinator._cloud_operation_lock = asyncio.Lock()
    coordinator.hass = Mock()
    coordinator.config_entry = Mock()
    return coordinator


@pytest.mark.asyncio
async def test_command_wraps_request_errors() -> None:
    """API request failures surface as HomeAssistantError."""
    coordinator = _build_coordinator()

    async def failing() -> None:
        raise InvalidRequestException("boom")

    with pytest.raises(HomeAssistantError, match="boom"):
        await coordinator.async_execute_command(failing)


@pytest.mark.asyncio
async def test_command_auth_error_starts_reauth() -> None:
    """Auth failures start reauth and surface as HomeAssistantError."""
    coordinator = _build_coordinator()

    async def failing() -> None:
        raise UnauthorizedException("expired")

    with pytest.raises(HomeAssistantError):
        await coordinator.async_execute_command(failing)
    coordinator.config_entry.async_start_reauth.assert_called_once_with(
        coordinator.hass
    )


@pytest.mark.asyncio
async def test_command_returns_result() -> None:
    """Successful commands pass their result through."""
    coordinator = _build_coordinator()

    async def ok(value: int) -> int:
        return value * 2

    assert await coordinator.async_execute_command(ok, 21) == 42


def test_ventilation_mode_switch_enabled_by_default() -> None:
    """Heating/ventilation mode switch is a primary, enabled control."""
    desc = next(s for s in SWITCHES if s.key == "ventilation_mode")
    assert desc.entity_registry_enabled_default is True
    assert desc.entity_category is None
