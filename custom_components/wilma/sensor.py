"""Sensor platform for Wilma integration."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_time_change,
)
from homeassistant.util import dt as dt_util
from wilhelmina import Exam, Homework, Lesson, WeekSchedule

from .const import (
    ATTR_CONTENT,
    ATTR_CONTENT_MARKDOWN,
    ATTR_ID,
    ATTR_SENDER,
    ATTR_SUBJECT,
    ATTR_TIMESTAMP,
    MAX_GRADE_LENGTH,
    MAX_LIST_TEXT_LENGTH,
    MAX_LISTED_EXAMS,
    MAX_STATE_LENGTH,
    RECENT_GRADES,
    RECENT_HOMEWORK,
    RECENT_MARKS,
    RECENT_MESSAGES,
    SENSOR_ATTENDANCE_COUNT,
    SENSOR_LAST_UPDATE,
    SENSOR_LATEST_ATTENDANCE_MARK,
    SENSOR_LATEST_BULLETIN,
    SENSOR_LATEST_EXAM_GRADE,
    SENSOR_LATEST_HOMEWORK,
    SENSOR_LATEST_MESSAGE,
    SENSOR_LESSONS_THIS_WEEK,
    SENSOR_LESSONS_TODAY,
    SENSOR_LESSONS_TOMORROW,
    SENSOR_NEXT_EXAM,
    SENSOR_NEXT_LESSON,
    SENSOR_UNREAD_BULLETIN_COUNT,
    SENSOR_UNREAD_COUNT,
    SENSOR_UPCOMING_EXAMS,
)
from .coordinator import (
    StudentData,
    WilmaConfigEntry,
    WilmaCoordinator,
    exam_attributes,
    exam_grade,
    homework_attributes,
    lesson_attributes,
    mark_attributes,
    truncate,
    week_start,
)
from .entity import WilmaAccountEntity, WilmaStudentEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WilmaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Wilma sensors: account-level ones and a set per student."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        WilmaLastUpdateSensor(coordinator, entry, SENSOR_LAST_UPDATE)
    ]
    for student in coordinator.data.students.values():
        entities.extend(
            [
                WilmaLatestMessageSensor(
                    coordinator, entry, student, SENSOR_LATEST_MESSAGE
                ),
                WilmaUnreadCountSensor(
                    coordinator, entry, student, SENSOR_UNREAD_COUNT
                ),
                WilmaLatestAttendanceMarkSensor(
                    coordinator, entry, student, SENSOR_LATEST_ATTENDANCE_MARK
                ),
                WilmaAttendanceCountSensor(
                    coordinator, entry, student, SENSOR_ATTENDANCE_COUNT
                ),
                WilmaLatestBulletinSensor(
                    coordinator, entry, student, SENSOR_LATEST_BULLETIN
                ),
                WilmaNewBulletinCountSensor(
                    coordinator, entry, student, SENSOR_UNREAD_BULLETIN_COUNT
                ),
                WilmaNextLessonSensor(coordinator, entry, student, SENSOR_NEXT_LESSON),
                WilmaLessonsOnDaySensor(
                    coordinator, entry, student, SENSOR_LESSONS_TODAY, days_ahead=0
                ),
                WilmaLessonsOnDaySensor(
                    coordinator, entry, student, SENSOR_LESSONS_TOMORROW, days_ahead=1
                ),
                WilmaLessonsThisWeekSensor(
                    coordinator, entry, student, SENSOR_LESSONS_THIS_WEEK
                ),
                WilmaNextExamSensor(coordinator, entry, student, SENSOR_NEXT_EXAM),
                WilmaUpcomingExamsSensor(
                    coordinator, entry, student, SENSOR_UPCOMING_EXAMS
                ),
                WilmaLatestExamGradeSensor(
                    coordinator, entry, student, SENSOR_LATEST_EXAM_GRADE
                ),
                WilmaLatestHomeworkSensor(
                    coordinator, entry, student, SENSOR_LATEST_HOMEWORK
                ),
            ]
        )
    async_add_entities(entities)


class WilmaLastUpdateSensor(WilmaAccountEntity, SensorEntity):
    """Time of the last successful update."""

    _attr_icon = "mdi:update"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> datetime | None:
        """Return the time of the last successful update."""
        data = self.coordinator.data
        return data.last_update if data else None


class WilmaStudentSensor(WilmaStudentEntity, SensorEntity):
    """Base class for per-student sensors."""

    def _value(self, student: StudentData) -> Any:
        raise NotImplementedError

    def _attributes(self, student: StudentData) -> dict[str, Any] | None:
        return None

    @property
    def native_value(self) -> Any:
        """Return the sensor's value for its student."""
        student = self.student
        return self._value(student) if student else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the sensor's attributes for its student."""
        student = self.student
        return self._attributes(student) if student else None


class WilmaLatestMessageSensor(WilmaStudentSensor):
    """The newest message, with its subject as state."""

    _attr_icon = "mdi:email"

    def _value(self, student: StudentData) -> str | None:
        message = student.latest_message
        return message.get("subject") if message else None

    def _attributes(self, student: StudentData) -> dict[str, Any] | None:
        message = student.latest_message
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
        attrs["recent_messages"] = [
            {
                "id": recent.get("id"),
                "subject": recent.get("subject"),
                "sender": recent.get("sender"),
                "timestamp": recent.get("timestamp"),
                "unread": bool(recent.get("unread")),
            }
            for recent in student.messages[:RECENT_MESSAGES]
        ]
        return attrs


class WilmaUnreadCountSensor(WilmaStudentSensor):
    """Number of unread messages in the inbox, as Wilma reports them."""

    _attr_icon = "mdi:email-alert"
    _attr_native_unit_of_measurement = "messages"

    def _value(self, student: StudentData) -> int:
        return student.unread_count


class WilmaLatestAttendanceMarkSensor(WilmaStudentSensor):
    """The most recent attendance mark (absence, feedback, homework note, etc.)."""

    _attr_icon = "mdi:clipboard-text-clock"

    def _value(self, student: StudentData) -> str | None:
        mark = student.latest_attendance_mark
        return mark.type.description if mark else None

    def _attributes(self, student: StudentData) -> dict[str, Any] | None:
        if not student.attendance:
            return None
        attrs: dict[str, Any] = {}
        if mark := student.latest_attendance_mark:
            attrs.update(mark_attributes(mark))
        attrs["marks_this_school_year"] = len(student.attendance.marks)
        attrs["counts_by_type"] = _counts_by_type(student)
        return attrs


class WilmaAttendanceCountSensor(WilmaStudentSensor):
    """Number of attendance marks this school year, with a breakdown by type."""

    _attr_icon = "mdi:clipboard-list"
    _attr_native_unit_of_measurement = "marks"

    def _value(self, student: StudentData) -> int | None:
        return len(student.attendance.marks) if student.attendance else None

    def _attributes(self, student: StudentData) -> dict[str, Any] | None:
        if not student.attendance:
            return None
        marks = student.attendance.marks
        by_code: Counter[str] = Counter(m.type.code for m in marks)
        by_type_id: Counter[int] = Counter(m.type.id for m in marks)
        mark_types = {mark_type.id: mark_type for mark_type in student.attendance.types}
        for mark in marks:
            mark_types.setdefault(mark.type.id, mark.type)
        types = [
            {
                "type_id": type_id,
                "code": mark_types[type_id].code,
                "description": mark_types[type_id].description,
                "color": mark_types[type_id].color,
                "count": count,
            }
            for type_id, count in by_type_id.most_common()
        ]
        newest = sorted(marks, key=lambda m: (m.date, m.hour or 0), reverse=True)
        recent_marks = [
            {
                "date": mark.date.isoformat(),
                "hour": mark.hour,
                "code": mark.type.code,
                "description": mark.type.description,
                "color": mark.type.color,
                "course": mark.course,
                "comment": truncate(mark.comment, MAX_LIST_TEXT_LENGTH),
                "teacher": mark.teacher,
            }
            for mark in newest[:RECENT_MARKS]
        ]
        return {
            "by_type": _counts_by_type(student),
            "by_code": dict(by_code),
            "types": types,
            "recent_marks": recent_marks,
        }


def _counts_by_type(student: StudentData) -> dict[str, int]:
    marks = student.attendance.marks if student.attendance else []
    return dict(Counter(mark.type.description for mark in marks))


class WilmaLatestBulletinSensor(WilmaStudentSensor):
    """The newest bulletin on the school's bulletin board, with its title as state."""

    _attr_icon = "mdi:bulletin-board"

    def _value(self, student: StudentData) -> str | None:
        bulletin = student.latest_bulletin
        return bulletin.get("title") if bulletin else None

    def _attributes(self, student: StudentData) -> dict[str, Any] | None:
        bulletin = student.latest_bulletin
        if not bulletin:
            return None
        return {
            key: bulletin.get(key)
            for key in (
                "id",
                "title",
                "date",
                "section",
                "author",
                "audience",
                "url",
                "content_html",
                "content_markdown",
            )
        } | {"recent_bulletins": student.recent_bulletins}


class WilmaNewBulletinCountSensor(WilmaStudentSensor):
    """Number of bulletins that appeared within the recent threshold."""

    _attr_icon = "mdi:bulletin-board"
    _attr_native_unit_of_measurement = "bulletins"

    def _value(self, student: StudentData) -> int:
        return student.new_bulletin_count


class WilmaScheduleSensor(WilmaStudentSensor):
    """Base class for schedule sensors, which also re-evaluate as time passes."""

    _unsub_timer: CALLBACK_TYPE | None = None

    async def async_added_to_hass(self) -> None:
        """Re-evaluate at the start of each day, between coordinator updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_change(
                self.hass, self._handle_time, hour=0, minute=0, second=1
            )
        )
        self.async_on_remove(self._cancel_timer)

    @callback
    def _cancel_timer(self) -> None:
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None

    @callback
    def _handle_time(self, now: datetime) -> None:
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


class WilmaNextLessonSensor(WilmaScheduleSensor):
    """The next lesson that has not started yet, with its subject as state."""

    _attr_icon = "mdi:school"

    def _next(self, student: StudentData) -> Lesson | None:
        now = dt_util.now()
        tz = self.coordinator.timezone
        for lesson in student.upcoming_lessons():
            if lesson.starts_at.replace(tzinfo=tz) > now:
                return lesson
        return None

    def _value(self, student: StudentData) -> str | None:
        lesson = self._next(student)
        return lesson.subject if lesson else None

    def _attributes(self, student: StudentData) -> dict[str, Any] | None:
        lesson = self._next(student)
        if not lesson:
            return None
        return {
            "date": lesson.date.isoformat(),
            **lesson_attributes(lesson, self.coordinator.timezone),
        }

    async def async_added_to_hass(self) -> None:
        """Also schedule a re-evaluation for when the next lesson starts."""
        await super().async_added_to_hass()
        self._schedule_next()

    @callback
    def _handle_coordinator_update(self) -> None:
        super()._handle_coordinator_update()
        self._schedule_next()

    @callback
    def _handle_time(self, now: datetime) -> None:
        super()._handle_time(now)
        self._schedule_next()

    @callback
    def _schedule_next(self) -> None:
        self._cancel_timer()
        student = self.student
        lesson = self._next(student) if student else None
        if lesson:
            starts = lesson.starts_at.replace(tzinfo=self.coordinator.timezone)
            self._unsub_timer = async_track_point_in_time(
                self.hass, self._handle_time, starts + timedelta(seconds=1)
            )


class WilmaLessonsOnDaySensor(WilmaScheduleSensor):
    """Number of lessons on a day relative to today, with the lessons as attributes."""

    _attr_native_unit_of_measurement = "lessons"

    def __init__(
        self,
        coordinator: WilmaCoordinator,
        entry: WilmaConfigEntry,
        student: StudentData,
        key: str,
        days_ahead: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, student, key)
        self._days_ahead = days_ahead
        self._attr_icon = (
            "mdi:calendar-today" if days_ahead == 0 else "mdi:calendar-arrow-right"
        )

    def _day(self) -> date:
        return self._today() + timedelta(days=self._days_ahead)

    def _value(self, student: StudentData) -> int | None:
        lessons = student.lessons_on(self._day())
        return len(lessons) if lessons is not None else None

    def _attributes(self, student: StudentData) -> dict[str, Any] | None:
        day = self._day()
        lessons = student.lessons_on(day)
        if lessons is None:
            return None
        return {"date": day.isoformat(), **self._summary(lessons)}


class WilmaLessonsThisWeekSensor(WilmaScheduleSensor):
    """Number of lessons this week, with the lessons as attributes."""

    _attr_icon = "mdi:calendar-week"
    _attr_native_unit_of_measurement = "lessons"

    def _week(self, student: StudentData) -> WeekSchedule | None:
        return student.schedule.get(week_start(self._today()))

    def _value(self, student: StudentData) -> int | None:
        week = self._week(student)
        return len(week.lessons) if week else None

    def _attributes(self, student: StudentData) -> dict[str, Any] | None:
        week = self._week(student)
        if not week:
            return None
        return {
            "week_start": week.week_start.isoformat(),
            "week_end": week.week_end.isoformat(),
            **self._summary(week.lessons),
        }


class WilmaNextExamSensor(WilmaScheduleSensor):
    """The next exam (today or later), with its subject as state."""

    _attr_icon = "mdi:file-document-edit"

    def _next(self, student: StudentData) -> Exam | None:
        upcoming = student.upcoming_exams(self._today())
        return upcoming[0] if upcoming else None

    def _value(self, student: StudentData) -> str | None:
        exam = self._next(student)
        return truncate(exam.subject or exam.course, MAX_STATE_LENGTH) if exam else None

    def _attributes(self, student: StudentData) -> dict[str, Any] | None:
        exam = self._next(student)
        if not exam:
            return None
        attrs = exam_attributes(exam)
        attrs["days_until"] = (exam.date - self._today()).days
        return attrs


class WilmaUpcomingExamsSensor(WilmaScheduleSensor):
    """Number of upcoming exams, with the exams as attributes."""

    _attr_icon = "mdi:calendar-alert"
    _attr_native_unit_of_measurement = "exams"

    def _value(self, student: StudentData) -> int | None:
        upcoming = student.upcoming_exams(self._today())
        return len(upcoming) if upcoming is not None else None

    def _attributes(self, student: StudentData) -> dict[str, Any] | None:
        upcoming = student.upcoming_exams(self._today())
        if upcoming is None:
            return None
        return {"exams": [_exam_summary(exam) for exam in upcoming[:MAX_LISTED_EXAMS]]}


def _exam_summary(exam: Exam) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "date": exam.date.isoformat(),
        "subject": exam.subject or exam.course,
        "course": exam.course,
        "name": exam.name or None,
        "info": truncate(exam.info, MAX_LIST_TEXT_LENGTH),
        "teachers": exam.teacher_names,
    }
    if grade := exam_grade(exam):
        summary["grade"] = truncate(grade, MAX_GRADE_LENGTH)
    return summary


class WilmaLatestExamGradeSensor(WilmaStudentSensor):
    """The grade of the most recent graded exam."""

    _attr_icon = "mdi:school-outline"

    def _latest(self, student: StudentData) -> Exam | None:
        graded = student.graded_exams()
        return graded[0] if graded else None

    def _value(self, student: StudentData) -> str | None:
        exam = self._latest(student)
        return truncate(exam_grade(exam), MAX_STATE_LENGTH) if exam else None

    def _attributes(self, student: StudentData) -> dict[str, Any] | None:
        graded = student.graded_exams()
        if graded is None:
            return None
        attrs: dict[str, Any] = {}
        if graded:
            attrs.update(exam_attributes(graded[0]))
            attrs["seen"] = graded[0].seen.isoformat() if graded[0].seen else None
        attrs["graded_exams"] = [
            {
                "date": exam.date.isoformat(),
                "subject": exam.subject or exam.course,
                "course": exam.course,
                "grade": truncate(exam.grade, MAX_GRADE_LENGTH),
                "verbal_grade": truncate(exam.verbal_grade, MAX_LIST_TEXT_LENGTH),
            }
            for exam in graded[:RECENT_GRADES]
        ]
        return attrs


class WilmaLatestHomeworkSensor(WilmaStudentSensor):
    """The newest homework entered in any course's lesson diary."""

    _attr_icon = "mdi:book-open-variant"

    def _latest(self, student: StudentData) -> Homework | None:
        homework = student.homework
        return homework[0] if homework else None

    def _value(self, student: StudentData) -> str | None:
        homework = self._latest(student)
        return truncate(homework.text, MAX_STATE_LENGTH) if homework else None

    def _attributes(self, student: StudentData) -> dict[str, Any] | None:
        homework = student.homework
        if homework is None:
            return None
        attrs: dict[str, Any] = {}
        if homework:
            attrs.update(homework_attributes(homework[0]))
        attrs["recent_homework"] = [
            homework_attributes(entry, MAX_LIST_TEXT_LENGTH)
            for entry in homework[:RECENT_HOMEWORK]
        ]
        return attrs
