"""Tests for the Wilma sensors."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wilma.const import DOMAIN

from .conftest import make_report


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> er.EntityRegistry:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return er.async_get(hass)


def _state(hass: HomeAssistant, registry: er.EntityRegistry, key: str):
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"test_{key}")
    assert entity_id is not None
    return hass.states.get(entity_id)


async def test_sensor_states(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    registry = await _setup(hass, mock_config_entry)

    message = _state(hass, registry, "latest_message")
    assert message.state == "Recent message"
    assert message.attributes["id"] == 2
    assert message.attributes["sender"] == "Teacher 2"
    assert message.attributes["content"] == "<p>Content 2</p>"
    assert message.attributes["content_markdown"] == "Content 2"

    mark = _state(hass, registry, "latest_attendance_mark")
    assert mark.state == "Övrig positiv feedback"
    assert mark.attributes["code"] == "+"
    assert mark.attributes["color"] == "#9191FF"
    assert mark.attributes["comment"] == "Great work"
    assert mark.attributes["marks_this_school_year"] == 2
    assert mark.attributes["counts_by_type"] == {
        "Övrig positiv feedback": 1,
        "Ogjorda läxor och uppgifter": 1,
    }

    last_update = _state(hass, registry, "last_update")
    assert last_update.state != STATE_UNKNOWN


async def test_sensors_without_data(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    mock_client.get_messages.side_effect = list
    mock_client.get_attendance.side_effect = lambda *a, **k: make_report()

    registry = await _setup(hass, mock_config_entry)

    assert _state(hass, registry, "latest_message").state == STATE_UNKNOWN
    mark = _state(hass, registry, "latest_attendance_mark")
    assert mark.state == STATE_UNKNOWN
    assert mark.attributes["marks_this_school_year"] == 0
