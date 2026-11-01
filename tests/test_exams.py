"""Tests for exams, exam grades and homework."""

from __future__ import annotations

import datetime
import json
from unittest.mock import MagicMock

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)
from wilhelmina import WilmaError

from custom_components.wilma.const import (
    DOMAIN,
    EVENT_NEW_EXAM,
    EVENT_NEW_EXAM_GRADE,
    EVENT_NEW_HOMEWORK,
    MAX_LISTED_EXAMS,
)
from custom_components.wilma.coordinator import WilmaCoordinator, _StudentState

from .conftest import HELSINKI, make_overview, overview_exam

USER_ID = "!12345"
NOW = datetime.datetime(2026, 11, 4, 12, 0, tzinfo=HELSINKI)
TODAY = NOW.date()


@pytest.fixture(autouse=True)
def frozen_time(freezer: FrozenDateTimeFactory) -> FrozenDateTimeFactory:
    freezer.move_to(NOW)
    return freezer


def _day(days_from_now: int) -> str:
    return (TODAY + datetime.timedelta(days=days_from_now)).isoformat()


async def _coordinator(hass: HomeAssistant, entry: MockConfigEntry) -> WilmaCoordinator:
    entry.add_to_hass(hass)
    coordinator = WilmaCoordinator(hass, entry)
    await coordinator._async_setup()
    return coordinator


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> er.EntityRegistry:
    await hass.config.async_set_time_zone("Europe/Helsinki")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return er.async_get(hass)


def _entity_id(registry: er.EntityRegistry, domain: str, key: str) -> str:
    entity_id = registry.async_get_entity_id(domain, DOMAIN, f"test_345_{key}")
    assert entity_id is not None, key
    return entity_id


async def test_first_update_records_exams_and_homework_without_events(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    events = [
        async_capture_events(hass, event)
        for event in (EVENT_NEW_EXAM, EVENT_NEW_EXAM_GRADE, EVENT_NEW_HOMEWORK)
    ]
    coordinator = await _coordinator(hass, mock_config_entry)

    data = await coordinator._async_update_data()
    await hass.async_block_till_done()

    mock_client.get_overview.assert_awaited_once_with(user_id=USER_ID)
    student = data.students[USER_ID]
    assert [exam.id for exam in student.exams] == [501, 502, 503]
    assert [exam.id for exam in student.upcoming_exams(TODAY)] == [502, 503]
    assert [exam.id for exam in student.graded_exams()] == [501]
    assert [hw.text for hw in student.homework] == ["Page 20", "Page 12"]
    for captured in events:
        assert captured == []


async def test_new_exams_grades_and_homework_fire_events_once(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    coordinator = await _coordinator(hass, mock_config_entry)
    await coordinator._async_update_data()
    exam_events = async_capture_events(hass, EVENT_NEW_EXAM)
    grade_events = async_capture_events(hass, EVENT_NEW_EXAM_GRADE)
    homework_events = async_capture_events(hass, EVENT_NEW_HOMEWORK)

    mock_client.get_overview.side_effect = lambda user_id=None: make_overview(
        exams=[
            overview_exam(501, -10, "Matematik", grade="9"),
            overview_exam(502, -1, "Svenska", info="Word classes", grade="8+"),
            overview_exam(503, 8, "Engelska", info=None),
            overview_exam(504, 12, "Musik", info="Notes"),
        ],
        homework=[(3, 0, "Page 30"), (2, -1, "Page 20"), (1, -6, "Page 12")],
    )
    for _ in range(2):
        await coordinator._async_update_data()
        await hass.async_block_till_done()

    assert len(exam_events) == 1
    exam = exam_events[0].data
    assert exam["entry_id"] == "test"
    assert exam["student_id"] == USER_ID
    assert exam["student_name"] == "Anna Student"
    assert exam["id"] == 504
    assert exam["date"] == _day(12)
    assert exam["subject"] == "Musik"
    assert exam["info"] == "Notes"
    assert exam["teachers"] == ["Anna Teacher"]
    assert exam["grade"] is None

    assert len(grade_events) == 1
    grade = grade_events[0].data
    assert grade["id"] == 502
    assert grade["subject"] == "Svenska"
    assert grade["grade"] == "8+"
    assert grade["previous_grade"] is None
    assert grade["student_id"] == USER_ID

    assert len(homework_events) == 1
    homework = homework_events[0].data
    assert homework["text"] == "Page 30"
    assert homework["date"] == _day(0)
    assert homework["subject"] == "Matematik"
    assert homework["key"] == f"50|3|{_day(0)}"
    assert homework["student_name"] == "Anna Student"


async def test_changed_grade_and_new_graded_exam(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    coordinator = await _coordinator(hass, mock_config_entry)
    await coordinator._async_update_data()
    exam_events = async_capture_events(hass, EVENT_NEW_EXAM)
    grade_events = async_capture_events(hass, EVENT_NEW_EXAM_GRADE)

    mock_client.get_overview.side_effect = lambda user_id=None: make_overview(
        exams=[
            overview_exam(501, -10, "Matematik", grade="9-"),
            overview_exam(505, -2, "Historia", grade="10"),
        ]
    )
    await coordinator._async_update_data()
    await hass.async_block_till_done()

    assert [event.data["id"] for event in exam_events] == [505]
    assert [
        (event.data["id"], event.data["grade"], event.data["previous_grade"])
        for event in grade_events
    ] == [(501, "9-", "9"), (505, "10", None)]


async def test_seen_state_survives_a_restart(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    coordinator = await _coordinator(hass, mock_config_entry)
    await coordinator._async_update_data()

    restarted = await _coordinator(hass, mock_config_entry)
    events = [
        async_capture_events(hass, event)
        for event in (EVENT_NEW_EXAM, EVENT_NEW_EXAM_GRADE, EVENT_NEW_HOMEWORK)
    ]
    await restarted._async_update_data()
    await hass.async_block_till_done()

    for captured in events:
        assert captured == []
    stored = (await restarted.store.async_load())["students"][USER_ID]
    assert stored["seen_exam_ids"] == [501, 502, 503]
    assert stored["exam_grades"] == {"501": "9", "502": None, "503": None}
    assert len(stored["seen_homework_keys"]) == 2


def test_state_round_trip_without_exam_data() -> None:
    state = _StudentState.from_store({"messages": []})

    assert state.seen_exam_ids is None
    assert state.seen_homework_keys is None
    assert "seen_exam_ids" not in state.to_store()


async def test_overview_failure_keeps_previous_data(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    coordinator = await _coordinator(hass, mock_config_entry)
    first = await coordinator._async_update_data()
    mock_client.get_overview.side_effect = WilmaError("down")

    data = await coordinator._async_update_data()

    assert data.students[USER_ID].overview == first.students[USER_ID].overview
    assert data.students[USER_ID].messages
    assert "exams and homework for Anna Student" in coordinator.partial_errors[0]


async def test_exam_sensors(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    registry = await _setup(hass, mock_config_entry)

    next_exam = hass.states.get(_entity_id(registry, "sensor", "next_exam"))
    assert next_exam.state == "Svenska"
    assert next_exam.attributes["date"] == _day(3)
    assert next_exam.attributes["subject"] == "Svenska"
    assert next_exam.attributes["info"] == "Word classes"
    assert next_exam.attributes["teachers"] == ["Anna Teacher"]
    assert next_exam.attributes["days_until"] == 3

    upcoming = hass.states.get(_entity_id(registry, "sensor", "upcoming_exams"))
    assert upcoming.state == "2"
    assert upcoming.attributes["exams"] == [
        {
            "date": _day(3),
            "subject": "Svenska",
            "course": "sv sv05",
            "name": None,
            "info": "Word classes",
            "teachers": ["Anna Teacher"],
        },
        {
            "date": _day(8),
            "subject": "Engelska",
            "course": "en en05",
            "name": None,
            "info": None,
            "teachers": ["Anna Teacher"],
        },
    ]

    grade = hass.states.get(_entity_id(registry, "sensor", "latest_exam_grade"))
    assert grade.state == "9"
    assert grade.attributes["subject"] == "Matematik"
    assert grade.attributes["date"] == _day(-10)
    assert grade.attributes["seen"] == _day(-1)
    assert grade.attributes["graded_exams"] == [
        {
            "date": _day(-10),
            "subject": "Matematik",
            "course": "ma ma05",
            "grade": "9",
            "verbal_grade": None,
        }
    ]

    homework = hass.states.get(_entity_id(registry, "sensor", "latest_homework"))
    assert homework.state == "Page 20"
    assert homework.attributes["date"] == _day(-1)
    assert homework.attributes["subject"] == "Matematik"
    assert homework.attributes["recent_homework"] == [
        {
            "date": _day(-1),
            "subject": "Matematik",
            "course": "ma ma05",
            "text": "Page 20",
        },
        {
            "date": _day(-6),
            "subject": "Matematik",
            "course": "ma ma05",
            "text": "Page 12",
        },
    ]


async def test_graded_upcoming_exam_lists_its_grade(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    mock_client.get_overview.side_effect = lambda user_id=None: make_overview(
        exams=[overview_exam(510, 0, "Matematik", grade="10")]
    )
    registry = await _setup(hass, mock_config_entry)

    upcoming = hass.states.get(_entity_id(registry, "sensor", "upcoming_exams"))
    assert upcoming.attributes["exams"][0]["grade"] == "10"


async def test_exam_sensors_without_exams(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    mock_client.get_overview.side_effect = lambda user_id=None: make_overview(
        exams=[], homework=[]
    )
    registry = await _setup(hass, mock_config_entry)

    assert (
        hass.states.get(_entity_id(registry, "sensor", "next_exam")).state
        == STATE_UNKNOWN
    )
    upcoming = hass.states.get(_entity_id(registry, "sensor", "upcoming_exams"))
    assert upcoming.state == "0"
    assert upcoming.attributes["exams"] == []
    grade = hass.states.get(_entity_id(registry, "sensor", "latest_exam_grade"))
    assert grade.state == STATE_UNKNOWN
    assert grade.attributes["graded_exams"] == []
    homework = hass.states.get(_entity_id(registry, "sensor", "latest_homework"))
    assert homework.state == STATE_UNKNOWN
    assert homework.attributes["recent_homework"] == []


async def test_exam_sensors_when_overview_unavailable(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    mock_client.get_overview.side_effect = WilmaError("down")
    registry = await _setup(hass, mock_config_entry)

    for key in ("next_exam", "upcoming_exams", "latest_exam_grade", "latest_homework"):
        assert (
            hass.states.get(_entity_id(registry, "sensor", key)).state == STATE_UNKNOWN
        )


async def test_long_texts_are_truncated_and_attributes_stay_small(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    long_text = "x" * 5000
    mock_client.get_overview.side_effect = lambda user_id=None: make_overview(
        exams=[
            overview_exam(600 + i, i + 1, "Matematik", info=long_text, grade=long_text)
            for i in range(MAX_LISTED_EXAMS + 10)
        ],
        homework=[(row, -row, long_text) for row in range(1, 40)],
    )
    registry = await _setup(hass, mock_config_entry)

    upcoming = hass.states.get(_entity_id(registry, "sensor", "upcoming_exams"))
    assert upcoming.state == str(MAX_LISTED_EXAMS + 10)
    assert len(upcoming.attributes["exams"]) == MAX_LISTED_EXAMS
    assert len(upcoming.attributes["exams"][0]["info"]) == 300
    assert upcoming.attributes["exams"][0]["info"].endswith("…")

    next_exam = hass.states.get(_entity_id(registry, "sensor", "next_exam"))
    assert len(next_exam.attributes["info"]) == 1000

    homework = hass.states.get(_entity_id(registry, "sensor", "latest_homework"))
    assert len(homework.state) == 255
    assert len(homework.attributes["text"]) == 1000

    grade = hass.states.get(_entity_id(registry, "sensor", "latest_exam_grade"))
    assert len(grade.state) == 255

    for key in ("next_exam", "upcoming_exams", "latest_exam_grade", "latest_homework"):
        attributes = hass.states.get(_entity_id(registry, "sensor", key)).attributes
        assert len(json.dumps(dict(attributes))) < 16384 // 2, key


async def test_exam_calendar(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    registry = await _setup(hass, mock_config_entry)
    entity_id = _entity_id(registry, "calendar", "exams")

    state = hass.states.get(entity_id)
    assert state.state == "off"
    assert state.attributes["message"] == "Svenska"
    assert state.attributes["all_day"] is True
    assert state.attributes["start_time"] == f"{_day(3)} 00:00:00"
    assert state.attributes["description"] == "Word classes\n\nAnna Teacher"

    result = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": entity_id,
            "start_date_time": f"{_day(-10)}T12:00:00+02:00",
            "end_date_time": f"{_day(8)}T00:00:00+02:00",
        },
        blocking=True,
        return_response=True,
    )
    events = result[entity_id]["events"]
    assert [(event["summary"], event["start"]) for event in events] == [
        ("Matematik", _day(-10)),
        ("Svenska", _day(3)),
    ]
    assert events[0]["description"] == "Chapters 1-3\n\nAnna Teacher\n\n9"


async def test_exam_calendar_is_on_during_exam_day(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    mock_client.get_overview.side_effect = lambda user_id=None: make_overview(
        exams=[overview_exam(510, 0, "Matematik")]
    )
    registry = await _setup(hass, mock_config_entry)

    state = hass.states.get(_entity_id(registry, "calendar", "exams"))
    assert state.state == "on"
    assert state.attributes["message"] == "Matematik"
