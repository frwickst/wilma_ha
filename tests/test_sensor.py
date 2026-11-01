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


def _state(
    hass: HomeAssistant, registry: er.EntityRegistry, key: str, student: str = "345"
):
    unique_id = f"test_{student}_{key}" if student else f"test_{key}"
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert entity_id is not None, key
    return hass.states.get(entity_id)


async def test_message_sensors(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    registry = await _setup(hass, mock_config_entry)

    message = _state(hass, registry, "latest_message")
    assert message.state == "Recent message"
    assert message.attributes["id"] == 2
    assert message.attributes["sender"] == "Teacher 2"
    assert message.attributes["content"] == "<p>Content 2</p>"
    assert message.attributes["content_markdown"] == "Content 2"

    assert _state(hass, registry, "unread_count").state == "1"


async def test_attendance_sensors(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    registry = await _setup(hass, mock_config_entry)

    mark = _state(hass, registry, "latest_attendance_mark")
    assert mark.state == "Övrig positiv feedback"
    assert mark.attributes["code"] == "+"
    assert mark.attributes["color"] == "#9191FF"
    assert mark.attributes["comment"] == "Great work"
    assert mark.attributes["marks_this_school_year"] == 2

    count = _state(hass, registry, "attendance_count")
    assert count.state == "2"
    assert count.attributes["by_type"] == {
        "Övrig positiv feedback": 1,
        "Ogjorda läxor och uppgifter": 1,
    }
    assert count.attributes["by_code"] == {"+": 1, "Ogjorda uppgifter": 1}


async def test_bulletin_sensors(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    registry = await _setup(hass, mock_config_entry)

    bulletin = _state(hass, registry, "latest_bulletin")
    assert bulletin.state == "Bulletin 10"
    assert bulletin.attributes["id"] == 10
    assert bulletin.attributes["section"] == "current"
    assert bulletin.attributes["author"] == "Principal"
    assert bulletin.attributes["audience"] == "Guardians"
    assert bulletin.attributes["content_markdown"] == "Body 10"
    assert bulletin.attributes["url"] == "https://test.inschool.fi/!12345/news/10"

    # Bulletins that existed before setup are not new
    assert _state(hass, registry, "unread_bulletin_count").state == "0"


async def test_last_update_sensor(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    registry = await _setup(hass, mock_config_entry)

    assert _state(hass, registry, "last_update", student="").state != STATE_UNKNOWN


async def test_sensors_without_data(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    mock_client.get_messages.side_effect = lambda **kwargs: []
    mock_client.get_attendance.side_effect = lambda *a, **k: make_report()
    mock_client.get_bulletins.side_effect = lambda user_id=None: []

    registry = await _setup(hass, mock_config_entry)

    assert _state(hass, registry, "latest_message").state == STATE_UNKNOWN
    assert _state(hass, registry, "unread_count").state == "0"
    mark = _state(hass, registry, "latest_attendance_mark")
    assert mark.state == STATE_UNKNOWN
    assert mark.attributes["marks_this_school_year"] == 0
    assert _state(hass, registry, "attendance_count").state == "0"
    assert _state(hass, registry, "latest_bulletin").state == STATE_UNKNOWN
