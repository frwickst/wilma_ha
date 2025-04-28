"""Test the Wilma sensor platform."""
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wilma.const import (
    ATTR_CONTENT,
    ATTR_CONTENT_MARKDOWN,
    ATTR_ID,
    ATTR_SENDER,
    ATTR_SUBJECT,
    ATTR_TIMESTAMP,
    DOMAIN,
)


async def test_sensors_state(hass: HomeAssistant, mock_setup_integration):
    """Test sensor states."""
    # Complete setup
    await mock_setup_integration()
    
    # Check latest message sensor
    state = hass.states.get("sensor.latest_message")
    assert state is not None
    assert state.state == "Test Message 1"
    
    # Check attributes
    assert state.attributes[ATTR_ID] == 1
    assert state.attributes[ATTR_SUBJECT] == "Test Message 1"
    assert state.attributes[ATTR_SENDER] == "Sender 1"
    assert state.attributes[ATTR_TIMESTAMP] == "2023-01-01 12:00"
    assert ATTR_CONTENT in state.attributes
    assert ATTR_CONTENT_MARKDOWN in state.attributes
    
    # Check latest unread message sensor
    state = hass.states.get("sensor.latest_unread_message")
    assert state is not None
    assert state.state == "Test Message 1"
    
    # Check last update sensor
    state = hass.states.get("sensor.last_update")
    assert state is not None
    assert state.state != STATE_UNKNOWN


async def test_sensor_no_messages(hass: HomeAssistant, mock_config_entry):
    """Test sensor behavior when there are no messages."""
    # Set up empty messages return
    with patch("wilma.WilmaClient") as mock_client:
        client = mock_client.return_value
        client.login = AsyncMock()
        client.get_messages = AsyncMock(return_value=[])
        
        # Set up entry
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    
    # Check latest message sensor - should be unknown
    state = hass.states.get("sensor.latest_message")
    assert state is not None
    assert state.state == STATE_UNKNOWN
    
    # Check latest unread message sensor - should be unknown
    state = hass.states.get("sensor.latest_unread_message")
    assert state is not None
    assert state.state == STATE_UNKNOWN