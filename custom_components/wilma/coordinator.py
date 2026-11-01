"""DataUpdateCoordinator for the Wilma integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from wilhelmina import (
    AttendanceMark,
    AttendanceRange,
    AttendanceReport,
    AuthenticationError,
    Bulletin,
    BulletinSection,
    Lesson,
    Message,
    Role,
    WeekSchedule,
    WilmaClient,
    WilmaError,
)

from .const import (
    ATTR_STUDENT_ID,
    ATTR_STUDENT_NAME,
    CONF_PASSWORD,
    CONF_RECENT_THRESHOLD_HOURS,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_SERVER_URL,
    CONF_USERNAME,
    DEFAULT_RECENT_THRESHOLD_HOURS,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    EVENT_NEW_ATTENDANCE_MARK,
    EVENT_NEW_BULLETIN,
    EVENT_NEW_MESSAGE,
    INITIAL_MESSAGE_LOOKBACK,
    MAX_BULLETIN_FETCHES_PER_UPDATE,
    MAX_CACHED_BULLETINS,
    MAX_CACHED_WEEKS,
    MAX_CONTENT_FETCHES_PER_UPDATE,
    MAX_STORED_MESSAGES,
    SEEN_MARK_RETENTION,
    STORAGE_KEY,
    STORAGE_VERSION,
    WEEK_CACHE_TTL,
)

_LOGGER = logging.getLogger(__name__)

type WilmaConfigEntry = ConfigEntry[WilmaCoordinator]


def week_start(day: date) -> date:
    """The Monday of the week containing ``day``."""
    return day - timedelta(days=day.weekday())


def mark_attributes(mark: AttendanceMark) -> dict[str, Any]:
    """Flat, JSON-serialisable description of an attendance mark."""
    return {
        "key": mark.key,
        "date": mark.date.isoformat(),
        "hour": mark.hour,
        "type_id": mark.type.id,
        "code": mark.type.code,
        "description": mark.type.description,
        "color": mark.type.color,
        "name": mark.name,
        "course": mark.course,
        "comment": mark.comment,
        "teacher": mark.teacher,
        "teacher_code": mark.teacher_code,
        "clarification": mark.clarification,
        "title": mark.title,
    }


def lesson_attributes(lesson: Lesson, tz: ZoneInfo) -> dict[str, Any]:
    """Flat, JSON-serialisable description of a lesson."""
    return {
        "start": lesson.starts_at.replace(tzinfo=tz).isoformat(),
        "end": lesson.ends_at.replace(tzinfo=tz).isoformat(),
        "subject": lesson.subject,
        "teachers": lesson.teachers,
        "rooms": lesson.rooms,
    }


@dataclass
class StudentData:
    """Data of one student, as provided to entities."""

    user_id: str
    name: str
    primus_id: int
    messages: list[dict[str, Any]] = field(default_factory=list)
    """Stored messages, newest first."""
    unread_count: int = 0
    attendance: AttendanceReport | None = None
    schedule: dict[date, WeekSchedule] = field(default_factory=dict)
    """The current and next week, keyed by their Monday."""
    latest_bulletin: dict[str, Any] | None = None
    new_bulletin_count: int = 0
    """Bulletins that appeared within the recent threshold."""
    latest_new_mark_seen: datetime | None = None
    """When the most recent previously unseen attendance mark was detected."""

    @property
    def first_name(self) -> str:
        """The student's first name, for naming the device."""
        return self.name.split()[0] if self.name.strip() else self.user_id

    @property
    def latest_message(self) -> dict[str, Any] | None:
        """The newest stored message."""
        return self.messages[0] if self.messages else None

    @property
    def latest_attendance_mark(self) -> AttendanceMark | None:
        """The attendance mark on the latest date and hour."""
        return self.attendance.latest if self.attendance else None

    def lessons_on(self, day: date) -> list[Lesson] | None:
        """Lessons on ``day``, or None if that week has not been fetched."""
        week = self.schedule.get(week_start(day))
        return week.lessons_on(day) if week else None

    def upcoming_lessons(self) -> list[Lesson]:
        """Lessons of the fetched weeks, in order."""
        return sorted(
            (lesson for week in self.schedule.values() for lesson in week.lessons),
            key=lambda lesson: lesson.starts_at,
        )


@dataclass
class WilmaData:
    """Data provided by the coordinator."""

    students: dict[str, StudentData]
    """Students by user ID."""
    last_update: datetime


def _message_to_dict(message: Message, student: Role) -> dict[str, Any]:
    data = message.to_dict()
    data["content_markdown"] = (
        message.content_markdown if message.content_html else None
    )
    data[ATTR_STUDENT_ID] = student.user_id
    data[ATTR_STUDENT_NAME] = student.name
    return data


def _message_time(message: Message) -> datetime | None:
    try:
        return message.format_timestamp()
    except (TypeError, ValueError):
        return None


def _merge_messages(
    new: list[dict[str, Any]], stored: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Merge messages by ID, newest first, keeping at most MAX_STORED_MESSAGES."""
    by_id: dict[Any, dict[str, Any]] = {}
    for message in [*new, *stored]:
        if isinstance(message, dict) and "id" in message:
            by_id.setdefault(message["id"], message)
    merged = sorted(
        by_id.values(), key=lambda m: str(m.get("timestamp") or ""), reverse=True
    )
    return merged[:MAX_STORED_MESSAGES]


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    return dt_util.parse_datetime(value)


@dataclass
class _StudentState:
    """Mutable per-student state; the persisted part survives restarts."""

    messages: list[dict[str, Any]] = field(default_factory=list)
    # None until the first successful update of that kind: that update records what
    # already exists without announcing it as new.
    seen_message_ids: set[int] | None = None
    seen_mark_keys: set[str] | None = None
    seen_bulletin_ids: set[int] | None = None
    # When previously unseen marks and bulletins were detected
    mark_first_seen: dict[str, datetime] = field(default_factory=dict)
    bulletin_first_seen: dict[int, datetime] = field(default_factory=dict)
    bulletin_cache: dict[int, dict[str, Any]] = field(default_factory=dict)
    # Not persisted
    unread_count: int = 0
    attendance: AttendanceReport | None = None
    schedule: dict[date, WeekSchedule] = field(default_factory=dict)
    latest_bulletin_id: int | None = None
    week_cache: dict[date, tuple[WeekSchedule, datetime]] = field(default_factory=dict)

    @classmethod
    def from_store(cls, data: dict[str, Any]) -> _StudentState:
        state = cls(messages=_merge_messages([], data.get("messages") or []))
        if data.get("seen_message_ids") is not None:
            state.seen_message_ids = set(data["seen_message_ids"])
        if data.get("seen_attendance_keys") is not None:
            state.seen_mark_keys = set(data["seen_attendance_keys"])
        if data.get("seen_bulletin_ids") is not None:
            state.seen_bulletin_ids = set(data["seen_bulletin_ids"])
        for key, value in (data.get("mark_first_seen") or {}).items():
            if (seen := _parse_time(value)) is not None:
                state.mark_first_seen[key] = seen
        for key, value in (data.get("bulletin_first_seen") or {}).items():
            if (seen := _parse_time(value)) is not None:
                state.bulletin_first_seen[int(key)] = seen
        for key, value in (data.get("bulletin_cache") or {}).items():
            if isinstance(value, dict):
                state.bulletin_cache[int(key)] = value
        return state

    def to_store(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "messages": self.messages,
            "mark_first_seen": {
                k: v.isoformat() for k, v in self.mark_first_seen.items()
            },
            "bulletin_first_seen": {
                str(k): v.isoformat() for k, v in self.bulletin_first_seen.items()
            },
            "bulletin_cache": {str(k): v for k, v in self.bulletin_cache.items()},
        }
        if self.seen_message_ids is not None:
            data["seen_message_ids"] = sorted(self.seen_message_ids)
        if self.seen_mark_keys is not None:
            data["seen_attendance_keys"] = sorted(self.seen_mark_keys)
        if self.seen_bulletin_ids is not None:
            data["seen_bulletin_ids"] = sorted(self.seen_bulletin_ids)
        return data


class WilmaCoordinator(DataUpdateCoordinator[WilmaData]):
    """Coordinator for fetching data of all students of an account from Wilma."""

    config_entry: WilmaConfigEntry

    def __init__(self, hass: HomeAssistant, entry: WilmaConfigEntry) -> None:
        """Initialize the coordinator."""
        minutes = entry.options.get(
            CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=minutes),
        )
        self.server_url: str = entry.data[CONF_SERVER_URL]
        self.username: str = entry.data[CONF_USERNAME]
        self.password: str = entry.data[CONF_PASSWORD]
        self.client: WilmaClient | None = None
        self.store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}"
        )
        self.students: list[Role] = []
        self.primary_user_id: str | None = None
        self.partial_errors: list[str] = []
        self.timezone = ZoneInfo("Europe/Helsinki")
        self._states: dict[str, _StudentState] = {}
        # State stored before multi-student support, for the account's primary student
        self._legacy_state: dict[str, Any] | None = None
        # Serialises use of the client, so concurrent callers don't log in twice and end
        # each other's session.
        self._client_lock = asyncio.Lock()

    @property
    def recent_threshold(self) -> timedelta:
        """How long new items count as recent."""
        hours = self.config_entry.options.get(
            CONF_RECENT_THRESHOLD_HOURS, DEFAULT_RECENT_THRESHOLD_HOURS
        )
        return timedelta(hours=hours)

    @property
    def primary_student(self) -> Role | None:
        """The student the account logs in to, or else the first one."""
        for student in self.students:
            if student.user_id == self.primary_user_id:
                return student
        return self.students[0] if self.students else None

    async def _async_setup(self) -> None:
        """Load persisted state."""
        stored = await self.store.async_load() or {}
        if isinstance(stored.get("students"), dict):
            self._states = {
                user_id: _StudentState.from_store(data)
                for user_id, data in stored["students"].items()
                if isinstance(data, dict)
            }
        elif stored:
            self._legacy_state = stored

    async def _async_update_data(self) -> WilmaData:
        """Fetch data for all students from Wilma."""
        self.partial_errors = []
        try:
            async with self._client_lock:
                client = await self._ensure_client()
                for student in self.students:
                    state = self._state_for(student)
                    await self._update_messages(client, student, state)
                    await self._update_attendance(client, student, state)
                    await self._update_schedule(client, student, state)
                    await self._update_bulletins(client, student, state)
        except AuthenticationError as err:
            await self.async_close_client()
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except WilmaError as err:
            raise UpdateFailed(f"Error communicating with Wilma: {err}") from err

        await self._async_save()
        return WilmaData(
            students={
                student.user_id or "": self._student_data(student)
                for student in self.students
            },
            last_update=dt_util.utcnow(),
        )

    async def _ensure_client(self) -> WilmaClient:
        if self.client is None:
            client = WilmaClient(self.server_url)
            try:
                await client.login(self.username, self.password)
                students = await self._discover_students(client)
            except BaseException:
                await client.close()
                raise
            self.client = client
            self.timezone = client.timezone
            self.primary_user_id = client.user_id
            self.students = students
        return self.client

    async def _discover_students(self, client: WilmaClient) -> list[Role]:
        try:
            students = await client.get_students()
        except AuthenticationError:
            raise
        except WilmaError as err:
            _LOGGER.warning("Could not list the account's students: %s", err)
            students = []
        if not students and client.user_id:
            # Fall back to the user ID the login landed on
            students = [
                Role(
                    name=self.username,
                    type="student",
                    primus_id=0,
                    slug=f"/{client.user_id}",
                )
            ]
        return students

    def _state_for(self, student: Role) -> _StudentState:
        user_id = student.user_id or ""
        if user_id not in self._states:
            if self._legacy_state is not None and user_id == self.primary_user_id:
                self._states[user_id] = _StudentState.from_store(self._legacy_state)
                self._legacy_state = None
            else:
                self._states[user_id] = _StudentState()
        return self._states[user_id]

    def _student_data(self, student: Role) -> StudentData:
        state = self._state_for(student)
        now = dt_util.utcnow()
        threshold = self.recent_threshold
        new_bulletins = sum(
            1 for seen in state.bulletin_first_seen.values() if now - seen <= threshold
        )
        latest_bulletin = (
            state.bulletin_cache.get(state.latest_bulletin_id)
            if state.latest_bulletin_id is not None
            else None
        )
        return StudentData(
            user_id=student.user_id or "",
            name=student.name,
            primus_id=student.primus_id,
            messages=list(state.messages),
            unread_count=state.unread_count,
            attendance=state.attendance,
            schedule=dict(state.schedule),
            latest_bulletin=latest_bulletin,
            new_bulletin_count=new_bulletins,
            latest_new_mark_seen=max(state.mark_first_seen.values(), default=None),
        )

    def _event_base(self, student: Role) -> dict[str, Any]:
        return {
            "entry_id": self.config_entry.entry_id,
            ATTR_STUDENT_ID: student.user_id,
            ATTR_STUDENT_NAME: student.name,
        }

    def _partial_failure(self, what: str, student: Role, err: WilmaError) -> None:
        message = f"{what} for {student.name}: {err}"
        _LOGGER.warning("Could not fetch %s", message)
        self.partial_errors.append(message)

    async def _update_messages(
        self, client: WilmaClient, student: Role, state: _StudentState
    ) -> None:
        listed = await client.get_messages(user_id=student.user_id)
        state.unread_count = sum(1 for message in listed if message.unread)
        known = set(state.seen_message_ids or ()) | {m["id"] for m in state.messages}
        unseen = [message for message in listed if message.id not in known]

        first_run = state.seen_message_ids is None
        if first_run:
            cutoff = (
                datetime.now(client.timezone).replace(tzinfo=None)
                - INITIAL_MESSAGE_LOOKBACK
            )
            unseen = [
                m for m in unseen if (t := _message_time(m)) is not None and t > cutoff
            ]

        # The listing is newest first; fetching content marks messages as read in Wilma
        to_fetch = unseen[:MAX_CONTENT_FETCHES_PER_UPDATE]
        if to_fetch:
            await client.fetch_content(to_fetch, user_id=student.user_id)

        new_messages = [_message_to_dict(message, student) for message in unseen]
        state.messages = _merge_messages(new_messages, state.messages)

        if listed:
            state.seen_message_ids = {message.id for message in listed}
        elif state.seen_message_ids is None:
            state.seen_message_ids = set()

        if not first_run:
            for message in reversed(new_messages):
                self.hass.bus.async_fire(
                    EVENT_NEW_MESSAGE,
                    {
                        **self._event_base(student),
                        "id": message["id"],
                        "subject": message.get("subject"),
                        "sender": message.get("sender"),
                        "timestamp": message.get("timestamp"),
                        "unread": message.get("unread"),
                        "content_html": message.get("content_html"),
                        "content_markdown": message.get("content_markdown"),
                    },
                )

    async def _update_attendance(
        self, client: WilmaClient, student: Role, state: _StudentState
    ) -> None:
        try:
            report = await client.get_attendance(
                AttendanceRange.SCHOOL_YEAR, user_id=student.user_id
            )
        except AuthenticationError:
            raise
        except WilmaError as err:
            # Attendance comes from an HTML page; don't let it break message updates
            self._partial_failure("attendance marks", student, err)
            return

        keys = {mark.key for mark in report.marks}
        if state.seen_mark_keys is None:
            state.seen_mark_keys = keys
        else:
            now = dt_util.utcnow()
            new_marks = [
                mark for mark in report.marks if mark.key not in state.seen_mark_keys
            ]
            for mark in sorted(new_marks, key=lambda m: (m.date, m.hour or 0)):
                state.mark_first_seen[mark.key] = now
                self.hass.bus.async_fire(
                    EVENT_NEW_ATTENDANCE_MARK,
                    {**self._event_base(student), **mark_attributes(mark)},
                )
            cutoff = (dt_util.now().date() - SEEN_MARK_RETENTION).isoformat()
            state.seen_mark_keys = {
                key for key in state.seen_mark_keys | keys if key[:10] >= cutoff
            }
            state.mark_first_seen = {
                key: seen
                for key, seen in state.mark_first_seen.items()
                if key in state.seen_mark_keys
            }

        state.attendance = report

    async def _update_schedule(
        self, client: WilmaClient, student: Role, state: _StudentState
    ) -> None:
        this_week = week_start(client.today())
        weeks: dict[date, WeekSchedule] = {}
        for monday in (this_week, this_week + timedelta(days=7)):
            try:
                weeks[monday] = await client.get_schedule(
                    monday, user_id=student.user_id
                )
            except AuthenticationError:
                raise
            except WilmaError as err:
                self._partial_failure(
                    f"the schedule for week of {monday}", student, err
                )
                if monday in state.schedule:
                    weeks[monday] = state.schedule[monday]
        state.schedule = weeks

    async def _update_bulletins(
        self, client: WilmaClient, student: Role, state: _StudentState
    ) -> None:
        try:
            bulletins = await client.get_bulletins(user_id=student.user_id)
        except AuthenticationError:
            raise
        except WilmaError as err:
            self._partial_failure("bulletins", student, err)
            return

        listed_ids = {bulletin.id for bulletin in bulletins}
        first_run = state.seen_bulletin_ids is None
        seen = state.seen_bulletin_ids or set()
        new = [] if first_run else [b for b in bulletins if b.id not in seen]

        current = [b for b in bulletins if b.section is BulletinSection.CURRENT]
        latest = current[0] if current else None

        to_fetch = new[:MAX_BULLETIN_FETCHES_PER_UPDATE]
        if latest and latest.id not in state.bulletin_cache and latest not in to_fetch:
            to_fetch.append(latest)
        for bulletin in to_fetch:
            await self._cache_bulletin(client, student, state, bulletin)

        now = dt_util.utcnow()
        for bulletin in reversed(new):
            state.bulletin_first_seen[bulletin.id] = now
            data = state.bulletin_cache.get(bulletin.id) or self._bulletin_dict(
                student, bulletin
            )
            self.hass.bus.async_fire(
                EVENT_NEW_BULLETIN,
                {
                    **self._event_base(student),
                    "id": bulletin.id,
                    "title": data.get("title"),
                    "date": data.get("date"),
                    "section": data.get("section"),
                    "author": data.get("author"),
                    "url": data.get("url"),
                    "content_html": data.get("content_html"),
                    "content_markdown": data.get("content_markdown"),
                },
            )

        if bulletins:
            state.seen_bulletin_ids = listed_ids
        elif state.seen_bulletin_ids is None:
            state.seen_bulletin_ids = set()
        state.bulletin_first_seen = {
            key: seen
            for key, seen in state.bulletin_first_seen.items()
            if key in state.seen_bulletin_ids
        }
        state.latest_bulletin_id = latest.id if latest else None
        keep = {state.latest_bulletin_id} | set(state.bulletin_first_seen)
        for key in sorted(state.bulletin_cache, reverse=True):
            if key not in keep and len(state.bulletin_cache) > MAX_CACHED_BULLETINS:
                del state.bulletin_cache[key]

    def _bulletin_dict(self, student: Role, bulletin: Bulletin) -> dict[str, Any]:
        return {
            "id": bulletin.id,
            "title": bulletin.title,
            "date": bulletin.date.isoformat() if bulletin.date else None,
            "section": bulletin.section.value if bulletin.section else None,
            "author": bulletin.author,
            "audience": bulletin.audience,
            "url": f"{self.server_url}/{student.user_id}/news/{bulletin.id}",
            "content_html": bulletin.content_html,
            "content_markdown": bulletin.content_markdown
            if bulletin.content_html
            else None,
        }

    async def _cache_bulletin(
        self, client: WilmaClient, student: Role, state: _StudentState, listed: Bulletin
    ) -> None:
        try:
            full = await client.get_bulletin(listed.id, user_id=student.user_id)
        except AuthenticationError:
            raise
        except WilmaError as err:
            self._partial_failure(f"bulletin {listed.id}", student, err)
            full = listed
        else:
            full.section = listed.section
            full.date = full.date or listed.date
            full.title = full.title or listed.title
            full.author = listed.author or full.author
        state.bulletin_cache[listed.id] = self._bulletin_dict(student, full)

    async def async_get_weeks(
        self, user_id: str, start: date, end: date
    ) -> list[WeekSchedule]:
        """A student's schedules of the weeks overlapping ``start``..``end``.

        Weeks other than the current and next one are fetched on demand and cached. At most
        MAX_CACHED_WEEKS weeks are returned, starting from ``start``.
        """
        state = self._states.get(user_id)
        if state is None:
            return []

        mondays: list[date] = []
        monday = week_start(start)
        while monday <= end and len(mondays) < MAX_CACHED_WEEKS:
            mondays.append(monday)
            monday += timedelta(days=7)

        now = dt_util.utcnow()
        weeks = []
        for monday in mondays:
            if monday in state.schedule:
                weeks.append(state.schedule[monday])
                continue
            cached = state.week_cache.get(monday)
            if cached and now - cached[1] < WEEK_CACHE_TTL:
                weeks.append(cached[0])
                continue
            async with self._client_lock:
                client = await self._ensure_client()
                week = await client.get_schedule(monday, user_id=user_id)
            state.week_cache[monday] = (week, now)
            weeks.append(week)

        # Keep the cache bounded, dropping the oldest fetches first
        for monday, _ in sorted(state.week_cache.items(), key=lambda item: item[1][1])[
            : max(0, len(state.week_cache) - MAX_CACHED_WEEKS)
        ]:
            del state.week_cache[monday]
        return weeks

    async def _async_save(self) -> None:
        data: dict[str, Any] = {
            "students": {
                user_id: state.to_store() for user_id, state in self._states.items()
            }
        }
        await self.store.async_save(data)

    async def async_close_client(self) -> None:
        """Close the Wilma client."""
        if self.client:
            try:
                await self.client.close()
            finally:
                self.client = None
