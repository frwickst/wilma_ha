"""Calendar platform showing the Wilma schedule and exams."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util
from wilhelmina import Exam, Lesson, WilmaError

from .const import CALENDAR_EXAMS, CALENDAR_SCHEDULE
from .coordinator import WilmaConfigEntry, exam_grade
from .entity import WilmaStudentEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WilmaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up a schedule and an exam calendar per student."""
    coordinator = entry.runtime_data
    entities: list[CalendarEntity] = []
    for student in coordinator.data.students.values():
        entities.append(
            WilmaScheduleCalendar(coordinator, entry, student, CALENDAR_SCHEDULE)
        )
        entities.append(WilmaExamCalendar(coordinator, entry, student, CALENDAR_EXAMS))
    async_add_entities(entities)


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


class WilmaExamCalendar(WilmaStudentEntity, CalendarEntity):
    """A student's exams (of the current courses) as all-day events."""

    def _to_event(self, exam: Exam) -> CalendarEvent:
        details = []
        if exam.info:
            details.append(exam.info)
        if exam.teacher_names:
            details.append(", ".join(exam.teacher_names))
        if grade := exam_grade(exam):
            details.append(grade)
        return CalendarEvent(
            start=exam.date,
            end=exam.date + timedelta(days=1),
            summary=exam.title,
            description="\n\n".join(details) or None,
            uid=f"wilma-exam-{exam.id}",
        )

    def _exams(self) -> list[Exam]:
        student = self.student
        return (student.exams or []) if student else []

    @property
    def event(self) -> CalendarEvent | None:
        """Today's exam, or else the next one."""
        today = datetime.now(self.coordinator.timezone).date()
        for exam in self._exams():
            if exam.date >= today:
                return self._to_event(exam)
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Exams between ``start_date`` and ``end_date``."""
        tz = self.coordinator.timezone
        start = start_date.astimezone(tz).date()
        end = end_date.astimezone(tz)
        # An all-day event ends at the start of the next day
        last = (
            end.date()
            if end.time() > datetime.min.time()
            else end.date() - timedelta(days=1)
        )
        return [
            self._to_event(exam) for exam in self._exams() if start <= exam.date <= last
        ]
