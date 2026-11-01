"""Tests for the weekly timetable card, rendered in Node with a fake Home Assistant."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

CARDS = (
    Path(__file__).parent.parent
    / "custom_components"
    / "wilma"
    / "frontend"
    / "wilma-cards.js"
)

# Renders scenarios with a minimal DOM shim and a clock set per scenario, and prints the
# resulting HTML (or error) of each as JSON.
SCRIPT = r"""
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

let fixedNow = 0;
const RealDate = Date;
globalThis.Date = class extends RealDate {
  constructor(...args) {
    super(...(args.length ? args : [fixedNow]));
  }
  static now() {
    return fixedNow;
  }
};

await import(pathToFileURL(process.argv[2]).href + "?v=test");
const Card = registry.get("wilma-timetable-card");

const lesson = (day, from, to, subject, extra = {}) => ({
  start: `${day}T${from}:00+02:00`, end: `${day}T${to}:00+02:00`, subject,
  teachers: ["Anna Teacher"], rooms: ["419"], ...extra,
});

// Week 45 of 2026: Monday 2 to Sunday 8 November
const THIS_WEEK = [
  lesson("2026-11-02", "08:15", "09:00", "Matematik", { color: "#A6CAF0" }),
  lesson("2026-11-02", "09:15", "10:00", "Svenska"),
  lesson("2026-11-03", "08:15", "09:00", "Matematik", { color: "#A6CAF0" }),
  lesson("2026-11-04", "08:15", "09:00", "Matematik", { color: "#A6CAF0" }),
  lesson("2026-11-04", "09:15", "10:00", "Svenska"),
  lesson("2026-11-04", "10:15", "11:00", "Musik"),
  lesson("2026-11-04", "10:30", "11:15", "<b>Engelska</b>"),
  lesson("2026-11-05", "12:00", "13:30", "Gymnastik", { color: "#202060" }),
];
const NEXT_WEEK = [lesson("2026-11-09", "09:15", "10:00", "Bildkonst")];

function makeHass({ language = "en", withNext = true, thisWeek = THIS_WEEK } = {}) {
  const entities = {
    "sensor.wilma_anna_lessons_this_week": { translation_key: "lessons_this_week" },
  };
  const states = {
    "sensor.wilma_anna_lessons_this_week": {
      state: String(thisWeek.length),
      attributes: { week_start: "2026-11-02", week_end: "2026-11-08", lessons: thisWeek },
    },
  };
  if (withNext) {
    entities["sensor.wilma_anna_lessons_next_week"] = { translation_key: "lessons_next_week" };
    states["sensor.wilma_anna_lessons_next_week"] = {
      state: "1",
      attributes: { week_start: "2026-11-09", week_end: "2026-11-15", lessons: NEXT_WEEK },
    };
  }
  for (const [id, entry] of Object.entries(entities)) {
    Object.assign(entry, { entity_id: id, platform: "wilma", device_id: "dev_anna" });
  }
  return {
    entities, states,
    devices: { dev_anna: { name: "Wilma Anna" } },
    locale: { language, time_format: "24", time_zone: "server" },
    config: { time_zone: "Europe/Helsinki" },
    language,
  };
}

function render(config, { now, hass, choice } = {}) {
  fixedNow = RealDate.parse(now);
  const card = new Card();
  try {
    card.setConfig(config);
  } catch (err) {
    return { error: err.message };
  }
  if (choice) card._choice = choice;
  card.hass = hass || makeHass();
  return { html: card.shadowRoot.innerHTML, size: card.getCardSize() };
}

const WEDNESDAY = "2026-11-04T09:30:00+02:00";
const SATURDAY = "2026-11-07T10:00:00+02:00";
const entity = "sensor.wilma_anna_lessons_this_week";
const result = {
  wednesday: render({ entity }, { now: WEDNESDAY }),
  saturday: render({ entity }, { now: SATURDAY }),
  saturday_current: render({ entity, week: "current" }, { now: SATURDAY }),
  wednesday_next: render({ entity, week: "next" }, { now: WEDNESDAY }),
  picked_next: render({ entity }, { now: WEDNESDAY, choice: "next" }),
  from_next_entity: render({ entity: "sensor.wilma_anna_lessons_next_week" }, { now: WEDNESDAY }),
  by_student: render({ student: "dev_anna" }, { now: WEDNESDAY }),
  no_next: render({ entity }, { now: SATURDAY, hass: makeHass({ withNext: false }) }),
  weekend: render({ entity }, {
    now: WEDNESDAY,
    hass: makeHass({ thisWeek: [...THIS_WEEK, lesson("2026-11-07", "10:00", "11:00", "Läger")] }),
  }),
  weekend_hidden: render({ entity, show_weekends: false }, {
    now: WEDNESDAY,
    hass: makeHass({ thisWeek: [...THIS_WEEK, lesson("2026-11-07", "10:00", "11:00", "Läger")] }),
  }),
  empty_week: render({ entity, week: "current" }, { now: WEDNESDAY, hass: makeHass({ thisWeek: [] }) }),
  finnish: render({ entity }, { now: WEDNESDAY, hass: makeHass({ language: "fi" }) }),
  fixed_hours: render({ entity, start_hour: 7, end_hour: 15, hour_height: 40 }, { now: WEDNESDAY }),
  teachers: render({ entity, show_teachers: true, hour_height: 100 }, { now: WEDNESDAY }),
  missing: render({ entity: "sensor.nope" }, { now: WEDNESDAY }),
  bad_week: render({ entity, week: "later" }, { now: WEDNESDAY }),
  bad_hours: render({ entity, start_hour: 15, end_hour: 8 }, { now: WEDNESDAY }),
  bad_height: render({ entity, hour_height: "tall" }, { now: WEDNESDAY }),
  stub: Card.getStubConfig(makeHass()),
};
console.log(JSON.stringify(result));
"""


@pytest.fixture(scope="module")
def rendered(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    script = tmp_path_factory.mktemp("timetable") / "timetable.mjs"
    script.write_text(SCRIPT)
    output = subprocess.run(
        [node, str(script), str(CARDS)],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return json.loads(output.stdout)


def musik_block(blocks: list[str]) -> str:
    """The upcoming Musik lesson, light-coloured, so it gets dark text."""
    return next(block for block in blocks if 'class="subject">Musik<' in block)


def _blocks(html: str) -> list[str]:
    return [part.split("</li>")[0] for part in html.split('<li class="block')[1:]]


def test_current_week_grid(rendered: dict[str, Any]) -> None:
    html = rendered["wednesday"]["html"]

    assert "Weekly timetable · Anna" in html
    assert "Week 45 · Nov 2 – Nov 6" in html
    # Monday to Friday; Friday has no lessons, and no weekend without lessons
    assert html.count('<section class="day') == 5
    assert html.count("No lessons") == 1
    # Wednesday is today, with the now line and the ongoing lesson
    assert html.count('class="head today" aria-current="date"') == 1
    assert html.count('class="now-line"') == 1
    ongoing = [block for block in _blocks(html) if 'aria-current="time"' in block]
    assert len(ongoing) == 1
    assert "Svenska" in ongoing[0]
    # Earlier lessons are past, later ones not
    assert sum(" past" in block.split('"')[0] for block in _blocks(html)) == 4
    # Hours from 08:00 to 14:00 at 56 px per hour
    assert "--grid-height:336px" in html
    assert ">08:00<" in html
    assert "This week" in html
    assert 'data-week="current" aria-pressed="true"' in html


def test_blocks(rendered: dict[str, Any]) -> None:
    blocks = _blocks(rendered["wednesday"]["html"])
    by_subject = {
        block.split('class="subject">')[1].split("<")[0]: block for block in blocks
    }

    # Wilma's colour with readable text; lessons without one get a stable palette colour
    matematik = by_subject["Matematik"]
    # Matematik on Wednesday is over: it fades into the card and uses the theme's text colour
    assert "--lesson-color:#A6CAF0" in matematik and ";color:#" not in matematik
    gymnastik = by_subject["Gymnastik"]
    assert "--lesson-color:#202060" in gymnastik and ";color:#ffffff" in gymnastik
    assert "--lesson-color:#" in by_subject["Svenska"]
    assert ";color:#1c1c1c" in musik_block(blocks)
    # 08:15-09:00 starts 15 minutes into the grid: 14 px down, 42 px tall minus a gap
    assert "top:14px" in matematik and "height:40px" in matematik
    assert "08:15–09:00" in matematik
    # Overlapping lessons share the column in two lanes
    musik, engelska = by_subject["Musik"], by_subject["&lt;b&gt;Engelska&lt;/b&gt;"]
    assert "width:calc(50% - 2px)" in musik and "width:calc(50% - 2px)" in engelska
    assert "inset-inline-start:calc(0% + 1px)" in musik
    assert "inset-inline-start:calc(50% + 1px)" in engelska
    # Single lessons use the full width, and the teacher is only for screen readers
    assert "width:calc(100% - 2px)" in matematik
    assert "Anna Teacher" in matematik and 'class="sr"' in matematik


def test_teachers_shown_when_configured(rendered: dict[str, Any]) -> None:
    blocks = _blocks(rendered["teachers"]["html"])
    gymnastik = next(block for block in blocks if "Gymnastik" in block)
    assert '<div class="line optional">Anna Teacher</div>' in gymnastik
    assert '<div class="line optional">419</div>' in gymnastik


def test_escapes_text(rendered: dict[str, Any]) -> None:
    html = rendered["wednesday"]["html"]
    assert "<b>Engelska</b>" not in html
    assert "&lt;b&gt;Engelska&lt;/b&gt;" in html


def test_automatic_week(rendered: dict[str, Any]) -> None:
    saturday = rendered["saturday"]["html"]
    assert 'data-week="next" aria-pressed="true"' in saturday
    assert "Week 46 · Nov 9 – Nov 13" in saturday
    assert "Bildkonst" in saturday

    current = rendered["saturday_current"]["html"]
    assert 'data-week="current" aria-pressed="true"' in current
    assert "Week 45" in current


def test_week_choices(rendered: dict[str, Any]) -> None:
    for name in ("wednesday_next", "picked_next", "from_next_entity"):
        html = rendered[name]["html"]
        if name == "from_next_entity":
            # A next-week entity still offers both weeks; automatic picks this week on Wednesday
            assert 'data-week="current" aria-pressed="true"' in html
            continue
        assert 'data-week="next" aria-pressed="true"' in html, name
        assert "Bildkonst" in html

    assert "Week 45" in rendered["by_student"]["html"]


def test_without_next_week_sensor(rendered: dict[str, Any]) -> None:
    html = rendered["no_next"]["html"]
    assert "data-week" not in html
    assert "Week 45" in html


def test_weekends(rendered: dict[str, Any]) -> None:
    assert rendered["weekend"]["html"].count('<section class="day') == 6
    assert "Week 45 · Nov 2 – Nov 7" in rendered["weekend"]["html"]
    assert "Läger" in rendered["weekend"]["html"]
    assert rendered["weekend_hidden"]["html"].count('<section class="day') == 5


def test_empty_week(rendered: dict[str, Any]) -> None:
    html = rendered["empty_week"]["html"]
    assert "No lessons" in html
    assert '<section class="day' not in html


def test_finnish(rendered: dict[str, Any]) -> None:
    html = rendered["finnish"]["html"]
    assert "Viikon lukujärjestys · Anna" in html
    assert "Viikko 45 · 2.11. – 6.11." in html
    assert "Tämä viikko" in html and "Ensi viikko" in html


def test_fixed_hours(rendered: dict[str, Any]) -> None:
    html = rendered["fixed_hours"]["html"]
    assert "--grid-height:320px" in html
    assert ">07:00<" in html and ">14:00<" in html


def test_problems_and_invalid_config(rendered: dict[str, Any]) -> None:
    assert "Entity not found: sensor.nope" in rendered["missing"]["html"]
    assert "week must be" in rendered["bad_week"]["error"]
    assert "start_hour must be before end_hour" in rendered["bad_hours"]["error"]
    assert "hour_height must be" in rendered["bad_height"]["error"]


def test_stub_config_and_size(rendered: dict[str, Any]) -> None:
    assert rendered["stub"] == {
        "entity": "sensor.wilma_anna_lessons_this_week",
        "week": "auto",
    }
    assert rendered["wednesday"]["size"] >= 6
