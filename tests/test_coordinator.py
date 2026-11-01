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
    EVENT_NEW_BULLETIN,
    EVENT_NEW_MESSAGE,
    MAX_STORED_MESSAGES,
)
from custom_components.wilma.coordinator import WilmaCoordinator

from .conftest import (
    BEHAVIOUR,
    HOMEWORK,
    POSITIVE,
    make_bulletins,
    make_mark,
    make_message,
    make_report,
)

USER_ID = "!12345"


async def _coordinator(hass: HomeAssistant, entry: MockConfigEntry) -> WilmaCoordinator:
    entry.add_to_hass(hass)
    coordinator = WilmaCoordinator(hass, entry)
    await coordinator._async_setup()
    return coordinator


async def test_first_update_records_existing_data_without_events(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    events = [
        async_capture_events(hass, event)
        for event in (EVENT_NEW_MESSAGE, EVENT_NEW_ATTENDANCE_MARK, EVENT_NEW_BULLETIN)
    ]
    coordinator = await _coordinator(hass, mock_config_entry)

    data = await coordinator._async_update_data()

    mock_client.login.assert_awaited_once_with("testuser", "testpass")
    student = data.students[USER_ID]
    assert student.name == "Anna Student"
    assert student.first_name == "Anna"
    # Only the message within the initial lookback gets its content fetched
    fetched = mock_client.fetch_content.await_args
    assert [m.id for m in fetched.args[0]] == [2]
    assert fetched.kwargs == {"user_id": USER_ID}
    assert [m["id"] for m in student.messages] == [2]
    assert student.latest_message["content_markdown"] == "Content 2"
    assert student.latest_message["student_id"] == USER_ID
    assert student.unread_count == 1
    assert student.latest_attendance_mark.type == POSITIVE
    # Only the latest bulletin gets its content fetched, for the sensor
    mock_client.get_bulletin.assert_awaited_once_with(10, user_id=USER_ID)
    assert student.latest_bulletin["title"] == "Bulletin 10"
    assert student.latest_bulletin["content_markdown"] == "Body 10"
    assert (
        student.latest_bulletin["url"] == f"https://test.inschool.fi/{USER_ID}/news/10"
    )
    assert student.new_bulletin_count == 0
    for captured in events:
        assert captured == []


async def test_new_items_fire_events_once(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    coordinator = await _coordinator(hass, mock_config_entry)
    await coordinator._async_update_data()
    message_events = async_capture_events(hass, EVENT_NEW_MESSAGE)
    mark_events = async_capture_events(hass, EVENT_NEW_ATTENDANCE_MARK)
    bulletin_events = async_capture_events(hass, EVENT_NEW_BULLETIN)

    mock_client.get_messages.side_effect = lambda **kwargs: [
        make_message(3, "Brand new", days_ago=0),
        make_message(2, "Recent message", days_ago=1),
        make_message(1, "Old message", days_ago=30, unread=False),
    ]
    mock_client.get_attendance.side_effect = lambda *a, **k: make_report(
        make_mark(BEHAVIOUR, days_ago=0, hour=8, comment="Talked in class"),
        make_mark(POSITIVE, days_ago=2, hour=9, comment="Comment edited later"),
        make_mark(HOMEWORK, days_ago=5, hour=10),
    )
    mock_client.get_bulletins.side_effect = lambda user_id=None: make_bulletins(
        11, 10, 9
    )
    mock_client.fetch_content.reset_mock()
    mock_client.get_bulletin.reset_mock()

    data = await coordinator._async_update_data()
    await hass.async_block_till_done()
    student = data.students[USER_ID]

    assert [m.id for m in mock_client.fetch_content.await_args.args[0]] == [3]
    assert [m["id"] for m in student.messages] == [3, 2]
    assert student.latest_message["subject"] == "Brand new"
    assert student.unread_count == 2

    assert len(message_events) == 1
    message_event = message_events[0].data
    assert message_event["id"] == 3
    assert message_event["content_markdown"] == "Content 3"
    assert message_event["student_id"] == USER_ID
    assert message_event["student_name"] == "Anna Student"

    # The edited comment does not make the positive mark look new
    assert len(mark_events) == 1
    mark_event = mark_events[0].data
    assert mark_event["entry_id"] == "test"
    assert mark_event["student_name"] == "Anna Student"
    assert mark_event["description"] == "Störande eller dåligt beteende"
    assert mark_event["color"] == "#D4D4D4"
    assert mark_event["comment"] == "Talked in class"
    assert student.latest_attendance_mark.type == BEHAVIOUR
    assert student.latest_new_mark_seen is not None

    assert len(bulletin_events) == 1
    bulletin_event = bulletin_events[0].data
    assert bulletin_event["id"] == 11
    assert bulletin_event["title"] == "Bulletin 11"
    assert bulletin_event["section"] == "current"
    assert bulletin_event["content_markdown"] == "Body 11"
    assert bulletin_event["student_id"] == USER_ID
    mock_client.get_bulletin.assert_awaited_once_with(11, user_id=USER_ID)
    assert student.latest_bulletin["id"] == 11
    assert student.new_bulletin_count == 1

    # Nothing new on the next update
    mock_client.fetch_content.reset_mock()
    mock_client.get_bulletin.reset_mock()
    await coordinator._async_update_data()
    await hass.async_block_till_done()
    mock_client.fetch_content.assert_not_awaited()
    mock_client.get_bulletin.assert_not_awaited()
    assert len(message_events) == 1
    assert len(mark_events) == 1
    assert len(bulletin_events) == 1


async def test_state_survives_restart(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    first = await _coordinator(hass, mock_config_entry)
    await first._async_update_data()

    second = WilmaCoordinator(hass, mock_config_entry)
    await second._async_setup()
    mark_events = async_capture_events(hass, EVENT_NEW_ATTENDANCE_MARK)
    bulletin_events = async_capture_events(hass, EVENT_NEW_BULLETIN)
    mock_client.get_attendance.side_effect = lambda *a, **k: make_report(
        make_mark(POSITIVE, days_ago=2, hour=9),
        make_mark(HOMEWORK, days_ago=5, hour=10),
        make_mark(HOMEWORK, days_ago=0, hour=12),
    )
    mock_client.fetch_content.reset_mock()
    mock_client.get_bulletin.reset_mock()

    data = await second._async_update_data()
    await hass.async_block_till_done()

    student = data.students[USER_ID]
    assert [m["id"] for m in student.messages] == [2]
    mock_client.fetch_content.assert_not_awaited()
    # The cached bulletin content survives as well
    mock_client.get_bulletin.assert_not_awaited()
    assert student.latest_bulletin["content_markdown"] == "Body 10"
    assert [e.data["hour"] for e in mark_events] == [12]
    assert bulletin_events == []


async def test_storage_from_before_multi_student_moves_to_primary_student(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    coordinator = WilmaCoordinator(hass, mock_config_entry)
    mock_config_entry.add_to_hass(hass)
    old = {"id": 7, "subject": "Old", "timestamp": "2024-01-01 10:00"}
    newer = {"id": 8, "subject": "Newer", "timestamp": "2024-02-01 10:00"}
    report = make_report(
        make_mark(POSITIVE, days_ago=2, hour=9),
        make_mark(HOMEWORK, days_ago=5, hour=10),
    )
    await coordinator.store.async_save(
        {
            "messages": [old, newer, old],
            "seen_message_ids": [1, 2, 7, 8],
            "seen_attendance_keys": [mark.key for mark in report.marks],
        }
    )
    await coordinator._async_setup()
    message_events = async_capture_events(hass, EVENT_NEW_MESSAGE)
    mark_events = async_capture_events(hass, EVENT_NEW_ATTENDANCE_MARK)

    data = await coordinator._async_update_data()
    await hass.async_block_till_done()

    assert [m["id"] for m in data.students[USER_ID].messages] == [8, 7]
    assert message_events == []
    assert mark_events == []
    stored = await coordinator.store.async_load()
    assert set(stored) == {"students"}
    assert stored["students"][USER_ID]["seen_message_ids"] == [1, 2]


async def test_stored_messages_are_capped(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    coordinator = await _coordinator(hass, mock_config_entry)
    await coordinator._async_update_data()
    mock_client.get_messages.side_effect = lambda **kwargs: [
        make_message(100 + i, f"Message {i}", days_ago=i / 100) for i in range(80)
    ]

    data = await coordinator._async_update_data()

    messages = data.students[USER_ID].messages
    assert len(messages) == MAX_STORED_MESSAGES
    assert messages[0]["id"] == 100
    # Content is only fetched for a bounded number of messages per update
    assert len(mock_client.fetch_content.await_args.args[0]) == 10


@pytest.mark.parametrize(
    "method", ["get_attendance", "get_bulletins", "get_schedule", "get_overview"]
)
async def test_partial_failures_keep_other_data(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
    method: str,
) -> None:
    coordinator = await _coordinator(hass, mock_config_entry)
    first = await coordinator._async_update_data()
    mocked = getattr(mock_client, method)
    original = mocked.side_effect
    mocked.side_effect = WilmaError("down")

    data = await coordinator._async_update_data()

    student = data.students[USER_ID]
    assert student.messages
    assert student.attendance == first.students[USER_ID].attendance
    assert student.schedule == first.students[USER_ID].schedule
    assert student.overview == first.students[USER_ID].overview
    assert coordinator.partial_errors
    assert "Anna Student" in coordinator.partial_errors[0]

    # A successful update clears them again
    mocked.side_effect = original
    await coordinator._async_update_data()
    assert coordinator.partial_errors == []


async def test_two_students(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_two_student_client: MagicMock,
) -> None:
    coordinator = await _coordinator(hass, mock_config_entry)

    data = await coordinator._async_update_data()

    assert list(data.students) == ["!12345", "!67890"]
    assert data.students["!67890"].first_name == "Bo"
    for method in (
        "get_messages",
        "get_attendance",
        "get_schedule",
        "get_bulletins",
        "get_overview",
    ):
        user_ids = {
            call.kwargs["user_id"]
            for call in getattr(mock_two_student_client, method).await_args_list
        }
        assert user_ids == {"!12345", "!67890"}, method
    stored = await coordinator.store.async_load()
    assert set(stored["students"]) == {"!12345", "!67890"}


@pytest.mark.parametrize(
    "students",
    [AsyncMock(return_value=[]), AsyncMock(side_effect=WilmaError("no roles"))],
)
async def test_falls_back_to_login_user_without_students(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
    students: AsyncMock,
) -> None:
    mock_client.get_students = students
    coordinator = await _coordinator(hass, mock_config_entry)

    data = await coordinator._async_update_data()

    assert list(data.students) == [USER_ID]
    assert data.students[USER_ID].name == "testuser"
    assert data.students[USER_ID].messages


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
