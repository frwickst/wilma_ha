"""Fixtures for Wilma integration tests."""

from __future__ import annotations

import datetime
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from wilhelmina import (
    AttendanceMark,
    AttendanceReport,
    Bulletin,
    BulletinSection,
    Lesson,
    MarkType,
    Message,
    Role,
    ScheduleGroup,
    ScheduleRoom,
    ScheduleTeacher,
    WeekSchedule,
)

from custom_components.wilma.const import (
    CONF_PASSWORD,
    CONF_SERVER_URL,
    CONF_USERNAME,
    DOMAIN,
)

HELSINKI = ZoneInfo("Europe/Helsinki")

POSITIVE = MarkType(
    id=146, code="+", description="Övrig positiv feedback", color="#9191FF"
)
HOMEWORK = MarkType(
    id=135,
    code="Ogjorda uppgifter",
    description="Ogjorda läxor och uppgifter",
    color="#0080FF",
)
BEHAVIOUR = MarkType(
    id=131,
    code="Beteende",
    description="Störande eller dåligt beteende",
    color="#D4D4D4",
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading the custom integration in all tests."""


def wilma_time(days_ago: float) -> str:
    """A Wilma-style timestamp (naive Helsinki time) ``days_ago`` days in the past."""
    moment = datetime.datetime.now(HELSINKI) - datetime.timedelta(days=days_ago)
    return moment.strftime("%Y-%m-%d %H:%M")


def make_message(
    message_id: int, subject: str, days_ago: float, unread: bool = True
) -> Message:
    """A message as returned by the list endpoint."""
    data = {
        "Id": message_id,
        "Subject": subject,
        "TimeStamp": wilma_time(days_ago),
        "Folder": "inbox",
        "SenderId": 1,
        "SenderType": 1,
        "Sender": f"Teacher {message_id}",
    }
    if unread:
        data["Status"] = 1
    return Message.from_dict(data)


def make_mark(
    mark_type: MarkType, days_ago: int, hour: int, comment: str | None = None
) -> AttendanceMark:
    """An attendance mark with its key assigned the way the parser does."""
    mark = AttendanceMark(
        date=datetime.date.today() - datetime.timedelta(days=days_ago),
        type=mark_type,
        title=f"ma05; {mark_type.description} /Anna Teacher",
        name=mark_type.description,
        hour=hour,
        course="ma05",
        comment=comment,
        teacher="Anna Teacher",
        teacher_code="atea",
    )
    mark.key = mark.identity()
    return mark


def make_report(*marks: AttendanceMark) -> AttendanceReport:
    """An attendance report containing ``marks``."""
    return AttendanceReport(marks=list(marks), types=[POSITIVE, HOMEWORK, BEHAVIOUR])


def make_week(monday: datetime.date, weekdays: int = 5) -> WeekSchedule:
    """A week with two lessons on each of the first ``weekdays`` days."""
    lessons = []
    for offset in range(weekdays):
        day = monday + datetime.timedelta(days=offset)
        for start, end, subject in (
            (datetime.time(8, 15), datetime.time(9, 0), "Matematik"),
            (datetime.time(9, 15), datetime.time(10, 0), "Svenska"),
        ):
            lessons.append(
                Lesson(
                    date=day,
                    start=start,
                    end=end,
                    class_name="3B",
                    groups=[
                        ScheduleGroup(
                            id=1,
                            caption=subject,
                            teachers=[
                                ScheduleTeacher(id=1, long_caption="Anna Teacher")
                            ],
                            rooms=[ScheduleRoom(id=1, caption="419")],
                        )
                    ],
                )
            )
    return WeekSchedule(week_start=monday, lessons=lessons)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Wilma (testuser)",
        data={
            CONF_SERVER_URL: "https://test.inschool.fi",
            CONF_USERNAME: "testuser",
            CONF_PASSWORD: "testpass",
        },
        unique_id="https://test.inschool.fi|testuser",
        entry_id="test",
    )


STUDENT = Role(name="Anna Student", type="guardian", primus_id=345, slug="/!12345")
SECOND_STUDENT = Role(name="Bo Student", type="guardian", primus_id=678, slug="/!67890")


def make_bulletins(*ids: int) -> list[Bulletin]:
    """Current bulletins, newest (highest ID) first, dated a day apart."""
    today = datetime.date.today()
    return [
        Bulletin(
            id=news_id,
            title=f"Bulletin {news_id}",
            section=BulletinSection.CURRENT,
            date=today - datetime.timedelta(days=index),
            author="Principal",
        )
        for index, news_id in enumerate(sorted(ids, reverse=True))
    ]


def _messages(**kwargs: object) -> list[Message]:
    return [
        make_message(2, "Recent message", days_ago=1),
        make_message(1, "Old message", days_ago=30, unread=False),
    ]


def _report(*args: object, **kwargs: object) -> AttendanceReport:
    return make_report(
        make_mark(POSITIVE, days_ago=2, hour=9, comment="Great work"),
        make_mark(HOMEWORK, days_ago=5, hour=10),
    )


async def _fetch_content(
    messages: list[Message], *args: object, **kwargs: object
) -> None:
    for message in messages:
        message.content_html = f"<p>Content {message.id}</p>"


async def _get_bulletin(news_id: int, user_id: str | None = None) -> Bulletin:
    return Bulletin(
        id=news_id,
        title=f"Bulletin {news_id}",
        author="atea (Anna Teacher)",
        audience="Guardians",
        content_html=f"<p>Body {news_id}</p>",
    )


def build_client(students: list[Role]) -> MagicMock:
    """A Wilma client mock serving the same data for every student."""
    client = MagicMock()
    client.timezone = HELSINKI
    client.user_id = students[0].user_id if students else None
    client.today = lambda: datetime.datetime.now(HELSINKI).date()
    client.login = AsyncMock()
    client.close = AsyncMock()
    client.get_students = AsyncMock(return_value=students)
    client.get_messages = AsyncMock(side_effect=_messages)
    client.fetch_content = AsyncMock(side_effect=_fetch_content)
    client.get_attendance = AsyncMock(side_effect=_report)
    client.get_schedule = AsyncMock(
        side_effect=lambda day, user_id=None: make_week(day)
    )
    client.get_bulletins = AsyncMock(
        side_effect=lambda user_id=None: make_bulletins(10, 9)
    )
    client.get_bulletin = AsyncMock(side_effect=_get_bulletin)
    return client


@pytest.fixture
def mock_client() -> Generator[MagicMock]:
    """A Wilma client for an account with one student."""
    client = build_client([STUDENT])
    with patch("custom_components.wilma.coordinator.WilmaClient", return_value=client):
        yield client


@pytest.fixture
def mock_two_student_client() -> Generator[MagicMock]:
    """A Wilma client for an account with two students."""
    client = build_client([STUDENT, SECOND_STUDENT])
    with patch("custom_components.wilma.coordinator.WilmaClient", return_value=client):
        yield client
