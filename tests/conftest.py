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
    Lesson,
    MarkType,
    Message,
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


@pytest.fixture
def mock_client() -> Generator[MagicMock]:
    """A Wilma client returning one recent and one old message, and two marks."""
    client = MagicMock()
    client.timezone = HELSINKI
    client.today = lambda: datetime.datetime.now(HELSINKI).date()
    client.get_schedule = AsyncMock(side_effect=lambda day: make_week(day))
    client.login = AsyncMock()
    client.close = AsyncMock()
    client.get_messages = AsyncMock(
        side_effect=lambda: [
            make_message(2, "Recent message", days_ago=1),
            make_message(1, "Old message", days_ago=30, unread=False),
        ]
    )

    async def fetch_content(messages: list[Message], *args: object) -> None:
        for message in messages:
            message.content_html = f"<p>Content {message.id}</p>"

    client.fetch_content = AsyncMock(side_effect=fetch_content)
    client.get_attendance = AsyncMock(
        side_effect=lambda *args, **kwargs: make_report(
            make_mark(POSITIVE, days_ago=2, hour=9, comment="Great work"),
            make_mark(HOMEWORK, days_ago=5, hour=10),
        )
    )

    with patch("custom_components.wilma.coordinator.WilmaClient", return_value=client):
        yield client
