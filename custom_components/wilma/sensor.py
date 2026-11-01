"""Sensor platform for Wilma integration."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from wilhelmina import Lesson, WeekSchedule

from .const import (
    ATTR_CONTENT,
    ATTR_CONTENT_MARKDOWN,
    ATTR_ID,
    ATTR_SENDER,
    ATTR_SUBJECT,
    ATTR_TIMESTAMP,
    SENSOR_LAST_UPDATE,
    SENSOR_LATEST_ATTENDANCE_MARK,
    SENSOR_LATEST_MESSAGE,
    SENSOR_LESSONS_THIS_WEEK,
    SENSOR_LESSONS_TODAY,
    SENSOR_LESSONS_TOMORROW,
)
from .coordinator import (
    WilmaConfigEntry,
    WilmaCoordinator,
    lesson_attributes,
    mark_attributes,
    week_start,
)
from .entity import device_info

LATEST_MESSAGE = SensorEntityDescription(
    key=SENSOR_LATEST_MESSAGE,
    translation_key=SENSOR_LATEST_MESSAGE,
    icon="mdi:email",
)
LATEST_ATTENDANCE_MARK = SensorEntityDescription(
    key=SENSOR_LATEST_ATTENDANCE_MARK,
    translation_key=SENSOR_LATEST_ATTENDANCE_MARK,
    icon="mdi:clipboard-text-clock",
)
LAST_UPDATE = SensorEntityDescription(
    key=SENSOR_LAST_UPDATE,
    translation_key=SENSOR_LAST_UPDATE,
    icon="mdi:update",
    device_class=SensorDeviceClass.TIMESTAMP,
    entity_category=EntityCategory.DIAGNOSTIC,
)
LESSONS_TODAY = SensorEntityDescription(
    key=SENSOR_LESSONS_TODAY,
    translation_key=SENSOR_LESSONS_TODAY,
    icon="mdi:calendar-today",
)
LESSONS_TOMORROW = SensorEntityDescription(
    key=SENSOR_LESSONS_TOMORROW,
    translation_key=SENSOR_LESSONS_TOMORROW,
    icon="mdi:calendar-arrow-right",
)
LESSONS_THIS_WEEK = SensorEntityDescription(
    key=SENSOR_LESSONS_THIS_WEEK,
    translation_key=SENSOR_LESSONS_THIS_WEEK,
    icon="mdi:calendar-week",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WilmaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Wilma sensor platform."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            WilmaLatestMessageSensor(coordinator, LATEST_MESSAGE, entry),
            WilmaLatestAttendanceMarkSensor(coordinator, LATEST_ATTENDANCE_MARK, entry),
            WilmaLastUpdateSensor(coordinator, LAST_UPDATE, entry),
            WilmaLessonsOnDaySensor(coordinator, LESSONS_TODAY, entry, days_ahead=0),
            WilmaLessonsOnDaySensor(coordinator, LESSONS_TOMORROW, entry, days_ahead=1),
            WilmaLessonsThisWeekSensor(coordinator, LESSONS_THIS_WEEK, entry),
        ]
    )


class WilmaEntity(CoordinatorEntity[WilmaCoordinator], SensorEntity):
    """Base class for Wilma sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WilmaCoordinator,
        description: SensorEntityDescription,
        entry: WilmaConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = device_info(entry)


class WilmaLatestMessageSensor(WilmaEntity):
    """The newest Wilma message, with its subject as state."""

    @property
    def _message(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        return data.latest_message if data else None

    @property
    def native_value(self) -> str | None:
        """Return the subject of the latest message."""
        message = self._message
        return message.get("subject") if message else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return details of the latest message."""
        message = self._message
        if not message:
            return None

        attrs: dict[str, Any] = {
            ATTR_ID: message.get("id"),
            ATTR_SUBJECT: message.get("subject"),
            ATTR_SENDER: message.get("sender"),
            ATTR_TIMESTAMP: message.get("timestamp"),
        }
        if message.get("content_html"):
            attrs[ATTR_CONTENT] = message["content_html"]
            attrs[ATTR_CONTENT_MARKDOWN] = message.get("content_markdown")
        return attrs


class WilmaLatestAttendanceMarkSensor(WilmaEntity):
    """The most recent attendance mark (absence, feedback, homework note, etc.)."""

    @property
    def native_value(self) -> str | None:
        """Return the description of the latest mark's type."""
        data = self.coordinator.data
        mark = data.latest_attendance_mark if data else None
        return mark.type.description if mark else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return details of the latest mark, and mark counts for the school year."""
        data = self.coordinator.data
        if not data or not data.attendance:
            return None

        attrs: dict[str, Any] = {}
        mark = data.latest_attendance_mark
        if mark:
            attrs.update(mark_attributes(mark))
        attrs["marks_this_school_year"] = len(data.attendance.marks)
        attrs["counts_by_type"] = dict(
            Counter(m.type.description for m in data.attendance.marks)
        )
        return attrs


class WilmaLastUpdateSensor(WilmaEntity):
    """Time of the last successful update."""

    @property
    def native_value(self) -> datetime | None:
        """Return the time of the last successful update."""
        data = self.coordinator.data
        return data.last_update if data else None


class WilmaScheduleSensor(WilmaEntity):
    """Base class for sensors showing lessons, refreshed at midnight as well."""

    _attr_native_unit_of_measurement = "lessons"

    async def async_added_to_hass(self) -> None:
        """Re-evaluate at the start of each day, between coordinator updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_change(
                self.hass, self._handle_new_day, hour=0, minute=0, second=1
            )
        )

    @callback
    def _handle_new_day(self, now: datetime) -> None:
        self.async_write_ha_state()

    def _today(self) -> date:
        return datetime.now(self.coordinator.timezone).date()

    def _summary(self, lessons: list[Lesson]) -> dict[str, Any]:
        tz = self.coordinator.timezone
        items = [lesson_attributes(lesson, tz) for lesson in lessons]
        return {
            "start": items[0]["start"] if items else None,
            "end": max(item["end"] for item in items) if items else None,
            "lessons": items,
        }


class WilmaLessonsOnDaySensor(WilmaScheduleSensor):
    """Number of lessons on a day relative to today, with the lessons as attributes."""

    def __init__(
        self,
        coordinator: WilmaCoordinator,
        description: SensorEntityDescription,
        entry: WilmaConfigEntry,
        days_ahead: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description, entry)
        self._days_ahead = days_ahead

    def _lessons(self) -> tuple[date, list[Lesson] | None]:
        day = self._today() + timedelta(days=self._days_ahead)
        data = self.coordinator.data
        return day, data.lessons_on(day) if data else None

    @property
    def native_value(self) -> int | None:
        """Return the number of lessons on the day."""
        _, lessons = self._lessons()
        return len(lessons) if lessons is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the day, its first start and last end, and its lessons."""
        day, lessons = self._lessons()
        if lessons is None:
            return None
        return {"date": day.isoformat(), **self._summary(lessons)}


class WilmaLessonsThisWeekSensor(WilmaScheduleSensor):
    """Number of lessons this week, with the lessons as attributes."""

    def _week(self) -> WeekSchedule | None:
        data = self.coordinator.data
        return data.schedule.get(week_start(self._today())) if data else None

    @property
    def native_value(self) -> int | None:
        """Return the number of lessons this week."""
        week = self._week()
        return len(week.lessons) if week else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the week's dates, start and end times, and lessons."""
        week = self._week()
        if not week:
            return None
        return {
            "week_start": week.week_start.isoformat(),
            "week_end": week.week_end.isoformat(),
            **self._summary(week.lessons),
        }
