"""Tests for the Wilma data update coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)
from wilhelmina import AuthenticationError, WilmaError

from custom_components.wilma.const import (
    EVENT_NEW_ATTENDANCE_MARK,
    EVENT_NEW_MESSAGE,
    MAX_STORED_MESSAGES,
)
from custom_components.wilma.coordinator import WilmaCoordinator

from .conftest import (
    BEHAVIOUR,
    HOMEWORK,
    POSITIVE,
    make_mark,
    make_message,
    make_report,
)


async def _coordinator(hass: HomeAssistant, entry: MockConfigEntry) -> WilmaCoordinator:
    entry.add_to_hass(hass)
    coordinator = WilmaCoordinator(hass, entry)
    await coordinator._async_setup()
    return coordinator


async def test_first_update_records_existing_data_without_events(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    message_events = async_capture_events(hass, EVENT_NEW_MESSAGE)
    mark_events = async_capture_events(hass, EVENT_NEW_ATTENDANCE_MARK)
    coordinator = await _coordinator(hass, mock_config_entry)

    data = await coordinator._async_update_data()

    mock_client.login.assert_awaited_once_with("testuser", "testpass")
    # Only the message within the initial lookback gets its content fetched
    fetched = mock_client.fetch_content.await_args.args[0]
    assert [m.id for m in fetched] == [2]
    assert [m["id"] for m in data.messages] == [2]
    assert data.latest_message["content_markdown"] == "Content 2"
    assert data.latest_attendance_mark.type == POSITIVE
    assert message_events == []
    assert mark_events == []


async def test_new_items_fire_events_once(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    coordinator = await _coordinator(hass, mock_config_entry)
    await coordinator._async_update_data()
    message_events = async_capture_events(hass, EVENT_NEW_MESSAGE)
    mark_events = async_capture_events(hass, EVENT_NEW_ATTENDANCE_MARK)

    mock_client.get_messages.side_effect = lambda: [
        make_message(3, "Brand new", days_ago=0),
        make_message(2, "Recent message", days_ago=1),
        make_message(1, "Old message", days_ago=30, unread=False),
    ]
    mock_client.get_attendance.side_effect = lambda *a, **k: make_report(
        make_mark(BEHAVIOUR, days_ago=0, hour=8, comment="Talked in class"),
        make_mark(POSITIVE, days_ago=2, hour=9, comment="Comment edited later"),
        make_mark(HOMEWORK, days_ago=5, hour=10),
    )
    mock_client.fetch_content.reset_mock()

    data = await coordinator._async_update_data()
    await hass.async_block_till_done()

    assert [m.id for m in mock_client.fetch_content.await_args.args[0]] == [3]
    assert [m["id"] for m in data.messages] == [3, 2]
    assert data.latest_message["subject"] == "Brand new"

    assert len(message_events) == 1
    assert message_events[0].data["id"] == 3
    assert message_events[0].data["content_markdown"] == "Content 3"

    # The edited comment does not make the positive mark look new
    assert len(mark_events) == 1
    event = mark_events[0].data
    assert event["entry_id"] == "test"
    assert event["description"] == "Störande eller dåligt beteende"
    assert event["color"] == "#D4D4D4"
    assert event["comment"] == "Talked in class"
    assert data.latest_attendance_mark.type == BEHAVIOUR

    # Nothing new on the next update
    mock_client.fetch_content.reset_mock()
    await coordinator._async_update_data()
    await hass.async_block_till_done()
    mock_client.fetch_content.assert_not_awaited()
    assert len(message_events) == 1
    assert len(mark_events) == 1


async def test_state_survives_restart(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    first = await _coordinator(hass, mock_config_entry)
    await first._async_update_data()

    second = WilmaCoordinator(hass, mock_config_entry)
    await second._async_setup()
    mark_events = async_capture_events(hass, EVENT_NEW_ATTENDANCE_MARK)
    mock_client.get_attendance.side_effect = lambda *a, **k: make_report(
        make_mark(POSITIVE, days_ago=2, hour=9),
        make_mark(HOMEWORK, days_ago=5, hour=10),
        make_mark(HOMEWORK, days_ago=0, hour=12),
    )
    mock_client.fetch_content.reset_mock()

    data = await second._async_update_data()
    await hass.async_block_till_done()

    assert [m["id"] for m in data.messages] == [2]
    mock_client.fetch_content.assert_not_awaited()
    assert [e.data["hour"] for e in mark_events] == [12]


async def test_legacy_storage_is_deduplicated(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    coordinator = WilmaCoordinator(hass, mock_config_entry)
    mock_config_entry.add_to_hass(hass)
    old = {"id": 7, "subject": "Old", "timestamp": "2024-01-01 10:00"}
    newer = {"id": 8, "subject": "Newer", "timestamp": "2024-02-01 10:00"}
    await coordinator.store.async_save({"messages": [old, newer, old, old]})
    await coordinator._async_setup()

    assert [m["id"] for m in coordinator._messages] == [8, 7]


async def test_stored_messages_are_capped(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    coordinator = await _coordinator(hass, mock_config_entry)
    await coordinator._async_update_data()
    mock_client.get_messages.side_effect = lambda: [
        make_message(100 + i, f"Message {i}", days_ago=i / 100) for i in range(80)
    ]

    data = await coordinator._async_update_data()

    assert len(data.messages) == MAX_STORED_MESSAGES
    assert data.messages[0]["id"] == 100
    # Content is only fetched for a bounded number of messages per update
    assert len(mock_client.fetch_content.await_args.args[0]) == 10


async def test_attendance_failure_keeps_messages_working(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    coordinator = await _coordinator(hass, mock_config_entry)
    first = await coordinator._async_update_data()
    mock_client.get_attendance.side_effect = WilmaError("parse failure")

    data = await coordinator._async_update_data()

    assert data.messages
    assert data.attendance is first.attendance
    assert "Could not fetch attendance marks" in caplog.text


async def test_auth_error_closes_client(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    mock_client.login = AsyncMock(side_effect=AuthenticationError("bad password"))
    coordinator = await _coordinator(hass, mock_config_entry)

    with pytest.raises(UpdateFailed, match="Authentication failed"):
        await coordinator._async_update_data()

    mock_client.close.assert_awaited()
    assert coordinator.client is None


async def test_wilma_error_raises_update_failed(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    mock_client.get_messages.side_effect = WilmaError("API error")
    coordinator = await _coordinator(hass, mock_config_entry)

    with pytest.raises(UpdateFailed, match="Error communicating with Wilma"):
        await coordinator._async_update_data()
