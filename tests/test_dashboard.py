"""Tests for the dashboard strategy and the static dashboard YAML."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template

from custom_components.wilma.frontend import CARDS_MODULE, FRONTEND_DIR

DASHBOARD_YAML = Path(__file__).parent.parent / "dashboards" / "wilma.yaml"

# Card types that ship with Home Assistant's frontend
BUILTIN_CARDS = {
    "alarm-panel",
    "area",
    "button",
    "calendar",
    "conditional",
    "entities",
    "entity",
    "entity-filter",
    "gauge",
    "glance",
    "grid",
    "heading",
    "history-graph",
    "horizontal-stack",
    "humidifier",
    "iframe",
    "light",
    "logbook",
    "map",
    "markdown",
    "media-control",
    "picture",
    "picture-elements",
    "picture-entity",
    "picture-glance",
    "plant-status",
    "sensor",
    "statistic",
    "statistics-graph",
    "thermostat",
    "tile",
    "todo-list",
    "vertical-stack",
    "weather-forecast",
}


def integration_cards() -> set[str]:
    """The custom card types the integration's module registers."""
    source = (FRONTEND_DIR / CARDS_MODULE).read_text()
    return {
        f"custom:{name}" for name in re.findall(r'type: "(wilma-[a-z-]+-card)"', source)
    }


def known_cards() -> set[str]:
    return BUILTIN_CARDS | integration_cards()


def iter_cards(node: Any) -> Iterator[dict[str, Any]]:
    """Every card in a dashboard, view or section, including cards nested in cards."""
    if isinstance(node, list):
        for item in node:
            yield from iter_cards(item)
    elif isinstance(node, dict):
        for key, value in node.items():
            if key == "cards" and isinstance(value, list):
                for card in value:
                    if isinstance(card, dict):
                        yield card
                    yield from iter_cards(card)
            elif key == "card" and isinstance(value, dict):
                yield value
                yield from iter_cards(value)
            elif key in ("views", "sections"):
                yield from iter_cards(value)


def entity_ids(node: Any) -> set[str]:
    """Every entity ID mentioned anywhere in a config, templates included."""
    text = json.dumps(node)
    return set(re.findall(r"\b(?:sensor|binary_sensor|calendar)\.[a-z0-9_]+", text))


# Calls the strategies in Node with fake `hass` objects. Generating a dashboard doesn't depend on
# the date or time, so no clock is faked.
NODE_STRATEGY_TEST = r"""
import { pathToFileURL } from "node:url";

globalThis.window = globalThis;
globalThis.HTMLElement = class {};
const registry = new Map();
globalThis.customElements = {
  define: (name, element) => registry.set(name, element),
  get: (name) => registry.get(name),
};
console.info = () => {};
console.warn = () => {};

await import(pathToFileURL(process.argv[2]).href + "?v=test");

// Entity IDs as Home Assistant derives them from the device and entity names
const STUDENT_ENTITIES = {
  sensor: {
    latest_message: "latest_message",
    unread_count: "unread_messages",
    latest_attendance_mark: "latest_attendance_mark",
    attendance_count: "attendance_marks",
    latest_bulletin: "latest_bulletin",
    unread_bulletin_count: "new_bulletins",
    next_lesson: "next_lesson",
    lessons_today: "lessons_today",
    lessons_tomorrow: "lessons_tomorrow",
    lessons_this_week: "lessons_this_week",
    next_exam: "next_exam",
    upcoming_exams: "upcoming_exams",
    latest_exam_grade: "latest_exam_grade",
    latest_homework: "latest_homework",
  },
  binary_sensor: {
    recent_message: "recent_message",
    recent_bulletin: "recent_bulletin",
    recent_attendance: "recent_attendance_mark",
  },
  calendar: { schedule: "schedule", exams: "exams" },
};

function makeHass(students, language = "en") {
  const entities = {};
  const devices = {};
  const add = (domain, prefix, key, objectId, device) => {
    const id = `${domain}.${prefix}_${objectId}`;
    entities[id] = { entity_id: id, platform: "wilma", translation_key: key, device_id: device };
  };
  for (const { name, entry = "entry1", account = "username", only } of students) {
    const device = `dev_${name.toLowerCase()}`;
    devices[device] = { id: device, name: `Wilma ${name}`, config_entries: [entry], config_entry_id: entry };
    for (const [domain, keys] of Object.entries(STUDENT_ENTITIES)) {
      for (const [key, objectId] of Object.entries(keys)) {
        if (!only || only.includes(key)) add(domain, `wilma_${name.toLowerCase()}`, key, objectId, device);
      }
    }
    const accountDevice = `dev_account_${entry}`;
    if (!devices[accountDevice]) {
      devices[accountDevice] = { id: accountDevice, name: `Wilma (${account})`, config_entries: [entry], config_entry_id: entry };
      add("sensor", `wilma_${account}`, "last_update", "last_update", accountDevice);
      add("binary_sensor", `wilma_${account}`, "problem", "problem", accountDevice);
    }
  }
  // Entities of other integrations are never taken for a student's
  entities["sensor.other"] = { entity_id: "sensor.other", platform: "other", translation_key: "next_lesson", device_id: "dev_other" };
  devices.dev_other = { id: "dev_other", name: "Other" };
  return { entities, devices, states: {}, locale: { language }, language };
}

const ANNA = { name: "Anna" };
// A second student on another account, with only some of the entities
const BO = {
  name: "Bo", entry: "entry2", account: "other",
  only: ["next_lesson", "lessons_today", "latest_message", "attendance_count", "schedule"],
};

const dashboard = registry.get("ll-strategy-dashboard-wilma");
const view = registry.get("ll-strategy-view-wilma");
const none = makeHass([]);
const one = makeHass([ANNA]);
const two = makeHass([BO, ANNA]);

const result = { dashboards: {}, views: {}, errors: {} };
const dashboards = {
  none: [none, {}],
  one: [one, {}],
  two: [two, {}],
  two_fi: [makeHass([BO, ANNA], "fi"), {}],
  only_bo: [two, { students: ["dev_bo"] }],
  ordered: [two, { students: ["bo", "dev_anna"] }],
  unknown: [two, { students: ["Nobody"] }],
  hidden: [two, { hide: ["overview", "calendar", "badges", "homework"] }],
  hidden_all: [one, { hide: ["today", "week", "activity", "marks", "exams", "bulletins", "homework", "calendar", "account", "badges"] }],
};
for (const [name, [hass, options]] of Object.entries(dashboards)) {
  result.dashboards[name] = await dashboard.generate({ type: "custom:wilma", ...options }, hass);
}
result.views.anna = await view.generate({ type: "custom:wilma", student: "Anna" }, two);
result.views.all = await view.generate({ type: "custom:wilma" }, two);
result.views.none = await view.generate({ type: "custom:wilma" }, none);
for (const [name, options] of Object.entries({
  hide_unknown: { hide: ["bogus"] },
  hide_string: { hide: "calendar" },
  students_string: { students: "dev_anna" },
})) {
  try {
    await dashboard.generate({ type: "custom:wilma", ...options }, two);
    result.errors[name] = null;
  } catch (err) {
    result.errors[name] = String(err.message);
  }
}
result.registration = {
  strategies: window.customStrategies,
  noEditor: dashboard.noEditor,
  suggestions: dashboard.getCreateSuggestions(),
};
console.log(JSON.stringify(result));
"""


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """The strategies' output for the cases in the Node script."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed")
    script = tmp_path_factory.mktemp("strategy") / "strategy.mjs"
    script.write_text(NODE_STRATEGY_TEST)

    process = subprocess.run(
        [node, str(script), str(FRONTEND_DIR / CARDS_MODULE)],
        capture_output=True,
        check=False,
        timeout=60,
    )
    assert process.returncode == 0, process.stderr.decode()
    stdout = process.stdout
    result: dict[str, Any] = json.loads(stdout)
    return result


def card_types(node: Any) -> list[str]:
    return [card["type"] for card in iter_cards(node)]


def test_no_students_shows_a_message(generated: dict[str, Any]) -> None:
    (view,) = generated["dashboards"]["none"]["views"]
    assert card_types(view) == ["markdown"]
    content = next(iter_cards(view))["content"]
    assert "No Wilma students found" in content
    assert "Settings → Devices & services" in content
    assert generated["views"]["none"]["sections"] == view["sections"]


def test_one_student(generated: dict[str, Any]) -> None:
    dashboard = generated["dashboards"]["one"]
    assert "title" not in dashboard
    (view,) = dashboard["views"]
    assert view["title"] == "Anna"
    assert view["path"] == "anna"
    assert view["type"] == "sections"
    assert "icon" not in view

    types = card_types(view)
    assert set(types) <= known_cards()
    assert types == [
        "custom:wilma-next-lesson-card",
        "custom:wilma-schedule-card",
        "custom:wilma-schedule-card",
        "custom:wilma-timetable-card",
        "custom:wilma-activity-card",
        "tile",
        "tile",
        "custom:wilma-marks-card",
        "custom:wilma-exams-card",
        "tile",
        "markdown",
        "markdown",
        "calendar",
        "entities",
    ]
    for section in view["sections"]:
        assert section["type"] == "grid"
        assert section["cards"]

    cards = list(iter_cards(view))
    schedules = [card for card in cards if card["type"] == "custom:wilma-schedule-card"]
    assert [(card["entity"], card["mode"]) for card in schedules] == [
        ("sensor.wilma_anna_lessons_today", "day"),
        ("sensor.wilma_anna_lessons_tomorrow", "day"),
    ]
    # The week is a timetable in a section two columns wide
    timetable = next(c for c in cards if c["type"] == "custom:wilma-timetable-card")
    assert timetable["entity"] == "sensor.wilma_anna_lessons_this_week"
    assert timetable["week"] == "auto"
    week_section = next(s for s in view["sections"] if timetable in s["cards"])
    assert week_section["column_span"] == 2
    assert all(
        "column_span" not in s for s in view["sections"] if s is not week_section
    )
    activity = next(c for c in cards if c["type"] == "custom:wilma-activity-card")
    assert activity["latest_message"] == "sensor.wilma_anna_latest_message"
    assert activity["attendance_count"] == "sensor.wilma_anna_attendance_marks"
    assert activity["latest_bulletin"] == "sensor.wilma_anna_latest_bulletin"
    calendar = next(c for c in cards if c["type"] == "calendar")
    assert calendar["entities"] == [
        "calendar.wilma_anna_schedule",
        "calendar.wilma_anna_exams",
    ]
    markdown = [c["content"] for c in cards if c["type"] == "markdown"]
    assert "'sensor.wilma_anna_latest_bulletin'" in markdown[0]
    assert "content_markdown" in markdown[0]
    assert "'sensor.wilma_anna_latest_homework'" in markdown[1]
    account = cards[-1]
    assert [row["entity"] for row in account["entities"]] == [
        "sensor.wilma_username_last_update",
        "binary_sensor.wilma_username_problem",
    ]
    # The problem badge only appears while there is a problem
    problem = next(b for b in view["badges"] if "problem" in b["entity"])
    assert problem["visibility"] == [
        {
            "condition": "state",
            "entity": "binary_sensor.wilma_username_problem",
            "state": "on",
        }
    ]
    assert {e for e in entity_ids(view) if ".wilma_anna_" not in e} == {
        "sensor.wilma_username_last_update",
        "binary_sensor.wilma_username_problem",
    }


def test_two_students(generated: dict[str, Any]) -> None:
    views = generated["dashboards"]["two"]["views"]
    assert [v["title"] for v in views] == ["Overview", "Anna", "Bo"]
    assert [v["path"] for v in views] == ["overview", "anna", "bo"]
    overview, anna, bo = views
    assert overview["icon"] == "mdi:home-account"
    for view in views:
        assert set(card_types(view)) <= known_cards()

    # The overview has a column per student, then both accounts
    headings = [c["heading"] for c in iter_cards(overview) if c["type"] == "heading"]
    assert headings == ["Anna", "Bo"]
    anna_column, bo_column, accounts = overview["sections"]
    assert card_types(anna_column) == [
        "heading",
        "custom:wilma-next-lesson-card",
        "custom:wilma-schedule-card",
        "custom:wilma-activity-card",
    ]
    assert all(".wilma_anna_" in e for e in entity_ids(anna_column)) and entity_ids(
        anna_column
    )
    assert all(".wilma_bo_" in e for e in entity_ids(bo_column)) and entity_ids(
        bo_column
    )
    assert entity_ids(accounts) == {
        "sensor.wilma_username_last_update",
        "binary_sensor.wilma_username_problem",
        "sensor.wilma_other_last_update",
        "binary_sensor.wilma_other_problem",
    }

    # Each student's view uses only their own entities and their own account's
    assert {e for e in entity_ids(anna) if ".wilma_anna_" not in e} == {
        "sensor.wilma_username_last_update",
        "binary_sensor.wilma_username_problem",
    }
    assert {e for e in entity_ids(bo) if ".wilma_bo_" not in e} == {
        "sensor.wilma_other_last_update",
        "binary_sensor.wilma_other_problem",
    }
    # Cards for entities a student doesn't have are left out
    assert card_types(bo) == [
        "custom:wilma-next-lesson-card",
        "custom:wilma-schedule-card",
        "custom:wilma-activity-card",
        "custom:wilma-marks-card",
        "calendar",
        "entities",
    ]
    assert next(c for c in iter_cards(bo) if c["type"] == "calendar")["entities"] == [
        "calendar.wilma_bo_schedule"
    ]


def test_translated(generated: dict[str, Any]) -> None:
    views = generated["dashboards"]["two_fi"]["views"]
    assert views[0]["title"] == "Yleiskatsaus"
    titles = {c.get("title") for c in iter_cards(views[1])}
    assert {"Seuraava tunti", "Kotitehtävät", "Kalenteri"} <= titles


def test_students_option(generated: dict[str, Any]) -> None:
    dashboards = generated["dashboards"]
    (bo,) = dashboards["only_bo"]["views"]
    assert bo["title"] == "Bo"
    assert all(".wilma_bo_" in e or "wilma_other" in e for e in entity_ids(bo))

    # Listed order, by device ID or first name in any case
    ordered = dashboards["ordered"]["views"]
    assert [v["title"] for v in ordered] == ["Overview", "Bo", "Anna"]
    assert [c["heading"] for c in iter_cards(ordered[0]) if c["type"] == "heading"] == [
        "Bo",
        "Anna",
    ]

    (message,) = dashboards["unknown"]["views"]
    content = next(iter_cards(message))["content"]
    assert "No Wilma students found" in content
    assert "Nobody" in content


def test_hide_option(generated: dict[str, Any]) -> None:
    views = generated["dashboards"]["hidden"]["views"]
    assert [v["title"] for v in views] == ["Anna", "Bo"]
    for view in views:
        assert "badges" not in view
        assert "calendar" not in card_types(view)
        assert not any(
            "latest_homework" in c.get("content", "") for c in iter_cards(view)
        )
    # The bulletin stays when only homework is hidden
    assert any("latest_bulletin" in c.get("content", "") for c in iter_cards(views[0]))

    (bare,) = generated["dashboards"]["hidden_all"]["views"]
    assert bare["sections"] == []
    assert "badges" not in bare

    errors = generated["errors"]
    assert "unknown hide value bogus" in errors["hide_unknown"]
    assert "hide must be a list" in errors["hide_string"]
    assert "students must be a list" in errors["students_string"]


def test_dashboard_is_offered_when_adding_a_dashboard(
    generated: dict[str, Any],
) -> None:
    registration = generated["registration"]
    assert registration["strategies"] == [
        {
            "type": "wilma",
            "strategyType": "dashboard",
            "name": "Wilma",
            "description": (
                "Schedule, activity, attendance marks, exams and bulletins for every student"
            ),
            "documentationURL": registration["strategies"][0]["documentationURL"],
        }
    ]
    assert registration["noEditor"] is True
    assert registration["suggestions"] == {"title": "Wilma", "icon": "mdi:school"}


def test_view_strategy(generated: dict[str, Any]) -> None:
    dashboard = generated["dashboards"]["two"]["views"]
    assert generated["views"]["anna"] == dashboard[1]
    assert generated["views"]["all"] == dashboard[0]


def test_dashboard_yaml_mirrors_strategy(generated: dict[str, Any]) -> None:
    config = yaml.safe_load(DASHBOARD_YAML.read_text())
    assert config == generated["dashboards"]["one"]


def test_dashboard_yaml_uses_known_cards() -> None:
    config = yaml.safe_load(DASHBOARD_YAML.read_text())
    assert isinstance(config, dict)
    assert config["views"]
    types = card_types(config)
    assert types
    assert set(types) <= known_cards()
    assert integration_cards() == {
        "custom:wilma-schedule-card",
        "custom:wilma-timetable-card",
        "custom:wilma-next-lesson-card",
        "custom:wilma-activity-card",
        "custom:wilma-marks-card",
        "custom:wilma-exams-card",
    }
    assert {t for t in types if t.startswith("custom:")} == integration_cards()
    for badge in config["views"][0]["badges"]:
        assert badge["type"] == "entity"


async def test_dashboard_yaml_templates_render(hass: HomeAssistant) -> None:
    config = yaml.safe_load(DASHBOARD_YAML.read_text())
    markdown = [
        card["content"] for card in iter_cards(config) if card["type"] == "markdown"
    ]
    bulletin, homework = (Template(content, hass) for content in markdown)

    assert bulletin.async_render(parse_result=False) == "No bulletins"
    assert homework.async_render(parse_result=False) == "No homework"

    hass.states.async_set(
        "sensor.wilma_anna_latest_bulletin",
        "Sports day",
        {
            "date": "2026-11-04",
            "author": "Principal",
            "content_markdown": "Bring **trainers**.",
            "url": "https://example.org/news/3",
        },
    )
    hass.states.async_set(
        "sensor.wilma_anna_latest_homework",
        "Read chapter 3",
        {
            "date": "2026-11-03",
            "subject": "Biology",
            "text": "Read chapter 3",
            "recent_homework": [
                {"date": "2026-11-03", "subject": "Biology", "text": "Read\nchapter 3"},
                {"date": "2026-11-02", "subject": "Maths", "text": "Exercises 1-4"},
            ],
        },
    )
    assert bulletin.async_render(parse_result=False) == (
        "**Sports day**\n\n2026-11-04 · Principal\n\nBring **trainers**.\n\n"
        "[Open in Wilma](https://example.org/news/3)"
    )
    assert homework.async_render(parse_result=False) == (
        "- **Biology** (2026-11-03): Read chapter 3\n"
        "- **Maths** (2026-11-02): Exercises 1-4"
    )

    # Without the list, the latest homework stands in
    hass.states.async_set(
        "sensor.wilma_anna_latest_homework",
        "Read chapter 3",
        {"date": "2026-11-03", "subject": "Biology"},
    )
    assert homework.async_render(parse_result=False) == (
        "- **Biology** (2026-11-03): Read chapter 3"
    )
