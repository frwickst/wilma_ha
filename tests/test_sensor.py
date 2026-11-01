"""Tests for the Wilma sensors."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wilma.const import DOMAIN

from .conftest import (
    BEHAVIOUR,
    HOMEWORK,
    POSITIVE,
    make_bulletins,
    make_mark,
    make_message,
    make_report,
)


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


async def test_recent_messages_attribute(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    mock_client.get_messages.side_effect = lambda **kwargs: [
        make_message(i, f"Message {i}", days_ago=i / 10, unread=i % 2 == 0)
        for i in range(1, 9)
    ]
    registry = await _setup(hass, mock_config_entry)

    recent = _state(hass, registry, "latest_message").attributes["recent_messages"]
    assert [m["id"] for m in recent] == [1, 2, 3, 4, 5]
    assert recent[1] == {
        "id": 2,
        "subject": "Message 2",
        "sender": "Teacher 2",
        "timestamp": recent[1]["timestamp"],
        "unread": True,
    }
    assert recent[0]["unread"] is False
    assert set(recent[0]) == {"id", "subject", "sender", "timestamp", "unread"}


async def test_stored_messages_follow_read_status(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    registry = await _setup(hass, mock_config_entry)
    assert _state(hass, registry, "latest_message").attributes["recent_messages"][0][
        "unread"
    ]

    mock_client.get_messages.side_effect = lambda **kwargs: [
        make_message(2, "Recent message", days_ago=1, unread=False),
        make_message(1, "Old message", days_ago=30, unread=False),
    ]
    await mock_config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    recent = _state(hass, registry, "latest_message").attributes["recent_messages"]
    assert recent[0]["unread"] is False


async def test_attendance_list_attributes(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    marks = [
        make_mark(POSITIVE, days_ago=1, hour=9, comment="x" * 1000),
        make_mark(POSITIVE, days_ago=1, hour=11),
        make_mark(HOMEWORK, days_ago=3, hour=10),
        *[make_mark(POSITIVE, days_ago=20 + i, hour=8) for i in range(10)],
    ]
    mock_client.get_attendance.side_effect = lambda *a, **k: make_report(*marks)
    registry = await _setup(hass, mock_config_entry)

    attributes = _state(hass, registry, "attendance_count").attributes
    # Only types that occur, most frequent first
    assert attributes["types"] == [
        {
            "type_id": 146,
            "code": "+",
            "description": "Övrig positiv feedback",
            "color": "#9191FF",
            "count": 12,
        },
        {
            "type_id": 135,
            "code": "Ogjorda uppgifter",
            "description": "Ogjorda läxor och uppgifter",
            "color": "#0080FF",
            "count": 1,
        },
    ]
    assert BEHAVIOUR.id not in {t["type_id"] for t in attributes["types"]}

    recent = attributes["recent_marks"]
    assert len(recent) == 10
    # Newest date first, and the later lesson first within a day
    assert [(m["hour"], m["code"]) for m in recent[:3]] == [
        (11, "+"),
        (9, "+"),
        (10, "Ogjorda uppgifter"),
    ]
    assert set(recent[0]) == {
        "date",
        "hour",
        "code",
        "description",
        "color",
        "course",
        "comment",
        "teacher",
    }
    assert recent[0]["course"] == "ma05"
    assert recent[0]["teacher"] == "Anna Teacher"
    assert recent[0]["color"] == "#9191FF"
    assert len(recent[1]["comment"]) == 300


async def test_recent_bulletins_attribute(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    mock_client.get_bulletins.side_effect = lambda user_id=None: make_bulletins(
        *range(1, 9)
    )
    registry = await _setup(hass, mock_config_entry)

    attributes = _state(hass, registry, "latest_bulletin").attributes
    recent = attributes["recent_bulletins"]
    assert [b["id"] for b in recent] == [8, 7, 6, 5, 4]
    assert recent[0]["author"] == "Principal"
    assert recent[1] == {
        "id": 7,
        "title": "Bulletin 7",
        "date": recent[1]["date"],
        "author": "Principal",
        "url": "https://test.inschool.fi/!12345/news/7",
    }
    assert all("content_html" not in b for b in recent)
    assert attributes["content_markdown"] == "Body 8"
