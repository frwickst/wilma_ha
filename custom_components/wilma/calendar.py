"""Calendar platform showing the Wilma schedule."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from wilhelmina import Lesson, WilmaError

from .const import CALENDAR_SCHEDULE
from .coordinator import WilmaConfigEntry, WilmaCoordinator
from .entity import device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WilmaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Wilma schedule calendar."""
    async_add_entities([WilmaScheduleCalendar(entry.runtime_data, entry)])


class WilmaScheduleCalendar(CoordinatorEntity[WilmaCoordinator], CalendarEntity):
    """The student's lessons as calendar events."""

    _attr_has_entity_name = True
    _attr_translation_key = CALENDAR_SCHEDULE

    def __init__(self, coordinator: WilmaCoordinator, entry: WilmaConfigEntry) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{CALENDAR_SCHEDULE}"
        self._attr_device_info = device_info(entry)

    def _to_event(self, lesson: Lesson) -> CalendarEvent:
        tz = self.coordinator.timezone
        details = []
        if lesson.teachers:
            details.append(", ".join(lesson.teachers))
        if lesson.class_name:
            details.append(lesson.class_name)
        return CalendarEvent(
            start=lesson.starts_at.replace(tzinfo=tz),
            end=lesson.ends_at.replace(tzinfo=tz),
            summary=lesson.subject,
            location=", ".join(lesson.rooms) or None,
            description="\n".join(details) or None,
        )

    @property
    def event(self) -> CalendarEvent | None:
        """The ongoing lesson, or else the next one within the current and next week."""
        data = self.coordinator.data
        if not data:
            return None
        now = dt_util.now()
        lessons = sorted(
            (lesson for week in data.schedule.values() for lesson in week.lessons),
            key=lambda lesson: lesson.starts_at,
        )
        for lesson in lessons:
            event = self._to_event(lesson)
            if event.end > now:
                return event
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Lessons between ``start_date`` and ``end_date``."""
        tz = self.coordinator.timezone
        start = start_date.astimezone(tz)
        end = end_date.astimezone(tz)
        try:
            weeks = await self.coordinator.async_get_weeks(start.date(), end.date())
        except WilmaError as err:
            raise HomeAssistantError(
                f"Could not fetch the Wilma schedule: {err}"
            ) from err

        events = [self._to_event(lesson) for week in weeks for lesson in week.lessons]
        return [
            event
            for event in events
            if event.end > start_date and event.start < end_date
        ]
