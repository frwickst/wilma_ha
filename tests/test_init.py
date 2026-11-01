"""Tests for setting up and unloading the Wilma integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from wilhelmina import AuthenticationError

from custom_components.wilma.const import DOMAIN


async def test_setup_and_unload_entry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    registry = er.async_get(hass)
    for key in ("latest_message", "latest_attendance_mark", "last_update"):
        assert registry.async_get_entity_id("sensor", DOMAIN, f"test_{key}") is not None

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    mock_client.close.assert_awaited()


async def test_setup_retries_when_login_fails(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    mock_client.login = AsyncMock(side_effect=AuthenticationError("bad password"))
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
    mock_client.close.assert_awaited()
