"""Test the Wilma integration initialization."""
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as get_entity_registry

from custom_components.wilma.const import DOMAIN, SENSOR_LATEST_MESSAGE


async def test_setup_and_unload_entry(hass: HomeAssistant, mock_setup_integration):
    """Test setting up and unloading the integration."""
    entry = await mock_setup_integration()

    # Verify entry has been set up properly
    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]
    
    # Verify entities are set up
    entity_registry = get_entity_registry(hass)
    latest_message_entity = entity_registry.async_get(f"sensor.latest_message")
    assert latest_message_entity is not None
    
    latest_unread_entity = entity_registry.async_get(f"sensor.latest_unread_message")
    assert latest_unread_entity is not None
    
    last_update_entity = entity_registry.async_get(f"sensor.last_update")
    assert last_update_entity is not None

    # Unload the entry
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    
    # Verify coordinator is removed from hass.data
    assert entry.entry_id not in hass.data[DOMAIN]