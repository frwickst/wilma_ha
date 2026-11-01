"""Shared entity helpers for the Wilma integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import CONF_SERVER_URL, CONF_USERNAME, DOMAIN
from .coordinator import WilmaConfigEntry


def device_info(entry: WilmaConfigEntry) -> DeviceInfo:
    """The device all of an account's entities belong to."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Wilma ({entry.data.get(CONF_USERNAME)})",
        manufacturer="Visma",
        model="Wilma",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=entry.data.get(CONF_SERVER_URL),
    )
