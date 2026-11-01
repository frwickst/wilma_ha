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
    Lesson,
    Message,
    WeekSchedule,
    WilmaClient,
    WilmaError,
)

from .const import (
    CONF_PASSWORD,
    CONF_SERVER_URL,
    CONF_USERNAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_NEW_ATTENDANCE_MARK,
    EVENT_NEW_MESSAGE,
    INITIAL_MESSAGE_LOOKBACK,
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


@dataclass
class WilmaData:
    """Data provided by the coordinator."""

    messages: list[dict[str, Any]]
    """Stored messages, newest first."""
    attendance: AttendanceReport | None
    last_update: datetime
    schedule: dict[date, WeekSchedule] = field(default_factory=dict)
    """The current and next week, keyed by their Monday."""

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


def week_start(day: date) -> date:
    """The Monday of the week containing ``day``."""
    return day - timedelta(days=day.weekday())


def lesson_attributes(lesson: Lesson, tz: ZoneInfo) -> dict[str, Any]:
    """Flat, JSON-serialisable description of a lesson."""
    return {
        "start": lesson.starts_at.replace(tzinfo=tz).isoformat(),
        "end": lesson.ends_at.replace(tzinfo=tz).isoformat(),
        "subject": lesson.subject,
        "teachers": lesson.teachers,
        "rooms": lesson.rooms,
    }


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


def _message_to_dict(message: Message) -> dict[str, Any]:
    data = message.to_dict()
    data["content_markdown"] = (
        message.content_markdown if message.content_html else None
    )
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


class WilmaCoordinator(DataUpdateCoordinator[WilmaData]):
    """Coordinator for fetching data from Wilma."""

    config_entry: WilmaConfigEntry

    def __init__(self, hass: HomeAssistant, entry: WilmaConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.server_url: str = entry.data[CONF_SERVER_URL]
        self.username: str = entry.data[CONF_USERNAME]
        self.password: str = entry.data[CONF_PASSWORD]
        self.client: WilmaClient | None = None
        self.store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}"
        )
        self._messages: list[dict[str, Any]] = []
        # None until the first successful update: that update records what already exists
        # without announcing it as new.
        self._seen_message_ids: set[int] | None = None
        self._seen_mark_keys: set[str] | None = None
        self._attendance: AttendanceReport | None = None
        self._schedule: dict[date, WeekSchedule] = {}
        # Weeks fetched on demand by the calendar, with the time they were fetched
        self._week_cache: dict[date, tuple[WeekSchedule, datetime]] = {}
        # Serialises use of the client, so concurrent callers don't log in twice and end
        # each other's session.
        self._client_lock = asyncio.Lock()
        self.timezone = ZoneInfo("Europe/Helsinki")

    async def _async_setup(self) -> None:
        """Load persisted state."""
        stored = await self.store.async_load() or {}
        self._messages = _merge_messages([], stored.get("messages") or [])
        if stored.get("seen_message_ids") is not None:
            self._seen_message_ids = set(stored["seen_message_ids"])
        if stored.get("seen_attendance_keys") is not None:
            self._seen_mark_keys = set(stored["seen_attendance_keys"])

    async def _async_update_data(self) -> WilmaData:
        """Fetch data from Wilma."""
        try:
            async with self._client_lock:
                client = await self._ensure_client()
                await self._update_messages(client)
                await self._update_attendance(client)
                await self._update_schedule(client)
        except AuthenticationError as err:
            await self.async_close_client()
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except WilmaError as err:
            raise UpdateFailed(f"Error communicating with Wilma: {err}") from err

        await self._async_save()
        return WilmaData(
            messages=list(self._messages),
            attendance=self._attendance,
            last_update=dt_util.utcnow(),
            schedule=dict(self._schedule),
        )

    async def _ensure_client(self) -> WilmaClient:
        if self.client is None:
            client = WilmaClient(self.server_url)
            try:
                await client.login(self.username, self.password)
            except BaseException:
                await client.close()
                raise
            self.client = client
            self.timezone = client.timezone
        return self.client

    async def _update_messages(self, client: WilmaClient) -> None:
        listed = await client.get_messages()
        known = set(self._seen_message_ids or ()) | {m["id"] for m in self._messages}
        unseen = [message for message in listed if message.id not in known]

        first_run = self._seen_message_ids is None
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
            await client.fetch_content(to_fetch)

        new_messages = [_message_to_dict(message) for message in unseen]
        self._messages = _merge_messages(new_messages, self._messages)

        if listed:
            self._seen_message_ids = {message.id for message in listed}
        elif self._seen_message_ids is None:
            self._seen_message_ids = set()

        if not first_run:
            for message in reversed(new_messages):
                self.hass.bus.async_fire(
                    EVENT_NEW_MESSAGE,
                    {
                        "entry_id": self.config_entry.entry_id,
                        "id": message["id"],
                        "subject": message.get("subject"),
                        "sender": message.get("sender"),
                        "timestamp": message.get("timestamp"),
                        "content_markdown": message.get("content_markdown"),
                    },
                )

    async def _update_attendance(self, client: WilmaClient) -> None:
        try:
            report = await client.get_attendance(AttendanceRange.SCHOOL_YEAR)
        except AuthenticationError:
            raise
        except WilmaError as err:
            # Attendance comes from an HTML page; don't let it break message updates
            _LOGGER.warning("Could not fetch attendance marks: %s", err)
            return

        keys = {mark.key for mark in report.marks}
        if self._seen_mark_keys is None:
            self._seen_mark_keys = keys
        else:
            new_marks = [
                mark for mark in report.marks if mark.key not in self._seen_mark_keys
            ]
            for mark in sorted(new_marks, key=lambda m: (m.date, m.hour or 0)):
                self.hass.bus.async_fire(
                    EVENT_NEW_ATTENDANCE_MARK,
                    {"entry_id": self.config_entry.entry_id, **mark_attributes(mark)},
                )
            cutoff = (dt_util.now().date() - SEEN_MARK_RETENTION).isoformat()
            self._seen_mark_keys = {
                key for key in self._seen_mark_keys | keys if key[:10] >= cutoff
            }

        self._attendance = report

    async def _update_schedule(self, client: WilmaClient) -> None:
        this_week = week_start(client.today())
        weeks: dict[date, WeekSchedule] = {}
        for monday in (this_week, this_week + timedelta(days=7)):
            try:
                weeks[monday] = await client.get_schedule(monday)
            except AuthenticationError:
                raise
            except WilmaError as err:
                _LOGGER.warning(
                    "Could not fetch the schedule for week of %s: %s", monday, err
                )
                if monday in self._schedule:
                    weeks[monday] = self._schedule[monday]
        self._schedule = weeks

    async def async_get_weeks(self, start: date, end: date) -> list[WeekSchedule]:
        """Schedules of the weeks overlapping ``start``..``end``, fetching missing ones.

        At most MAX_CACHED_WEEKS weeks are returned, starting from ``start``.
        """
        mondays: list[date] = []
        monday = week_start(start)
        while monday <= end and len(mondays) < MAX_CACHED_WEEKS:
            mondays.append(monday)
            monday += timedelta(days=7)

        now = dt_util.utcnow()
        weeks = []
        for monday in mondays:
            if monday in self._schedule:
                weeks.append(self._schedule[monday])
                continue
            cached = self._week_cache.get(monday)
            if cached and now - cached[1] < WEEK_CACHE_TTL:
                weeks.append(cached[0])
                continue
            async with self._client_lock:
                client = await self._ensure_client()
                week = await client.get_schedule(monday)
            self._week_cache[monday] = (week, now)
            weeks.append(week)

        # Keep the cache bounded, dropping the oldest fetches first
        for monday, _ in sorted(self._week_cache.items(), key=lambda item: item[1][1])[
            : max(0, len(self._week_cache) - MAX_CACHED_WEEKS)
        ]:
            del self._week_cache[monday]
        return weeks

    async def _async_save(self) -> None:
        data: dict[str, Any] = {"messages": self._messages}
        if self._seen_message_ids is not None:
            data["seen_message_ids"] = sorted(self._seen_message_ids)
        if self._seen_mark_keys is not None:
            data["seen_attendance_keys"] = sorted(self._seen_mark_keys)
        await self.store.async_save(data)

    async def async_close_client(self) -> None:
        """Close the Wilma client."""
        if self.client:
            try:
                await self.client.close()
            finally:
                self.client = None
