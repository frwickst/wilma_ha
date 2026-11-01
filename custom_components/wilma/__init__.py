"""The Wilma integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import WilmaConfigEntry, WilmaCoordinator

PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: WilmaConfigEntry) -> bool:
    """Set up Wilma from a config entry."""
    coordinator = WilmaCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except BaseException:
        await coordinator.async_close_client()
        raise

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WilmaConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_close_client()
    return unload_ok
