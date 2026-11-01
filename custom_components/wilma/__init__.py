"""The Wilma integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import LEGACY_STUDENT_ENTITY_KEYS
from .coordinator import StudentData, WilmaConfigEntry, WilmaCoordinator
from .entity import student_key

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: WilmaConfigEntry) -> bool:
    """Set up Wilma from a config entry."""
    coordinator = WilmaCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except BaseException:
        await coordinator.async_close_client()
        raise

    _migrate_legacy_unique_ids(hass, entry, coordinator)

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WilmaConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_close_client()
    return unload_ok


async def _async_options_updated(hass: HomeAssistant, entry: WilmaConfigEntry) -> None:
    """Reload so that changed options take effect."""
    await hass.config_entries.async_reload(entry.entry_id)


@callback
def _migrate_legacy_unique_ids(
    hass: HomeAssistant, entry: WilmaConfigEntry, coordinator: WilmaCoordinator
) -> None:
    """Move entities from before multi-student support to the account's primary student.

    Their unique IDs had no student part; keeping the entities (rather than creating new
    ones) preserves their entity IDs and history.
    """
    primary = coordinator.primary_student
    if primary is None or primary.user_id is None:
        return
    student = coordinator.data.students.get(primary.user_id)
    if not isinstance(student, StudentData):
        return

    registry = er.async_get(hass)
    for key in LEGACY_STUDENT_ENTITY_KEYS:
        for domain in ("sensor", "calendar"):
            entity_id = registry.async_get_entity_id(
                domain, "wilma", f"{entry.entry_id}_{key}"
            )
            if entity_id is None:
                continue
            new_unique_id = f"{entry.entry_id}_{student_key(student)}_{key}"
            if registry.async_get_entity_id(domain, "wilma", new_unique_id) is None:
                registry.async_update_entity(entity_id, new_unique_id=new_unique_id)
