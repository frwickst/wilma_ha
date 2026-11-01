"""Tests for the schedule calendar and sensors."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from wilhelmina import WilmaError

from custom_components.wilma.const import DOMAIN

from .conftest import HELSINKI, make_week

# A Wednesday, after the day's last lesson
NOW = datetime.datetime(2026, 11, 4, 10, 30, tzinfo=HELSINKI)
MONDAY = datetime.date(2026, 11, 2)


@pytest.fixture(autouse=True)
def frozen_time(freezer: FrozenDateTimeFactory) -> FrozenDateTimeFactory:
    freezer.move_to(NOW)
    return freezer


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> er.EntityRegistry:
    await hass.config.async_set_time_zone("Europe/Helsinki")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return er.async_get(hass)


def _entity_id(registry: er.EntityRegistry, domain: str, key: str) -> str:
    entity_id = registry.async_get_entity_id(domain, DOMAIN, f"test_{key}")
    assert entity_id is not None
    return entity_id


async def test_fetches_current_and_next_week(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    await _setup(hass, mock_config_entry)

    fetched = [call.args[0] for call in mock_client.get_schedule.await_args_list]
    assert fetched == [MONDAY, MONDAY + datetime.timedelta(days=7)]


async def test_day_and_week_sensors(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    registry = await _setup(hass, mock_config_entry)

    today = hass.states.get(_entity_id(registry, "sensor", "lessons_today"))
    assert today.state == "2"
    assert today.attributes["date"] == "2026-11-04"
    assert today.attributes["start"] == "2026-11-04T08:15:00+02:00"
    assert today.attributes["end"] == "2026-11-04T10:00:00+02:00"
    assert today.attributes["lessons"][1] == {
        "start": "2026-11-04T09:15:00+02:00",
        "end": "2026-11-04T10:00:00+02:00",
        "subject": "Svenska",
        "teachers": ["Anna Teacher"],
        "rooms": ["419"],
    }

    tomorrow = hass.states.get(_entity_id(registry, "sensor", "lessons_tomorrow"))
    assert tomorrow.state == "2"
    assert tomorrow.attributes["date"] == "2026-11-05"

    week = hass.states.get(_entity_id(registry, "sensor", "lessons_this_week"))
    assert week.state == "10"
    assert week.attributes["week_start"] == "2026-11-02"
    assert week.attributes["week_end"] == "2026-11-08"
    assert len(week.attributes["lessons"]) == 10


async def test_sensors_roll_over_at_midnight(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
    frozen_time: FrozenDateTimeFactory,
) -> None:
    registry = await _setup(hass, mock_config_entry)
    tomorrow_id = _entity_id(registry, "sensor", "lessons_tomorrow")

    # Friday evening: tomorrow is Saturday, without lessons
    friday_evening = datetime.datetime(2026, 11, 6, 23, 59, 50, tzinfo=HELSINKI)
    frozen_time.move_to(friday_evening)
    async_fire_time_changed(hass, friday_evening)
    await hass.async_block_till_done()
    hass.states.async_set(tomorrow_id, "stale")  # make the next write observable

    # Sunday 00:00:01: tomorrow is Monday of the next week, which is already fetched
    sunday = datetime.datetime(2026, 11, 8, 0, 0, 1, tzinfo=HELSINKI)
    frozen_time.move_to(sunday)
    async_fire_time_changed(hass, sunday)
    await hass.async_block_till_done()

    tomorrow = hass.states.get(tomorrow_id)
    assert tomorrow.state == "2"
    assert tomorrow.attributes["date"] == "2026-11-09"


async def test_holiday_shows_zero_lessons(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    mock_client.get_schedule.side_effect = lambda day: make_week(day, weekdays=0)
    registry = await _setup(hass, mock_config_entry)

    today = hass.states.get(_entity_id(registry, "sensor", "lessons_today"))
    assert today.state == "0"
    assert today.attributes["start"] is None
    assert today.attributes["lessons"] == []


async def test_schedule_failure_keeps_other_data(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_client.get_schedule.side_effect = WilmaError("schedule down")
    registry = await _setup(hass, mock_config_entry)

    assert hass.states.get(_entity_id(registry, "sensor", "latest_message")).state == (
        "Recent message"
    )
    assert (
        hass.states.get(_entity_id(registry, "sensor", "lessons_today")).state
        == "unknown"
    )
    assert "Could not fetch the schedule" in caplog.text


async def test_calendar_state_is_next_lesson(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    registry = await _setup(hass, mock_config_entry)

    state = hass.states.get(_entity_id(registry, "calendar", "schedule"))
    assert state.state == "off"
    assert state.attributes["message"] == "Matematik"
    assert state.attributes["start_time"] == "2026-11-05 08:15:00"
    assert state.attributes["location"] == "419"
    assert state.attributes["description"] == "Anna Teacher\n3B"


async def test_calendar_is_on_during_lesson(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
    frozen_time: FrozenDateTimeFactory,
) -> None:
    frozen_time.move_to(datetime.datetime(2026, 11, 4, 9, 30, tzinfo=HELSINKI))
    registry = await _setup(hass, mock_config_entry)

    state = hass.states.get(_entity_id(registry, "calendar", "schedule"))
    assert state.state == "on"
    assert state.attributes["message"] == "Svenska"


async def test_calendar_get_events(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    registry = await _setup(hass, mock_config_entry)
    entity_id = _entity_id(registry, "calendar", "schedule")
    mock_client.get_schedule.reset_mock()

    # This week: served from the coordinator's data, no requests
    result = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": entity_id,
            "start_date_time": "2026-11-02T00:00:00+02:00",
            "end_date_time": "2026-11-09T00:00:00+02:00",
        },
        blocking=True,
        return_response=True,
    )
    events = result[entity_id]["events"]
    assert len(events) == 10
    assert events[0]["summary"] == "Matematik"
    assert events[0]["start"] == "2026-11-02T08:15:00+02:00"
    mock_client.get_schedule.assert_not_awaited()

    # A later week: fetched once, then cached
    for _ in range(2):
        result = await hass.services.async_call(
            "calendar",
            "get_events",
            {
                "entity_id": entity_id,
                "start_date_time": "2026-11-23T00:00:00+02:00",
                "end_date_time": "2026-11-24T00:00:00+02:00",
            },
            blocking=True,
            return_response=True,
        )
        assert len(result[entity_id]["events"]) == 2
    assert [c.args[0] for c in mock_client.get_schedule.await_args_list] == [
        datetime.date(2026, 11, 23)
    ]


async def test_calendar_get_events_error(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    registry = await _setup(hass, mock_config_entry)
    entity_id = _entity_id(registry, "calendar", "schedule")
    mock_client.get_schedule.side_effect = WilmaError("down")

    with pytest.raises(HomeAssistantError, match="Could not fetch the Wilma schedule"):
        await hass.services.async_call(
            "calendar",
            "get_events",
            {
                "entity_id": entity_id,
                "start_date_time": "2027-01-04T00:00:00+02:00",
                "end_date_time": "2027-01-05T00:00:00+02:00",
            },
            blocking=True,
            return_response=True,
        )


async def test_calendar_query_is_capped(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    await _setup(hass, mock_config_entry)
    coordinator = mock_config_entry.runtime_data
    mock_client.get_schedule.reset_mock()

    weeks = await coordinator.async_get_weeks(
        datetime.date(2027, 1, 1), datetime.date(2027, 12, 31)
    )

    assert len(weeks) == 12
    assert mock_client.get_schedule.await_count == 12
