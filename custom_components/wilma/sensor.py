"""Sensor platform for Wilma integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_CONTENT,
    ATTR_CONTENT_MARKDOWN,
    ATTR_ID,
    ATTR_SENDER,
    ATTR_SUBJECT,
    ATTR_TIMESTAMP,
    DOMAIN,
    SENSOR_LATEST_MESSAGE,
)
from .coordinator import WilmaCoordinator

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS = [
    SensorEntityDescription(
        key=SENSOR_LATEST_MESSAGE,
        name="Latest Message",
        icon="mdi:email",
    )
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Wilma sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for description in SENSOR_DESCRIPTIONS:
        entities.append(WilmaSensor(coordinator, description, entry))

    # Add last update status sensor
    entities.append(
        WilmaLastUpdateSensor(
            coordinator,
            SensorEntityDescription(
                key="last_update",
                name="Last Update",
                icon="mdi:update",
                device_class=SensorDeviceClass.TIMESTAMP,
                entity_category=EntityCategory.DIAGNOSTIC,
            ),
            entry,
        )
    )

    async_add_entities(entities)


class WilmaSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing Wilma message data."""

    def __init__(
        self,
        coordinator: WilmaCoordinator,
        description: SensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_name = f"{description.name}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Wilma ({entry.data.get('username')})",
            "manufacturer": "Visma",
            "model": "Wilma",
            "sw_version": "1.0.0",
        }
        self._message = None

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        if not self.coordinator.data:
            return None

        key = self.entity_description.key
        if key == SENSOR_LATEST_MESSAGE:
            message = self.coordinator.data.get("latest_message")
        else:
            return None

        self._message = message
        if not message:
            return None

        return message["subject"]

    @property
    def extra_state_attributes(self) -> Optional[Dict[str, Any]]:
        """Return entity specific state attributes."""
        if not self._message:
            return None

        attrs = {
            ATTR_ID: self._message["id"],
            ATTR_SUBJECT: self._message["subject"],
            ATTR_SENDER: self._message["sender"],
            ATTR_TIMESTAMP: self._message["timestamp"],
        }

        # Add content if available
        if "content_html" in self._message and self._message["content_html"]:
            attrs[ATTR_CONTENT] = self._message["content_html"]
            try:
                attrs[ATTR_CONTENT_MARKDOWN] = self._message["content_markdown"]
            except Exception:
                pass

        return attrs


class WilmaLastUpdateSensor(CoordinatorEntity, SensorEntity):
    """Sensor for tracking the last successful update time."""

    def __init__(
        self,
        coordinator: WilmaCoordinator,
        description: SensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the last update sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_name = f"{description.name}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Wilma ({entry.data.get('username')})",
            "manufacturer": "Visma",
            "model": "Wilma",
            "sw_version": "1.0.0",
        }

    @property
    def native_value(self) -> datetime | None:
        """Return the value reported by the sensor."""
        if self.coordinator.data and "last_update" in self.coordinator.data:
            return self.coordinator.data["last_update"]
        if self.coordinator.last_update_success_time:
            return dt_util.as_local(self.coordinator.last_update_success_time)
        return None
