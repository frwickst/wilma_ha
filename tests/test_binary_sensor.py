"""Tests for the Wilma binary sensors."""

from __future__ import annotations

import dataclasses
import datetime
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from wilhelmina import WilmaError

from custom_components.wilma.const import DOMAIN

from .conftest import HOMEWORK, make_bulletins, make_mark, make_message, make_report


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> er.EntityRegistry:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return er.async_get(hass)


def _entity_id(registry: er.EntityRegistry, unique_id: str) -> str:
    entity_id = registry.async_get_entity_id("binary_sensor", DOMAIN, unique_id)
    assert entity_id is not None, unique_id
    return entity_id


async def test_recent_sensors_on_for_recent_items(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    # The fixtures have a message from a day ago, a bulletin dated today and a mark from
    # two days ago; the default threshold is 24 hours.
    mock_client.get_messages.side_effect = lambda **kwargs: [
        make_message(2, "Recent message", days_ago=0.5)
    ]
    registry = await _setup(hass, mock_config_entry)

    assert (
        hass.states.get(_entity_id(registry, "test_345_recent_message")).state
        == STATE_ON
    )
    assert (
        hass.states.get(_entity_id(registry, "test_345_recent_bulletin")).state
        == STATE_ON
    )
    assert (
        hass.states.get(_entity_id(registry, "test_345_recent_attendance")).state
        == STATE_OFF
    )


async def test_recent_sensors_off_for_old_items(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    mock_client.get_messages.side_effect = lambda **kwargs: [
        make_message(2, "Old message", days_ago=3)
    ]
    mock_client.get_bulletins.side_effect = lambda user_id=None: [
        dataclasses.replace(bulletin, date=datetime.date(2020, 1, 1))
        for bulletin in make_bulletins(10)
    ]
    registry = await _setup(hass, mock_config_entry)

    assert (
        hass.states.get(_entity_id(registry, "test_345_recent_message")).state
        == STATE_OFF
    )
    assert (
        hass.states.get(_entity_id(registry, "test_345_recent_bulletin")).state
        == STATE_OFF
    )


async def test_recent_attendance_turns_on_for_new_mark_and_off_later(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    registry = await _setup(hass, mock_config_entry)
    entity_id = _entity_id(registry, "test_345_recent_attendance")
    assert hass.states.get(entity_id).state == STATE_OFF

    # A mark dated last week appears (entered late): it is new, so it counts as recent
    late_report = make_report(make_mark(HOMEWORK, days_ago=7, hour=11))
    mock_client.get_attendance.side_effect = lambda *a, **k: late_report
    await mock_config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_ON

    freezer.tick(datetime.timedelta(hours=25))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_OFF


async def test_problem_sensor(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    registry = await _setup(hass, mock_config_entry)
    entity_id = _entity_id(registry, "test_problem")
    coordinator = mock_config_entry.runtime_data
    assert hass.states.get(entity_id).state == STATE_OFF

    # Part of the data fails
    mock_client.get_bulletins.side_effect = WilmaError("bulletins down")
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.state == STATE_ON
    assert "bulletins down" in state.attributes["partial_errors"][0]

    # The whole update fails
    mock_client.get_messages.side_effect = WilmaError("all down")
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.state == STATE_ON
    assert "all down" in state.attributes["error"]
