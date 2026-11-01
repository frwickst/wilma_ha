"""Tests for setting up and unloading the Wilma integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from wilhelmina import AuthenticationError

from custom_components.wilma.const import (
    CONF_RECENT_THRESHOLD_HOURS,
    CONF_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)

STUDENT_ENTITIES = {
    "sensor": (
        "latest_message",
        "unread_count",
        "latest_attendance_mark",
        "attendance_count",
        "latest_bulletin",
        "unread_bulletin_count",
        "next_lesson",
        "lessons_today",
        "lessons_tomorrow",
        "lessons_this_week",
    ),
    "binary_sensor": ("recent_message", "recent_bulletin", "recent_attendance"),
    "calendar": ("schedule",),
}
ACCOUNT_ENTITIES = {"sensor": ("last_update",), "binary_sensor": ("problem",)}


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_and_unload_entry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    await _setup(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED
    entities = er.async_get(hass)
    devices = dr.async_get(hass)
    student_device = devices.async_get_device_by_identifier(
        (DOMAIN, "test_345"), "test"
    )
    account_device = devices.async_get_device_by_identifier((DOMAIN, "test"), "test")
    assert student_device.name == "Wilma Anna"
    assert account_device.name == "Wilma (testuser)"
    for domain, keys in STUDENT_ENTITIES.items():
        for key in keys:
            entity_id = entities.async_get_entity_id(domain, DOMAIN, f"test_345_{key}")
            assert entity_id is not None, key
            assert entities.async_get(entity_id).device_id == student_device.id
    for domain, keys in ACCOUNT_ENTITIES.items():
        for key in keys:
            entity_id = entities.async_get_entity_id(domain, DOMAIN, f"test_{key}")
            assert entity_id is not None, key
            assert entities.async_get(entity_id).device_id == account_device.id

    # Names come from the translations, prefixed with the student's device name
    next_lesson = entities.async_get_entity_id("sensor", DOMAIN, "test_345_next_lesson")
    assert (
        hass.states.get(next_lesson).attributes["friendly_name"]
        == "Wilma Anna Next lesson"
    )
    problem = entities.async_get_entity_id("binary_sensor", DOMAIN, "test_problem")
    assert (
        hass.states.get(problem).attributes["friendly_name"]
        == "Wilma (testuser) Problem"
    )

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    mock_client.close.assert_awaited()


async def test_entities_from_before_multi_student_support_are_kept(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    mock_config_entry.add_to_hass(hass)
    entities = er.async_get(hass)
    old = {
        ("sensor", "latest_message"): "sensor.wilma_testuser_latest_message",
        ("sensor", "lessons_today"): "sensor.wilma_testuser_lessons_today",
        ("calendar", "schedule"): "calendar.wilma_testuser_schedule",
    }
    for (domain, key), entity_id in old.items():
        entities.async_get_or_create(
            domain,
            DOMAIN,
            f"test_{key}",
            config_entry=mock_config_entry,
            suggested_object_id=entity_id.split(".", 1)[1],
        )

    await _setup(hass, mock_config_entry)

    for (domain, key), entity_id in old.items():
        assert (
            entities.async_get_entity_id(domain, DOMAIN, f"test_345_{key}") == entity_id
        )
        assert entities.async_get_entity_id(domain, DOMAIN, f"test_{key}") is None
        assert hass.states.get(entity_id) is not None


async def test_two_students_get_their_own_devices(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_two_student_client: MagicMock,
) -> None:
    await _setup(hass, mock_config_entry)

    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    for key, name in (("345", "Wilma Anna"), ("678", "Wilma Bo")):
        device = devices.async_get_device_by_identifier((DOMAIN, f"test_{key}"), "test")
        assert device.name == name
        entity_id = entities.async_get_entity_id(
            "sensor", DOMAIN, f"test_{key}_latest_message"
        )
        assert entities.async_get(entity_id).device_id == device.id


async def test_setup_retries_when_login_fails(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    mock_client.login = AsyncMock(side_effect=AuthenticationError("bad password"))
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
    mock_client.close.assert_awaited()


async def test_options_change_reloads_with_new_interval(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_client: MagicMock
) -> None:
    await _setup(hass, mock_config_entry)
    assert mock_config_entry.runtime_data.update_interval.total_seconds() == 30 * 60

    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={CONF_SCAN_INTERVAL_MINUTES: 10, CONF_RECENT_THRESHOLD_HOURS: 6},
    )
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    assert coordinator.update_interval.total_seconds() == 10 * 60
    assert coordinator.recent_threshold.total_seconds() == 6 * 3600
