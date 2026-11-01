"""Tests for serving the Lovelace cards and adding them to the frontend."""

from __future__ import annotations

import asyncio
import json
import shutil
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL, UrlManager
from homeassistant.const import EVENT_COMPONENT_LOADED
from homeassistant.core import HomeAssistant
from homeassistant.setup import ATTR_COMPONENT, async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.wilma.const import (
    CONF_PASSWORD,
    CONF_SERVER_URL,
    CONF_USERNAME,
    DOMAIN,
)
from custom_components.wilma.frontend import (
    CARDS_MODULE,
    FRONTEND_DIR,
    URL_BASE,
    cards_url,
)

from .conftest import SECOND_STUDENT, STUDENT, build_client

MANIFEST = Path(__file__).parent.parent / "custom_components" / DOMAIN / "manifest.json"
VERSION = json.loads(MANIFEST.read_text())["version"]
CARDS_URL = f"{URL_BASE}/{CARDS_MODULE}?v={VERSION}"


@pytest.fixture
def clients() -> Generator[list[MagicMock]]:
    """A separate Wilma client for every config entry that gets set up."""
    created: list[MagicMock] = []

    def make(*args: object, **kwargs: object) -> MagicMock:
        client = build_client([STUDENT] if not created else [SECOND_STUDENT])
        created.append(client)
        return client

    with patch("custom_components.wilma.coordinator.WilmaClient", side_effect=make):
        yield created


def _second_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Wilma (other)",
        data={
            CONF_SERVER_URL: "https://other.inschool.fi",
            CONF_USERNAME: "other",
            CONF_PASSWORD: "otherpass",
        },
        unique_id="https://other.inschool.fi|other",
        entry_id="other",
    )


def _fake_frontend(hass: HomeAssistant) -> UrlManager:
    """Stand in for the frontend integration, whose UI package isn't installed in tests."""
    urls = UrlManager(lambda *args: None, [])
    hass.data[DATA_EXTRA_MODULE_URL] = urls
    hass.config.components.add("frontend")
    return urls


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_cards_registered_once_for_several_entries(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    clients: list[MagicMock],
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    assert await async_setup_component(hass, "http", {})
    urls = _fake_frontend(hass)

    with patch.object(
        hass.http,
        "async_register_static_paths",
        wraps=hass.http.async_register_static_paths,
    ) as register:
        await _setup(hass, mock_config_entry)
        await _setup(hass, _second_entry())
        # Reloading an entry doesn't register again either
        assert await hass.config_entries.async_reload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert len(clients) >= 2
    register.assert_awaited_once()
    (config,) = register.await_args.args[0]
    assert config.url_path == URL_BASE
    assert Path(config.path) == FRONTEND_DIR
    assert urls.urls == frozenset({CARDS_URL})
    assert cards_url(VERSION) == CARDS_URL

    client = await hass_client_no_auth()
    response = await client.get(CARDS_URL)
    assert response.status == 200
    body = await response.text()
    assert "customElements.define" in body
    assert (FRONTEND_DIR / CARDS_MODULE).read_text() == body


async def test_setup_without_frontend_registers_once_it_loads(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    assert await async_setup_component(hass, "http", {})
    await _setup(hass, mock_config_entry)
    assert DATA_EXTRA_MODULE_URL not in hass.data

    urls = _fake_frontend(hass)
    hass.bus.async_fire(EVENT_COMPONENT_LOADED, {ATTR_COMPONENT: "frontend"})
    await hass.async_block_till_done()

    assert urls.urls == frozenset({CARDS_URL})


def test_cards_module_exists() -> None:
    assert (FRONTEND_DIR / CARDS_MODULE).is_file()


# Renders every card in Node with a minimal DOM and a fake `hass`, to catch runtime errors
# and check the main content of each card without a browser.
NODE_SMOKE_TEST = r"""
import { pathToFileURL } from "node:url";

globalThis.window = globalThis;
globalThis.HTMLElement = class {
  attachShadow() {
    this.shadowRoot = { innerHTML: "" };
    return this.shadowRoot;
  }
};
const registry = new Map();
globalThis.customElements = {
  define: (name, element) => registry.set(name, element),
  get: (name) => registry.get(name),
};
console.info = () => {};

// A fixed clock (a Wednesday at noon UTC) keeps day and week boundaries out of the results
const FIXED_NOW = Date.UTC(2026, 10, 4, 12, 0, 0);
const RealDate = Date;
globalThis.Date = class extends RealDate {
  constructor(...args) {
    super(...(args.length ? args : [FIXED_NOW]));
  }
  static now() {
    return FIXED_NOW;
  }
};

await import(pathToFileURL(process.argv[2]).href + "?v=test");

const now = Date.now();
const iso = (minutes) => new Date(now + minutes * 60000).toISOString();
const day = (days) => new Date(now + days * 86400000).toISOString().slice(0, 10);
const lesson = (from, to, subject) => ({
  start: iso(from), end: iso(to), subject, teachers: ["Anna Teacher"], rooms: ["419"],
});
const today = day(0);
const weekday = new Date(today + "T12:00:00Z").getUTCDay() || 7;

const ANNA = "dev_anna";
const BO = "dev_bo";
const entities = {};
const states = {};
function add(entityId, key, device, state, attributes = {}) {
  entities[entityId] = { entity_id: entityId, platform: "wilma", translation_key: key, device_id: device };
  states[entityId] = { entity_id: entityId, state: String(state), attributes };
}

const lessons = [lesson(-120, -75, "Matematik"), lesson(-10, 35, "Svenska"), lesson(60, 105, "Biologi")];
add("sensor.wilma_anna_lessons_today", "lessons_today", ANNA, 3, {
  date: today, start: lessons[0].start, end: lessons[2].end, lessons,
});
add("sensor.wilma_anna_lessons_tomorrow", "lessons_tomorrow", ANNA, 0, {
  date: day(1), start: null, end: null, lessons: [],
});
add("sensor.wilma_anna_lessons_this_week", "lessons_this_week", ANNA, 3, {
  week_start: day(1 - weekday), week_end: day(7 - weekday), lessons,
});
add("sensor.wilma_anna_next_lesson", "next_lesson", ANNA, "Biologi", {
  date: today, ...lesson(25, 70, "Biologi"),
});
add("sensor.wilma_anna_latest_message", "latest_message", ANNA, "Excursion", {
  id: 7, subject: "Excursion", sender: "Teacher Seven", timestamp: "2099-01-03 10:00",
  recent_messages: [
    { id: 7, subject: "Excursion", sender: "Teacher Seven", timestamp: "2099-01-03 10:00", unread: true },
    { id: 6, subject: "<img src=x onerror=alert(1)>", sender: "Teacher Six", timestamp: "2099-01-01 09:00", unread: false },
  ],
});
add("sensor.wilma_anna_attendance_count", "attendance_count", ANNA, 3, {
  by_type: { "Övrig positiv feedback": 2, "Ogjorda läxor och uppgifter": 1 },
  by_code: { "+": 2, "Ogjorda uppgifter": 1 },
  types: [
    { type_id: 146, code: "+", description: "Övrig positiv feedback", color: "#9191FF", count: 2 },
    { type_id: 135, code: "Ogjorda uppgifter", description: "Ogjorda läxor och uppgifter", color: "#0080FF", count: 1 },
    { type_id: 131, code: "Beteende", description: "Störande", color: "#D4D4D4", count: 0 },
  ],
  recent_marks: [
    { date: "2099-01-02", hour: 9, code: "+", description: "Övrig positiv feedback", color: "#9191FF", course: "ma05", comment: "Great work", teacher: "Mark Teacher" },
  ],
});
add("sensor.wilma_anna_latest_attendance_mark", "latest_attendance_mark", ANNA, "Övrig positiv feedback", {
  date: "2099-01-02", hour: 9, code: "+", description: "Övrig positiv feedback", color: "#9191FF", teacher: "Mark Teacher",
});
add("sensor.wilma_anna_latest_bulletin", "latest_bulletin", ANNA, "Sports day", {
  id: 3, title: "Sports day", date: "2099-01-04", author: "Principal", url: "https://example.org/news/3",
  recent_bulletins: [{ id: 3, title: "Sports day", date: "2099-01-04", author: "Principal", url: "https://example.org/news/3" }],
});
add("sensor.wilma_anna_upcoming_exams", "upcoming_exams", ANNA, 2, {
  exams: [
    { date: day(-3), subject: "Past exam", info: null, teachers: [] },
    { date: day(2), subject: "Kemi", name: "Kurssikoe", info: "Chapters 1-3", teachers: ["Exam Teacher"], grade: "9" },
    { date: day(9), subject: "Historia", info: null, teachers: ["Other Teacher"] },
  ],
});
// A second student, with only the attributes from before the newer lists existed
add("sensor.wilma_bo_latest_message", "latest_message", BO, "Old style", {
  id: 1, subject: "Old style", sender: "Bo's teacher", timestamp: "2099-01-01 08:00",
});
add("sensor.wilma_bo_attendance_count", "attendance_count", BO, 1, {
  by_type: { "Beteende": 1 }, by_code: { "Beteende": 1 },
});
add("sensor.wilma_bo_latest_attendance_mark", "latest_attendance_mark", BO, "Beteende", {
  date: "2099-01-01", hour: null, code: "Beteende", description: "Beteende", color: "#D4D4D4", teacher: "Bo Mark Teacher",
});
add("sensor.wilma_bo_latest_bulletin", "latest_bulletin", BO, "unavailable", {});
add("sensor.wilma_bo_next_lesson", "next_lesson", BO, "unknown", {});

const hass = {
  entities, states,
  devices: { [ANNA]: { id: ANNA, name: "Wilma Anna" }, [BO]: { id: BO, name: "Wilma Bo" } },
  locale: { language: process.argv[3] || "en", time_format: "24", time_zone: "server" },
  language: process.argv[3] || "en",
  config: { time_zone: "UTC" },
};

function render(type, config) {
  const element = new (customElements.get(type))();
  element.setConfig(config);
  element.hass = hass;
  element.connectedCallback();
  const html = element.shadowRoot.innerHTML;
  const size = element.getCardSize();
  element.disconnectedCallback();
  if (!Number.isFinite(size)) throw new Error(`${type}: bad card size`);
  return html;
}

const result = {
  cards: window.customCards.map((card) => card.type),
  elements: [...registry.keys()],
  stubs: {},
  html: {},
};
for (const type of result.cards) result.stubs[type] = registry.get(type).getStubConfig(hass);
const cases = {
  schedule_day: ["wilma-schedule-card", { entity: "sensor.wilma_anna_lessons_today" }],
  schedule_tomorrow: ["wilma-schedule-card", { entity: "sensor.wilma_anna_lessons_tomorrow" }],
  schedule_week: ["wilma-schedule-card", { entity: "sensor.wilma_anna_lessons_this_week", mode: "week" }],
  schedule_student: ["wilma-schedule-card", { student: ANNA, mode: "week" }],
  schedule_missing: ["wilma-schedule-card", { entity: "sensor.nope" }],
  schedule_unconfigured: ["wilma-schedule-card", {}],
  next_lesson: ["wilma-next-lesson-card", { entity: "sensor.wilma_anna_next_lesson" }],
  next_lesson_none: ["wilma-next-lesson-card", { entity: "sensor.wilma_bo_next_lesson" }],
  activity: ["wilma-activity-card", result.stubs["wilma-activity-card"]],
  activity_limited: ["wilma-activity-card", { ...result.stubs["wilma-activity-card"], max_items: 2 }],
  activity_fallback: ["wilma-activity-card", { student: BO }],
  marks: ["wilma-marks-card", { entity: "sensor.wilma_anna_attendance_count" }],
  marks_fallback: ["wilma-marks-card", { entity: "sensor.wilma_bo_attendance_count" }],
  exams: ["wilma-exams-card", { entity: "sensor.wilma_anna_upcoming_exams" }],
  exams_missing: ["wilma-exams-card", { student: BO }],
};
for (const [name, [type, config]] of Object.entries(cases)) result.html[name] = render(type, config);

let rejected = 0;
for (const [type, config] of [
  ["wilma-schedule-card", { mode: "month" }],
  ["wilma-activity-card", { max_items: 0 }],
]) {
  try { render(type, config); } catch (err) { rejected += 1; }
}
result.rejected = rejected;
console.log(JSON.stringify(result));
"""


async def _run_node(language: str, tmp_path: Path) -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed")
    script = tmp_path / "smoke.mjs"
    script.write_text(NODE_SMOKE_TEST)
    process = await asyncio.create_subprocess_exec(
        node,
        str(script),
        str(FRONTEND_DIR / CARDS_MODULE),
        language,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    assert process.returncode == 0, stderr.decode()
    return json.loads(stdout)


async def test_cards_render(tmp_path: Path) -> None:
    result = await _run_node("en", tmp_path)
    html = result["html"]

    assert result["cards"] == [
        "wilma-schedule-card",
        "wilma-timetable-card",
        "wilma-next-lesson-card",
        "wilma-activity-card",
        "wilma-marks-card",
        "wilma-exams-card",
    ]
    # The dashboard and view strategies come with the same module
    assert result["elements"] == [
        *result["cards"],
        "ll-strategy-dashboard-wilma",
        "ll-strategy-view-wilma",
    ]
    assert result["rejected"] == 2
    for name, markup in html.items():
        assert "could not be displayed" not in markup, name

    # The card picker preselects the first student's entities
    stubs = result["stubs"]
    assert stubs["wilma-schedule-card"]["entity"] == "sensor.wilma_anna_lessons_today"
    assert stubs["wilma-next-lesson-card"]["entity"] == "sensor.wilma_anna_next_lesson"
    assert stubs["wilma-activity-card"] == {
        "latest_message": "sensor.wilma_anna_latest_message",
        "attendance_count": "sensor.wilma_anna_attendance_count",
        "latest_bulletin": "sensor.wilma_anna_latest_bulletin",
        "max_items": 10,
    }
    assert stubs["wilma-marks-card"]["entity"] == "sensor.wilma_anna_attendance_count"
    assert stubs["wilma-exams-card"]["entity"] == "sensor.wilma_anna_upcoming_exams"

    day = html["schedule_day"]
    assert "Schedule · Anna" in day
    assert 'class="lesson past"' in day
    assert 'class="lesson now"' in day
    assert ">Now<" in day
    assert day.index("Matematik") < day.index("Svenska") < day.index("Biologi")
    assert "No lessons" in html["schedule_tomorrow"]
    week = html["schedule_week"]
    assert week.count('class="day ') >= 5
    assert 'aria-current="date"' in week
    assert "Svenska" in week
    assert html["schedule_student"] == week
    assert "Entity not found: sensor.nope" in html["schedule_missing"]
    assert "Choose an entity" in html["schedule_unconfigured"]

    assert "Biologi" in html["next_lesson"]
    assert "minutes" in html["next_lesson"]
    assert "No upcoming lessons" in html["next_lesson_none"]

    activity = html["activity"]
    order = [
        activity.index(text)
        for text in ("Sports day", "Excursion", "Great work", "Teacher Six")
    ]
    assert order == sorted(order)
    assert "Mark Teacher" in activity
    assert "#9191FF" in activity
    assert ">+<" in activity
    assert ">Unread<" in activity
    assert "<img" not in activity
    assert "&lt;img src=x" in activity
    assert html["activity_limited"].count('class="item ') == 2
    fallback = html["activity_fallback"]
    assert "Old style" in fallback
    assert "Bo Mark Teacher" in fallback
    assert "is unavailable" in fallback

    marks = html["marks"]
    assert "3 this school year" in marks
    assert "#0080FF" in marks
    assert "Ogjorda uppgifter" in marks
    assert "Beteende" not in marks
    assert "Great work" in marks
    marks_fallback = html["marks_fallback"]
    assert "Beteende" in marks_fallback
    assert "Bo Mark Teacher" in marks_fallback

    exams = html["exams"]
    assert "Past exam" not in exams
    assert exams.index("Kemi") < exams.index("Historia")
    assert "Grade" in exams
    assert "Chapters 1-3" in exams
    assert "Kurssikoe" in exams
    assert "in 2 days" in exams
    assert "Choose an entity" in html["exams_missing"]


@pytest.mark.parametrize("language", ["fi", "sv"])
async def test_cards_render_translated(language: str, tmp_path: Path) -> None:
    result = await _run_node(language, tmp_path)
    expected = {"fi": "Ei oppitunteja", "sv": "Inga lektioner"}[language]
    assert expected in result["html"]["schedule_tomorrow"]
    for name, markup in result["html"].items():
        assert "could not be displayed" not in markup, name
        assert "Kortet kunde inte visas" not in markup, name
        assert "Korttia ei voitu näyttää" not in markup, name
