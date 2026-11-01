"""Calendar platform showing the Wilma schedule."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util
from wilhelmina import Lesson, WilmaError

from .const import CALENDAR_SCHEDULE
from .coordinator import WilmaConfigEntry
from .entity import WilmaStudentEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WilmaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up a schedule calendar per student."""
    coordinator = entry.runtime_data
    async_add_entities(
        WilmaScheduleCalendar(coordinator, entry, student, CALENDAR_SCHEDULE)
        for student in coordinator.data.students.values()
    )


class WilmaScheduleCalendar(WilmaStudentEntity, CalendarEntity):
    """A student's lessons as calendar events."""

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
        student = self.student
        if not student:
            return None
        now = dt_util.now()
        for lesson in student.upcoming_lessons():
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
            weeks = await self.coordinator.async_get_weeks(
                self._user_id, start.date(), end.date()
            )
        except WilmaError as err:
            raise HomeAssistantError(
                f"Could not fetch the Wilma schedule: {err}"
            ) from err

        events = [self._to_event(lesson) for week in weeks for lesson in week.lessons]
        return [e for e in events if e.end > start_date and e.start < end_date]
