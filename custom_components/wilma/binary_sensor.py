"""Binary sensor platform for Wilma integration."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    BINARY_SENSOR_PROBLEM,
    BINARY_SENSOR_RECENT_ATTENDANCE,
    BINARY_SENSOR_RECENT_BULLETIN,
    BINARY_SENSOR_RECENT_MESSAGE,
)
from .coordinator import StudentData, WilmaConfigEntry
from .entity import WilmaAccountEntity, WilmaStudentEntity

# How often "recent" sensors re-check whether their item is still recent
RECHECK_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WilmaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Wilma binary sensors."""
    coordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = [
        WilmaProblemSensor(coordinator, entry, BINARY_SENSOR_PROBLEM)
    ]
    for student in coordinator.data.students.values():
        entities.extend(
            [
                WilmaRecentMessageSensor(
                    coordinator, entry, student, BINARY_SENSOR_RECENT_MESSAGE
                ),
                WilmaRecentBulletinSensor(
                    coordinator, entry, student, BINARY_SENSOR_RECENT_BULLETIN
                ),
                WilmaRecentAttendanceSensor(
                    coordinator, entry, student, BINARY_SENSOR_RECENT_ATTENDANCE
                ),
            ]
        )
    async_add_entities(entities)


class WilmaProblemSensor(WilmaAccountEntity, BinarySensorEntity):
    """On when the last update failed, or some of the data could not be fetched."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Always available, so that it can report failures."""
        return True

    @property
    def is_on(self) -> bool:
        """Return whether there is a problem."""
        return not self.coordinator.last_update_success or bool(
            self.coordinator.partial_errors
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return what went wrong."""
        error = self.coordinator.last_exception
        return {
            "error": str(error)
            if error and not self.coordinator.last_update_success
            else None,
            "partial_errors": list(self.coordinator.partial_errors),
        }


class WilmaRecentSensor(WilmaStudentEntity, BinarySensorEntity):
    """Base class for sensors that are on while something new is recent."""

    async def async_added_to_hass(self) -> None:
        """Re-check periodically so the sensor turns off when the item stops being recent."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(self.hass, self._handle_time, RECHECK_INTERVAL)
        )

    @callback
    def _handle_time(self, now: datetime) -> None:
        self.async_write_ha_state()

    def _recent(self, student: StudentData) -> bool:
        raise NotImplementedError

    @property
    def is_on(self) -> bool:
        """Return whether the student's latest item is recent."""
        student = self.student
        return self._recent(student) if student else False

    def _within_threshold(self, moment: datetime | None) -> bool:
        return (
            moment is not None
            and dt_util.utcnow() - moment <= self.coordinator.recent_threshold
        )

    def _date_within_threshold(self, day: date | None) -> bool:
        """Whether a date, taken as the start of that day, is within the threshold."""
        if day is None:
            return False
        return self._within_threshold(
            datetime.combine(day, time(), self.coordinator.timezone)
        )


class WilmaRecentMessageSensor(WilmaRecentSensor):
    """On while the latest message was sent within the recent threshold."""

    def _recent(self, student: StudentData) -> bool:
        message = student.latest_message
        if not message:
            return False
        try:
            sent = datetime.strptime(str(message.get("timestamp")), "%Y-%m-%d %H:%M")
        except ValueError:
            return False
        return self._within_threshold(sent.replace(tzinfo=self.coordinator.timezone))


class WilmaRecentBulletinSensor(WilmaRecentSensor):
    """On while a bulletin appeared, or the latest one is dated, within the recent threshold."""

    def _recent(self, student: StudentData) -> bool:
        if student.new_bulletin_count:
            return True
        bulletin = student.latest_bulletin
        dated = bulletin.get("date") if bulletin else None
        return self._date_within_threshold(date.fromisoformat(dated) if dated else None)


class WilmaRecentAttendanceSensor(WilmaRecentSensor):
    """On while a mark appeared, or the latest one is dated, within the recent threshold."""

    def _recent(self, student: StudentData) -> bool:
        if self._within_threshold(student.latest_new_mark_seen):
            return True
        mark = student.latest_attendance_mark
        return self._date_within_threshold(mark.date if mark else None)
