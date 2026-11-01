/*
 * Lovelace cards for the Wilma integration.
 *
 * Plain web components without a build step or external imports: everything they need is
 * in this file or provided by Home Assistant at runtime (ha-card, ha-icon, theme variables).
 */

const DOMAIN = "wilma";
const VERSION = new URL(import.meta.url).searchParams.get("v") || "dev";
const DOCS_URL = "https://github.com/frwickst/wilma_ha#lovelace-cards";
const TICK_MS = 60 * 1000;

/* Translation keys of the per-student entities, used to find a student's entities. */
const STUDENT_KEYS = new Set([
  "latest_message",
  "unread_count",
  "latest_attendance_mark",
  "attendance_count",
  "latest_bulletin",
  "unread_bulletin_count",
  "next_lesson",
  "lessons_today",
  "lessons_tomorrow",
  "lessons_this_week",
  "upcoming_exams",
  "next_exam",
  "latest_exam_grade",
  "latest_homework",
  "schedule",
]);

/* ---------- Localisation ---------- */

const STRINGS = {
  en: {
    schedule: "Schedule",
    today: "Today",
    tomorrow: "Tomorrow",
    yesterday: "Yesterday",
    no_lessons: "No lessons",
    now: "Now",
    ended: "ended",
    next_lesson: "Next lesson",
    no_next_lesson: "No upcoming lessons",
    started: "Started",
    activity: "Recent activity",
    no_activity: "Nothing yet",
    message: "Message",
    mark: "Attendance mark",
    bulletin: "Bulletin",
    unread: "Unread",
    marks: "Attendance marks",
    marks_total: "{count} this school year",
    latest_marks: "Latest marks",
    no_marks: "No marks this school year",
    exams: "Upcoming exams",
    no_exams: "No upcoming exams",
    grade: "Grade",
    room: "Room",
    teacher: "Teacher",
    choose_entity: "Choose an entity in the card configuration.",
    not_found: "Entity not found: {id}",
    unavailable: "{name} is unavailable",
    error: "The card could not be displayed",
    // Card editor labels
    entity: "Entity",
    student: "Student (finds the entities automatically)",
    mode: "Mode",
    mode_day: "Day",
    mode_week: "Week",
    day: "Day (with student)",
    title: "Title",
    hide_past_days: "Hide past days",
    show_teachers: "Show teachers",
    show_rooms: "Show rooms",
    max_items: "Number of items",
    recent: "Latest marks to show",
    latest_message: "Latest message sensor",
    attendance_count: "Attendance marks sensor",
    latest_bulletin: "Latest bulletin sensor",
    // Dashboard strategy
    overview: "Overview",
    this_week: "This week",
    unread_messages: "Unread messages",
    new_bulletins: "New bulletins",
    bulletin_title: "Latest bulletin",
    homework: "Homework",
    latest_grade: "Latest exam grade",
    calendar: "Calendar",
    account: "Wilma account",
    problem: "Problem",
    last_update: "Last update",
    no_bulletins: "No bulletins",
    no_homework: "No homework",
    open_in_wilma: "Open in Wilma",
    no_students_title: "No Wilma students found",
    no_students_text:
      "Set up the Wilma integration under Settings → Devices & services. Its students appear here once it has loaded; refresh the page after adding it.",
    unknown_students: "Not found among the Wilma students: {names}",
  },
  fi: {
    schedule: "Lukujärjestys",
    today: "Tänään",
    tomorrow: "Huomenna",
    yesterday: "Eilen",
    no_lessons: "Ei oppitunteja",
    now: "Nyt",
    ended: "päättynyt",
    next_lesson: "Seuraava tunti",
    no_next_lesson: "Ei tulevia oppitunteja",
    started: "Alkanut",
    activity: "Viimeaikaiset tapahtumat",
    no_activity: "Ei tapahtumia",
    message: "Viesti",
    mark: "Tuntimerkintä",
    bulletin: "Tiedote",
    unread: "Lukematon",
    marks: "Tuntimerkinnät",
    marks_total: "{count} tänä lukuvuonna",
    latest_marks: "Uusimmat merkinnät",
    no_marks: "Ei merkintöjä tänä lukuvuonna",
    exams: "Tulevat kokeet",
    no_exams: "Ei tulevia kokeita",
    grade: "Arvosana",
    room: "Luokka",
    teacher: "Opettaja",
    choose_entity: "Valitse entiteetti kortin asetuksista.",
    not_found: "Entiteettiä ei löydy: {id}",
    unavailable: "{name} ei ole saatavilla",
    error: "Korttia ei voitu näyttää",
    overview: "Yleiskatsaus",
    this_week: "Tämä viikko",
    unread_messages: "Lukemattomat viestit",
    new_bulletins: "Uudet tiedotteet",
    bulletin_title: "Uusin tiedote",
    homework: "Kotitehtävät",
    latest_grade: "Viimeisin koearvosana",
    calendar: "Kalenteri",
    account: "Wilma-tili",
    problem: "Ongelma",
    last_update: "Viimeisin päivitys",
    no_bulletins: "Ei tiedotteita",
    no_homework: "Ei kotitehtäviä",
    open_in_wilma: "Avaa Wilmassa",
    no_students_title: "Wilma-oppilaita ei löytynyt",
    no_students_text:
      "Ota Wilma-integraatio käyttöön kohdassa Asetukset → Laitteet ja palvelut. Oppilaat näkyvät täällä, kun se on latautunut; päivitä sivu lisäämisen jälkeen.",
    unknown_students: "Ei löytynyt Wilma-oppilaista: {names}",
  },
  sv: {
    schedule: "Schema",
    today: "I dag",
    tomorrow: "I morgon",
    yesterday: "I går",
    no_lessons: "Inga lektioner",
    now: "Nu",
    ended: "slut",
    next_lesson: "Nästa lektion",
    no_next_lesson: "Inga kommande lektioner",
    started: "Har börjat",
    activity: "Senaste händelser",
    no_activity: "Inga händelser",
    message: "Meddelande",
    mark: "Lektionsanteckning",
    bulletin: "Anslag",
    unread: "Oläst",
    marks: "Lektionsanteckningar",
    marks_total: "{count} detta läsår",
    latest_marks: "Senaste anteckningar",
    no_marks: "Inga anteckningar detta läsår",
    exams: "Kommande prov",
    no_exams: "Inga kommande prov",
    grade: "Vitsord",
    room: "Sal",
    teacher: "Lärare",
    choose_entity: "Välj en entitet i kortets inställningar.",
    not_found: "Entiteten hittades inte: {id}",
    unavailable: "{name} är inte tillgänglig",
    error: "Kortet kunde inte visas",
    overview: "Översikt",
    this_week: "Den här veckan",
    unread_messages: "Olästa meddelanden",
    new_bulletins: "Nya anslag",
    bulletin_title: "Senaste anslaget",
    homework: "Läxor",
    latest_grade: "Senaste provvitsord",
    calendar: "Kalender",
    account: "Wilma-konto",
    problem: "Problem",
    last_update: "Senaste uppdatering",
    no_bulletins: "Inga anslag",
    no_homework: "Inga läxor",
    open_in_wilma: "Öppna i Wilma",
    no_students_title: "Inga elever i Wilma hittades",
    no_students_text:
      "Lägg till Wilma-integrationen under Inställningar → Enheter och tjänster. Eleverna visas här när den har laddats; uppdatera sidan efter att du lagt till den.",
    unknown_students: "Hittades inte bland eleverna i Wilma: {names}",
  },
};

function language(hass) {
  return (
    hass?.locale?.language ||
    hass?.language ||
    (typeof navigator !== "undefined" && navigator.language) ||
    "en"
  );
}

function t(hass, key, vars = {}) {
  const base = language(hass).split("-")[0].toLowerCase();
  const text = STRINGS[base]?.[key] ?? STRINGS.en[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, name) => String(vars[name] ?? ""));
}

/* ---------- Small helpers ---------- */

const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ESCAPES[c]);
}

function safeColor(value) {
  return typeof value === "string" && /^#[0-9a-fA-F]{6}$/.test(value) ? value : null;
}

function safeUrl(value) {
  return typeof value === "string" && /^https?:\/\//i.test(value) ? value : null;
}

function asList(value) {
  return Array.isArray(value) ? value : [];
}

function textList(value) {
  if (typeof value === "string") return value ? [value] : [];
  return asList(value)
    .filter((item) => item !== null && item !== undefined && item !== "")
    .map(String);
}

function present(value) {
  return value !== null && value !== undefined && value !== "";
}

function pad(number) {
  return String(number).padStart(2, "0");
}

/* ---------- Dates and times ---------- */

/* Times follow the user's profile: server or browser time zone, 12 or 24 hours. */
function displayTimeZone(hass) {
  return hass?.locale?.time_zone === "server" ? hass?.config?.time_zone : undefined;
}

function timeOptions(hass) {
  const options = { hour: "2-digit", minute: "2-digit" };
  const format = hass?.locale?.time_format;
  if (format === "12") options.hour12 = true;
  else if (format === "24") options.hourCycle = "h23";
  return options;
}

function format(hass, date, options) {
  try {
    return new Intl.DateTimeFormat(language(hass), options).format(date);
  } catch (err) {
    try {
      const { timeZone, ...rest } = options;
      return new Intl.DateTimeFormat("en", rest).format(date);
    } catch (err2) {
      return date.toISOString();
    }
  }
}

function parseDateTime(value) {
  if (!present(value)) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatTime(hass, value) {
  const date = value instanceof Date ? value : parseDateTime(value);
  if (!date) return "";
  return format(hass, date, { ...timeOptions(hass), timeZone: displayTimeZone(hass) });
}

/* A wall-clock time that is already local to the school, such as "14:05". */
function formatWallTime(hass, hours, minutes) {
  const date = new Date(Date.UTC(2000, 0, 1, hours, minutes));
  return format(hass, date, { ...timeOptions(hass), timeZone: "UTC" });
}

/* Calendar dates ("YYYY-MM-DD") are kept as dates and never shifted by a time zone. */
function dateOnly(iso) {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(typeof iso === "string" ? iso : "");
  return match ? new Date(Date.UTC(+match[1], +match[2] - 1, +match[3], 12)) : null;
}

function formatDate(hass, iso, options) {
  const date = dateOnly(iso);
  return date ? format(hass, date, { ...options, timeZone: "UTC" }) : String(iso ?? "");
}

function isoDateIn(hass, date) {
  try {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone: displayTimeZone(hass),
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).formatToParts(date);
    const get = (type) => parts.find((part) => part.type === type)?.value;
    return `${get("year")}-${get("month")}-${get("day")}`;
  } catch (err) {
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  }
}

function daysBetween(fromIso, toIso) {
  const from = dateOnly(fromIso);
  const to = dateOnly(toIso);
  return from && to ? Math.round((to - from) / 86400000) : null;
}

/* "Today", "Tomorrow", "Yesterday" or a short date such as "Mon 3 Nov". */
function relativeDay(hass, iso, now) {
  const today = isoDateIn(hass, now);
  const diff = daysBetween(today, iso);
  if (diff === 0) return t(hass, "today");
  if (diff === 1) return t(hass, "tomorrow");
  if (diff === -1) return t(hass, "yesterday");
  const options = { weekday: "short", day: "numeric", month: "short" };
  if (dateOnly(iso) && iso.slice(0, 4) !== today.slice(0, 4)) options.year = "numeric";
  return formatDate(hass, iso, options);
}

function relativeTime(hass, value, unit) {
  try {
    return new Intl.RelativeTimeFormat(language(hass), { numeric: "auto" }).format(
      value,
      unit
    );
  } catch (err) {
    return `${value} ${unit}`;
  }
}

/* The school-local date of an ISO datetime with offset, e.g. "2026-11-03T08:15:00+02:00". */
function lessonDate(lesson) {
  const start = typeof lesson?.start === "string" ? lesson.start : "";
  return /^\d{4}-\d{2}-\d{2}/.test(start) ? start.slice(0, 10) : null;
}

/* ---------- Entities ---------- */

function wilmaEntities(hass) {
  return Object.values(hass?.entities || {}).filter(
    (entry) => entry && entry.platform === DOMAIN
  );
}

function findEntity(hass, deviceId, key) {
  if (!deviceId) return undefined;
  const entry = wilmaEntities(hass).find(
    (item) => item.device_id === deviceId && item.translation_key === key
  );
  return entry?.entity_id;
}

/* Entity of the same student (device) as another of their entities. */
function siblingEntity(hass, entityId, key) {
  return findEntity(hass, hass?.entities?.[entityId]?.device_id, key);
}

function deviceName(hass, deviceId) {
  const device = hass?.devices?.[deviceId];
  return device ? device.name_by_user || device.name || "" : "";
}

/* Device IDs of the students, ordered by device name. */
function studentDevices(hass) {
  const ids = new Set();
  for (const entry of wilmaEntities(hass)) {
    if (entry.device_id && STUDENT_KEYS.has(entry.translation_key)) ids.add(entry.device_id);
  }
  return [...ids].sort((a, b) => deviceName(hass, a).localeCompare(deviceName(hass, b)));
}

/* The first student's entities for the given translation keys, for card picker defaults. */
function firstStudentEntities(hass, keys) {
  const deviceId = studentDevices(hass)[0];
  const found = {};
  for (const key of keys) {
    const entityId = findEntity(hass, deviceId, key);
    if (entityId) found[key] = entityId;
  }
  return found;
}

/* The student's first name, from a device called "Wilma {first name}". */
function studentName(hass, entityId) {
  const name = deviceName(hass, hass?.entities?.[entityId]?.device_id);
  return name.replace(/^Wilma\s+/i, "");
}

function friendlyName(hass, entityId) {
  return hass?.states?.[entityId]?.attributes?.friendly_name || entityId;
}

/* A message explaining why an entity can't be shown, or null when it can. */
function entityProblem(hass, entityId) {
  if (!entityId) return t(hass, "choose_entity");
  const state = hass?.states?.[entityId];
  if (!state) return t(hass, "not_found", { id: entityId });
  if (state.state === "unavailable") {
    return t(hass, "unavailable", { name: friendlyName(hass, entityId) });
  }
  return null;
}

function attributes(hass, entityId) {
  const state = entityId ? hass?.states?.[entityId] : undefined;
  return state && state.state !== "unavailable" ? state.attributes || {} : null;
}

/* ---------- Shared markup ---------- */

function icon(name, extraClass = "") {
  return `<ha-icon class="icon ${extraClass}" icon="${esc(name)}" aria-hidden="true"></ha-icon>`;
}

function srOnly(text) {
  return `<span class="sr">${esc(text)}</span>`;
}

function warning(text) {
  return `<div class="warning" role="status">${icon("mdi:alert-circle-outline")}<span>${esc(
    text
  )}</span></div>`;
}

function empty(text) {
  return `<div class="empty">${esc(text)}</div>`;
}

function header(title, subtitle) {
  if (!present(title) && !present(subtitle)) return "";
  return `<div class="header">${present(title) ? `<h2 class="title">${esc(title)}</h2>` : ""}${
    present(subtitle) ? `<span class="subtitle">${esc(subtitle)}</span>` : ""
  }</div>`;
}

/* A mark type's colour next to its code or description, so colour is never the only cue. */
function chip(color, label, description) {
  const swatch = safeColor(color);
  const title = present(description) && description !== label ? ` title="${esc(description)}"` : "";
  return `<span class="chip"${title}><span class="swatch${
    swatch ? "" : " no-color"
  }" style="background:${swatch || "transparent"}" aria-hidden="true"></span><span>${esc(
    label
  )}</span></span>`;
}

function meta(parts) {
  const items = parts.filter((part) => present(part?.text));
  if (!items.length) return "";
  return `<div class="meta">${items
    .map(
      (part) =>
        `<span class="meta-item">${part.icon ? icon(part.icon, "small") : ""}${
          part.label ? srOnly(`${part.label}: `) : ""
        }${esc(part.text)}</span>`
    )
    .join("")}</div>`;
}

function datetimeAttr(value) {
  return present(value) ? ` datetime="${esc(value)}"` : "";
}

const BASE_CSS = `
  :host { display: block; }
  ha-card { height: 100%; box-sizing: border-box; overflow: hidden; color: var(--primary-text-color); }
  .header {
    display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between;
    gap: 4px 12px; padding: 16px 16px 0;
  }
  .title {
    margin: 0; font-size: var(--ha-card-header-font-size, 1.5rem); font-weight: 400;
    line-height: 1.3; color: var(--ha-card-header-color, var(--primary-text-color));
    overflow-wrap: anywhere;
  }
  .subtitle { color: var(--secondary-text-color); font-size: 0.875rem; }
  .content { padding: 8px 16px 16px; }
  .list { list-style: none; margin: 0; padding: 0; }
  .empty { color: var(--secondary-text-color); padding: 8px 0; }
  .warning {
    display: flex; gap: 8px; align-items: flex-start; padding: 8px 12px; margin: 8px 0;
    border-inline-start: 4px solid var(--warning-color, #ffa600); border-radius: 4px;
    background: var(--secondary-background-color, transparent);
  }
  .icon { --mdc-icon-size: 20px; color: var(--secondary-text-color); flex: none; }
  .icon.small { --mdc-icon-size: 16px; }
  .sr {
    position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden;
    clip: rect(0 0 0 0); white-space: nowrap; border: 0;
  }
  .meta {
    display: flex; flex-wrap: wrap; gap: 2px 12px; color: var(--secondary-text-color);
    font-size: 0.875rem;
  }
  .meta-item { display: inline-flex; align-items: center; gap: 4px; overflow-wrap: anywhere; }
  .chip {
    display: inline-flex; align-items: center; gap: 6px; max-width: 100%;
    padding: 1px 8px 1px 4px; border: 1px solid var(--divider-color); border-radius: 12px;
    font-size: 0.8125rem; line-height: 1.4; vertical-align: middle;
  }
  .chip > span:last-child { overflow-wrap: anywhere; }
  .swatch {
    flex: none; width: 12px; height: 12px; border-radius: 50%;
    border: 1px solid var(--divider-color); box-sizing: border-box;
  }
  .badge {
    display: inline-block; padding: 0 8px; border-radius: 10px; font-size: 0.75rem;
    font-weight: 500; line-height: 1.5; vertical-align: middle;
    background: var(--primary-color); color: var(--text-primary-color, #fff);
  }
  .badge.outline {
    background: transparent; color: var(--primary-text-color);
    border: 1px solid var(--divider-color);
  }
  a { color: var(--primary-color); }
`;

/* ---------- Base card ---------- */

class WilmaCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = undefined;
    this._hass = undefined;
    this._html = "";
    this._timer = undefined;
  }

  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("Invalid configuration");
    this.validateConfig(config);
    this._config = { ...config };
    this._update();
  }

  /* Throws for options that can never work; missing entities are shown in the card. */
  validateConfig(_config) {}

  set hass(hass) {
    const previous = this._hass;
    this._hass = hass;
    if (!previous || this._changed(previous, hass)) this._update();
  }

  get hass() {
    return this._hass;
  }

  connectedCallback() {
    if (!this._timer) this._timer = setInterval(() => this._update(), TICK_MS);
    this._update();
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    this._timer = undefined;
  }

  /* The entity IDs the card displays; it re-renders when any of their states change. */
  entityIds() {
    return [];
  }

  /* A configured entity, or the student's entity with the given translation key. */
  resolve(option, key) {
    const configured = this._config?.[option];
    if (configured) return configured;
    return findEntity(this._hass, this._config?.student, key);
  }

  _changed(previous, hass) {
    if (
      previous.locale !== hass.locale ||
      previous.language !== hass.language ||
      previous.entities !== hass.entities ||
      previous.devices !== hass.devices
    ) {
      return true;
    }
    return this.entityIds().some((id) => previous.states?.[id] !== hass.states?.[id]);
  }

  _update() {
    if (!this._config || !this._hass) return;
    let body;
    try {
      body = this.renderCard(new Date());
    } catch (err) {
      console.error("Wilma card failed to render", err);
      body = `<ha-card><div class="content">${warning(t(this._hass, "error"))}</div></ha-card>`;
    }
    const html = `<style>${BASE_CSS}${this.constructor.styles || ""}</style>${body}`;
    if (html !== this._html) {
      this._html = html;
      this.shadowRoot.innerHTML = html;
    }
  }

  renderCard(_now) {
    return "";
  }

  getCardSize() {
    if (!this._config) return 3;
    try {
      return this.cardSize();
    } catch (err) {
      return 3;
    }
  }

  cardSize() {
    return 3;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }
}

function card(content, title, subtitle) {
  return `<ha-card>${header(title, subtitle)}<div class="content">${content}</div></ha-card>`;
}

function titleWithStudent(hass, title, entityId) {
  const name = studentName(hass, entityId);
  return name ? `${title} · ${name}` : title;
}

/* ---------- Schedule ---------- */

function lessonStatus(lesson, now) {
  const start = parseDateTime(lesson.start);
  const end = parseDateTime(lesson.end);
  if (end && now >= end) return "past";
  if (start && now >= start) return "now";
  return "future";
}

function renderLesson(hass, lesson, now, config) {
  const status = lessonStatus(lesson, now);
  const start = formatTime(hass, lesson.start);
  const end = formatTime(hass, lesson.end);
  const subject = present(lesson.subject) ? lesson.subject : "—";
  const details = [];
  if (config.show_rooms !== false) {
    details.push({ icon: "mdi:door", label: t(hass, "room"), text: textList(lesson.rooms).join(", ") });
  }
  if (config.show_teachers !== false) {
    details.push({
      icon: "mdi:account",
      label: t(hass, "teacher"),
      text: textList(lesson.teachers).join(", "),
    });
  }
  return `<li class="lesson ${status}"${status === "now" ? ' aria-current="time"' : ""}>
    <div class="time"><time${datetimeAttr(lesson.start)}>${esc(start)}</time><span class="sr"> – </span><time${datetimeAttr(
      lesson.end
    )}>${esc(end)}</time></div>
    <div class="body">
      <div class="subject">${esc(subject)}${
        status === "now" ? ` <span class="badge">${esc(t(hass, "now"))}</span>` : ""
      }${status === "past" ? srOnly(` (${t(hass, "ended")})`) : ""}</div>
      ${meta(details)}
    </div>
    ${status === "past" ? icon("mdi:check", "done") : ""}
  </li>`;
}

function renderLessonList(hass, lessons, now, config) {
  if (!lessons.length) return empty(t(hass, "no_lessons"));
  return `<ul class="list lessons">${lessons
    .map((lesson) => renderLesson(hass, lesson, now, config))
    .join("")}</ul>`;
}

function sortLessons(lessons) {
  return asList(lessons)
    .filter((lesson) => lesson && typeof lesson === "object")
    .slice()
    .sort((a, b) => String(a.start ?? "").localeCompare(String(b.start ?? "")));
}

function addDays(iso, days) {
  const date = dateOnly(iso);
  if (!date) return null;
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

class WilmaScheduleCard extends WilmaCard {
  static styles = `
    .lesson {
      display: grid; grid-template-columns: auto 1fr auto; gap: 12px; align-items: center;
      padding: 8px; margin: 2px 0; border-radius: 8px;
      border-inline-start: 4px solid transparent;
    }
    .lesson .time {
      display: flex; flex-direction: column; min-width: 3.25rem; font-variant-numeric: tabular-nums;
      font-size: 0.875rem; line-height: 1.3;
    }
    .lesson .time time + time { color: var(--secondary-text-color); }
    .lesson .subject { font-weight: 500; overflow-wrap: anywhere; }
    .lesson.past .subject, .lesson.past .time time:first-child { color: var(--secondary-text-color); font-weight: 400; }
    .lesson.now {
      border-inline-start-color: var(--primary-color);
      background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.12);
    }
    .lesson .done { --mdc-icon-size: 18px; }
    .day + .day { margin-top: 12px; }
    .day-title {
      display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 8px;
      margin: 0 0 4px; padding-bottom: 4px; font-size: 1rem; font-weight: 500;
      border-bottom: 1px solid var(--divider-color);
    }
    .day-title .date { color: var(--secondary-text-color); font-weight: 400; font-size: 0.875rem; }
    .day.past .day-title { color: var(--secondary-text-color); }
  `;

  static getStubConfig(hass) {
    const found = firstStudentEntities(hass, ["lessons_today"]);
    return { entity: found.lessons_today || "", mode: "day" };
  }

  static getConfigForm() {
    return {
      schema: [
        { name: "entity", selector: { entity: { filter: { integration: DOMAIN, domain: "sensor" } } } },
        {
          name: "mode",
          selector: {
            select: {
              mode: "dropdown",
              options: [
                { value: "day", label: "Day" },
                { value: "week", label: "Week" },
              ],
            },
          },
        },
        { name: "title", selector: { text: {} } },
        { name: "show_rooms", selector: { boolean: {} } },
        { name: "show_teachers", selector: { boolean: {} } },
        { name: "hide_past_days", selector: { boolean: {} } },
      ],
      computeLabel: (item) => t(undefined, item.name),
    };
  }

  validateConfig(config) {
    if (config.mode !== undefined && !["day", "week"].includes(config.mode)) {
      throw new Error("mode must be 'day' or 'week'");
    }
    if (config.day !== undefined && !["today", "tomorrow"].includes(config.day)) {
      throw new Error("day must be 'today' or 'tomorrow'");
    }
  }

  get mode() {
    if (this._config.mode) return this._config.mode;
    const key = this._hass?.entities?.[this._config.entity]?.translation_key;
    return key === "lessons_this_week" ? "week" : "day";
  }

  entityIds() {
    const config = this._config;
    if (config.entity) return [config.entity];
    if (this.mode === "week") return [this.resolve("entity", "lessons_this_week")].filter(Boolean);
    const key = config.day === "tomorrow" ? "lessons_tomorrow" : "lessons_today";
    return [this.resolve("entity", key)].filter(Boolean);
  }

  renderCard(now) {
    const hass = this._hass;
    const entityId = this.entityIds()[0];
    const baseTitle = present(this._config.title)
      ? this._config.title
      : titleWithStudent(hass, t(hass, "schedule"), entityId);
    const problem = entityProblem(hass, entityId);
    if (problem) return card(warning(problem), baseTitle);

    const attrs = attributes(hass, entityId);
    const lessons = sortLessons(attrs.lessons);
    return this.mode === "week"
      ? this._renderWeek(attrs, lessons, now, baseTitle)
      : this._renderDay(attrs, lessons, now, baseTitle);
  }

  _renderDay(attrs, lessons, now, title) {
    const hass = this._hass;
    // A week sensor shown in day mode shows today's part of the week
    const day = dateOnly(attrs.date) ? attrs.date : isoDateIn(hass, now);
    const ofDay = dateOnly(attrs.date) ? lessons : lessons.filter((l) => lessonDate(l) === day);
    const relative = relativeDay(hass, day, now);
    const full = formatDate(hass, day, { weekday: "long", day: "numeric", month: "long" });
    const subtitle = relative === t(hass, "today") || relative === t(hass, "tomorrow")
      ? `${relative} · ${full}`
      : full;
    return card(renderLessonList(hass, ofDay, now, this._config), title, subtitle);
  }

  _renderWeek(attrs, lessons, now, title) {
    const hass = this._hass;
    const byDay = new Map();
    for (const lesson of lessons) {
      const day = lessonDate(lesson);
      if (!day) continue;
      if (!byDay.has(day)) byDay.set(day, []);
      byDay.get(day).push(lesson);
    }
    const days = [];
    const first = dateOnly(attrs.week_start) ? attrs.week_start : [...byDay.keys()].sort()[0];
    const last = dateOnly(attrs.week_end) ? attrs.week_end : [...byDay.keys()].sort().pop();
    if (first && last) {
      for (let day = first, n = 0; day && day <= last && n < 14; day = addDays(day, 1), n++) {
        const weekday = dateOnly(day).getUTCDay();
        // Weekends only appear when they have lessons
        if (byDay.has(day) || (weekday !== 0 && weekday !== 6)) days.push(day);
      }
    }
    const today = isoDateIn(hass, now);
    const sections = days
      .filter((day) => !(this._config.hide_past_days && day < today))
      .map((day) => {
        const isToday = day === today;
        const state = isToday ? "today" : day < today ? "past" : "future";
        return `<section class="day ${state}"${isToday ? ' aria-current="date"' : ""}>
          <h3 class="day-title"><span>${esc(
            formatDate(hass, day, { weekday: "long" })
          )}</span><span class="date">${esc(
            formatDate(hass, day, { day: "numeric", month: "short" })
          )}</span>${isToday ? `<span class="badge outline">${esc(t(hass, "today"))}</span>` : ""}</h3>
          ${renderLessonList(hass, byDay.get(day) || [], now, this._config)}
        </section>`;
      })
      .join("");
    const subtitle =
      first && last
        ? `${formatDate(hass, first, { day: "numeric", month: "short" })} – ${formatDate(hass, last, {
            day: "numeric",
            month: "short",
          })}`
        : "";
    return card(sections || empty(t(hass, "no_lessons")), title, subtitle);
  }

  cardSize() {
    const attrs = attributes(this._hass, this.entityIds()[0]);
    const count = asList(attrs?.lessons).length;
    return this.mode === "week" ? Math.max(4, 2 + Math.ceil(count / 1.5)) : 2 + count;
  }
}

/* ---------- Next lesson ---------- */

class WilmaNextLessonCard extends WilmaCard {
  static styles = `
    .tile { display: flex; gap: 16px; align-items: center; padding: 16px; }
    .tile-icon {
      flex: none; display: flex; align-items: center; justify-content: center;
      width: 44px; height: 44px; border-radius: 50%;
      background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.15);
    }
    .tile-icon .icon { color: var(--primary-color); --mdc-icon-size: 24px; }
    .info { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 2px; }
    .label { color: var(--secondary-text-color); font-size: 0.875rem; }
    .subject { font-size: 1.25rem; font-weight: 500; line-height: 1.3; overflow-wrap: anywhere; }
    .when { font-size: 0.9375rem; }
    .when strong { font-weight: 500; }
    .tile .warning { margin: 0; flex: 1; }
  `;

  static getStubConfig(hass) {
    return { entity: firstStudentEntities(hass, ["next_lesson"]).next_lesson || "" };
  }

  static getConfigForm() {
    return {
      schema: [
        { name: "entity", selector: { entity: { filter: { integration: DOMAIN, domain: "sensor" } } } },
        { name: "title", selector: { text: {} } },
      ],
      computeLabel: (item) => t(undefined, item.name),
    };
  }

  entityIds() {
    return [this.resolve("entity", "next_lesson")].filter(Boolean);
  }

  renderCard(now) {
    const hass = this._hass;
    const entityId = this.entityIds()[0];
    const label = present(this._config.title)
      ? this._config.title
      : titleWithStudent(hass, t(hass, "next_lesson"), entityId);
    const problem = entityProblem(hass, entityId);
    const attrs = problem ? null : attributes(hass, entityId);
    const subject = attrs?.subject ?? hass.states[entityId]?.state;
    let info;
    if (problem) {
      info = warning(problem);
    } else if (!present(subject) || subject === "unknown") {
      info = `<div class="info"><div class="label">${esc(label)}</div><div class="when">${esc(
        t(hass, "no_next_lesson")
      )}</div></div>`;
    } else {
      const start = parseDateTime(attrs.start);
      const end = parseDateTime(attrs.end);
      const range = [formatTime(hass, start), formatTime(hass, end)].filter(Boolean).join("–");
      let when = "";
      if (start) {
        const minutes = Math.ceil((start - now) / 60000);
        if (minutes <= 0 && (!end || now < end)) when = t(hass, "started");
        else if (minutes > 0 && minutes < 90) when = relativeTime(hass, minutes, "minute");
        else when = relativeDay(hass, attrs.date || lessonDate(attrs) || isoDateIn(hass, start), now);
      }
      info = `<div class="info">
        <div class="label">${esc(label)}</div>
        <div class="subject">${esc(subject)}</div>
        <div class="when">${when ? `<strong>${esc(when)}</strong>` : ""}${
          when && range ? " · " : ""
        }${range ? `<time${datetimeAttr(attrs.start)}>${esc(range)}</time>` : ""}</div>
        ${meta([
          { icon: "mdi:door", label: t(hass, "room"), text: textList(attrs.rooms).join(", ") },
          { icon: "mdi:account", label: t(hass, "teacher"), text: textList(attrs.teachers).join(", ") },
        ])}
      </div>`;
    }
    return `<ha-card><div class="tile"><div class="tile-icon">${icon("mdi:school")}</div>${info}</div></ha-card>`;
  }

  cardSize() {
    return 2;
  }

  getGridOptions() {
    return { columns: 6, min_columns: 4 };
  }
}

/* ---------- Activity ---------- */

function messageItems(attrs) {
  if (!attrs) return [];
  let messages = asList(attrs.recent_messages);
  if (!messages.length && (present(attrs.subject) || present(attrs.id))) {
    messages = [{ id: attrs.id, subject: attrs.subject, sender: attrs.sender, timestamp: attrs.timestamp }];
  }
  return messages
    .filter((m) => m && typeof m === "object")
    .map((m) => {
      const match = /^(\d{4}-\d{2}-\d{2})[ T](\d{2}):(\d{2})/.exec(String(m.timestamp ?? ""));
      return {
        kind: "message",
        id: `message-${m.id ?? m.subject}`,
        sort: match ? `${match[1]}T${match[2]}:${match[3]}` : "",
        date: match?.[1],
        hours: match ? +match[2] : null,
        minutes: match ? +match[3] : null,
        data: m,
      };
    });
}

function markItems(attrs, fallback) {
  let marks = asList(attrs?.recent_marks);
  if (!marks.length && fallback && (present(fallback.code) || present(fallback.description))) {
    marks = [fallback];
  }
  return marks
    .filter((m) => m && typeof m === "object")
    .map((m, index) => {
      const hour = Number.isInteger(m.hour) ? m.hour : null;
      return {
        kind: "mark",
        id: `mark-${m.date}-${m.hour}-${m.code}-${m.course}-${index}`,
        sort: dateOnly(m.date) ? `${m.date.slice(0, 10)}T${pad(hour ?? 0)}:00` : "",
        date: m.date,
        hours: hour,
        minutes: hour === null ? null : 0,
        data: m,
      };
    });
}

function bulletinItems(attrs) {
  if (!attrs) return [];
  let bulletins = asList(attrs.recent_bulletins);
  if (!bulletins.length && (present(attrs.title) || present(attrs.id))) {
    bulletins = [{ id: attrs.id, title: attrs.title, date: attrs.date, author: attrs.author, url: attrs.url }];
  }
  return bulletins
    .filter((b) => b && typeof b === "object")
    .map((b) => ({
      kind: "bulletin",
      id: `bulletin-${b.id ?? b.title}`,
      sort: dateOnly(b.date) ? `${String(b.date).slice(0, 10)}T00:00` : "",
      date: b.date,
      hours: null,
      minutes: null,
      data: b,
    }));
}

function whenText(hass, item, now) {
  if (!dateOnly(item.date)) return "";
  const day = relativeDay(hass, item.date, now);
  return item.hours === null ? day : `${day} ${formatWallTime(hass, item.hours, item.minutes)}`;
}

function renderMark(hass, mark, when) {
  const code = present(mark.code) ? mark.code : mark.description;
  const description = present(mark.description) && mark.description !== code ? mark.description : "";
  return `<li class="item mark">
    ${icon("mdi:clipboard-text-outline")}
    <div class="body">
      <div class="line">${srOnly(`${t(hass, "mark")}: `)}${chip(mark.color, code ?? "—", mark.description)}${
        description ? ` <span class="text">${esc(description)}</span>` : ""
      }</div>
      ${meta([
        { icon: "mdi:account", label: t(hass, "teacher"), text: mark.teacher },
        { text: mark.course },
        { text: when },
      ])}
      ${present(mark.comment) ? `<div class="comment">${esc(mark.comment)}</div>` : ""}
    </div>
  </li>`;
}

function renderActivityItem(hass, item, now) {
  const when = whenText(hass, item, now);
  const data = item.data;
  if (item.kind === "mark") return renderMark(hass, data, when);
  if (item.kind === "message") {
    return `<li class="item message${data.unread ? " unread" : ""}">
      ${icon(data.unread ? "mdi:email" : "mdi:email-open-outline")}
      <div class="body">
        <div class="line">${srOnly(`${t(hass, "message")}: `)}<span class="text">${esc(
          data.subject ?? "—"
        )}</span>${data.unread ? ` <span class="badge">${esc(t(hass, "unread"))}</span>` : ""}</div>
        ${meta([{ icon: "mdi:account", text: data.sender }, { text: when }])}
      </div>
    </li>`;
  }
  const url = safeUrl(data.url);
  const title = esc(data.title ?? "—");
  return `<li class="item bulletin">
    ${icon("mdi:bulletin-board")}
    <div class="body">
      <div class="line">${srOnly(`${t(hass, "bulletin")}: `)}<span class="text">${
        url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${title}</a>` : title
      }</span></div>
      ${meta([{ icon: "mdi:account", text: data.author }, { text: when }])}
    </div>
  </li>`;
}

const ACTIVITY_CSS = `
  .item {
    display: grid; grid-template-columns: auto 1fr; gap: 12px; align-items: start;
    padding: 8px 0;
  }
  .item + .item { border-top: 1px solid var(--divider-color); }
  .item > .icon { margin-top: 2px; }
  .body { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  .line { overflow-wrap: anywhere; }
  .item.unread .text { font-weight: 600; }
  .comment { font-size: 0.875rem; overflow-wrap: anywhere; }
  .comment::before { content: "“"; }
  .comment::after { content: "”"; }
`;

const ACTIVITY_KEYS = ["latest_message", "attendance_count", "latest_bulletin"];

class WilmaActivityCard extends WilmaCard {
  static styles = ACTIVITY_CSS;

  static getStubConfig(hass) {
    return { ...firstStudentEntities(hass, ACTIVITY_KEYS), max_items: 10 };
  }

  static getConfigForm() {
    const entity = { entity: { filter: { integration: DOMAIN, domain: "sensor" } } };
    return {
      schema: [
        { name: "latest_message", selector: entity },
        { name: "attendance_count", selector: entity },
        { name: "latest_bulletin", selector: entity },
        { name: "max_items", selector: { number: { min: 1, max: 50, mode: "box" } } },
        { name: "title", selector: { text: {} } },
      ],
      computeLabel: (item) => t(undefined, item.name),
    };
  }

  validateConfig(config) {
    if (config.max_items !== undefined && !(Number.isInteger(config.max_items) && config.max_items > 0)) {
      throw new Error("max_items must be a positive whole number");
    }
  }

  _entities() {
    const found = {};
    for (const key of ACTIVITY_KEYS) found[key] = this.resolve(key, key);
    // Without the recent marks list, the latest mark sensor of the same student stands in
    found.latest_attendance_mark =
      this._config.latest_attendance_mark ||
      siblingEntity(this._hass, found.attendance_count, "latest_attendance_mark") ||
      findEntity(this._hass, this._config.student, "latest_attendance_mark");
    return found;
  }

  entityIds() {
    return Object.values(this._entities()).filter(Boolean);
  }

  renderCard(now) {
    const hass = this._hass;
    const entities = this._entities();
    const anyEntity = entities.latest_message || entities.attendance_count || entities.latest_bulletin;
    const title = present(this._config.title)
      ? this._config.title
      : titleWithStudent(hass, t(hass, "activity"), anyEntity);
    if (!anyEntity) return card(warning(t(hass, "choose_entity")), title);

    const problems = ACTIVITY_KEYS.filter((key) => entities[key])
      .map((key) => entityProblem(hass, entities[key]))
      .filter(Boolean);
    const items = [
      ...messageItems(attributes(hass, entities.latest_message)),
      ...markItems(
        attributes(hass, entities.attendance_count),
        attributes(hass, entities.latest_attendance_mark)
      ),
      ...bulletinItems(attributes(hass, entities.latest_bulletin)),
    ];
    const seen = new Set();
    const unique = items.filter((item) => !seen.has(item.id) && seen.add(item.id));
    unique.sort((a, b) => b.sort.localeCompare(a.sort));
    const shown = unique.slice(0, this._config.max_items ?? 10);
    const list = shown.length
      ? `<ul class="list">${shown.map((item) => renderActivityItem(hass, item, now)).join("")}</ul>`
      : empty(t(hass, "no_activity"));
    return card(problems.map(warning).join("") + list, title);
  }

  cardSize() {
    return 1 + Math.min(this._config?.max_items ?? 10, 10);
  }
}

/* ---------- Attendance marks ---------- */

function markTypes(attrs) {
  const types = asList(attrs?.types).filter((type) => type && typeof type === "object");
  if (types.length) return types;
  // Without the types list, the counts by description stand in, without colours
  return Object.entries(attrs?.by_type || {})
    .map(([description, count]) => ({ description, code: null, color: null, count }))
    .sort((a, b) => (Number(b.count) || 0) - (Number(a.count) || 0));
}

class WilmaMarksCard extends WilmaCard {
  static styles = `
    ${ACTIVITY_CSS}
    .type {
      display: grid; grid-template-columns: auto 1fr auto; gap: 4px 10px; align-items: center;
      padding: 6px 0;
    }
    .type .name { min-width: 0; overflow-wrap: anywhere; }
    .type .code { font-weight: 500; }
    .type .description { color: var(--secondary-text-color); font-size: 0.875rem; }
    .type .count { font-weight: 500; font-variant-numeric: tabular-nums; }
    .bar {
      grid-column: 2 / 4; height: 6px; border-radius: 3px; overflow: hidden;
      background: var(--divider-color);
    }
    .bar > span { display: block; height: 100%; border-radius: 3px; }
    h3 { margin: 16px 0 0; font-size: 1rem; font-weight: 500; }
  `;

  static getStubConfig(hass) {
    return {
      entity: firstStudentEntities(hass, ["attendance_count"]).attendance_count || "",
      recent: 3,
    };
  }

  static getConfigForm() {
    return {
      schema: [
        { name: "entity", selector: { entity: { filter: { integration: DOMAIN, domain: "sensor" } } } },
        { name: "recent", selector: { number: { min: 0, max: 10, mode: "box" } } },
        { name: "title", selector: { text: {} } },
      ],
      computeLabel: (item) => t(undefined, item.name),
    };
  }

  validateConfig(config) {
    if (config.recent !== undefined && !(Number.isInteger(config.recent) && config.recent >= 0)) {
      throw new Error("recent must be a whole number, 0 or more");
    }
  }

  _entities() {
    const entity = this.resolve("entity", "attendance_count");
    return {
      entity,
      latest:
        siblingEntity(this._hass, entity, "latest_attendance_mark") ||
        findEntity(this._hass, this._config.student, "latest_attendance_mark"),
    };
  }

  entityIds() {
    return Object.values(this._entities()).filter(Boolean);
  }

  renderCard(now) {
    const hass = this._hass;
    const { entity, latest } = this._entities();
    const title = present(this._config.title)
      ? this._config.title
      : titleWithStudent(hass, t(hass, "marks"), entity);
    const problem = entityProblem(hass, entity);
    if (problem) return card(warning(problem), title);

    const attrs = attributes(hass, entity);
    const total = Number(hass.states[entity].state);
    const types = markTypes(attrs).filter((type) => Number(type.count) > 0);
    const max = Math.max(1, ...types.map((type) => Number(type.count) || 0));
    const rows = types
      .map((type) => {
        const code = present(type.code) ? type.code : type.description;
        const description =
          present(type.description) && type.description !== code ? type.description : "";
        const color = safeColor(type.color);
        const width = Math.round(((Number(type.count) || 0) / max) * 100);
        return `<li class="type">
          <span class="swatch${color ? "" : " no-color"}" style="background:${
            color || "transparent"
          }" aria-hidden="true"></span>
          <span class="name"><span class="code">${esc(code)}</span>${
            description ? ` <span class="description">${esc(description)}</span>` : ""
          }</span>
          <span class="count">${esc(type.count)}</span>
          <span class="bar" aria-hidden="true"><span style="width:${width}%;background:${
            color || "var(--primary-color)"
          }"></span></span>
        </li>`;
      })
      .join("");
    let content = rows ? `<ul class="list">${rows}</ul>` : empty(t(hass, "no_marks"));

    const recentCount = this._config.recent ?? 3;
    if (recentCount > 0) {
      const marks = markItems(attrs, attributes(hass, latest)).slice(0, recentCount);
      if (marks.length) {
        content += `<h3>${esc(t(hass, "latest_marks"))}</h3><ul class="list">${marks
          .map((item) => renderMark(hass, item.data, whenText(hass, item, now)))
          .join("")}</ul>`;
      }
    }
    const subtitle = Number.isFinite(total) ? t(hass, "marks_total", { count: total }) : "";
    return card(content, title, subtitle);
  }

  cardSize() {
    const attrs = attributes(this._hass, this._entities().entity);
    return 2 + markTypes(attrs).length + (this._config?.recent ?? 3);
  }
}

/* ---------- Exams ---------- */

class WilmaExamsCard extends WilmaCard {
  static styles = `
    .exam {
      display: grid; grid-template-columns: auto 1fr; gap: 12px; align-items: start;
      padding: 8px 0;
    }
    .exam + .exam { border-top: 1px solid var(--divider-color); }
    .date-box {
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      min-width: 3rem; padding: 4px; border-radius: 8px; line-height: 1.15;
      border: 1px solid var(--divider-color); text-align: center;
    }
    .date-box .dow, .date-box .month { font-size: 0.75rem; color: var(--secondary-text-color); text-transform: uppercase; }
    .date-box .dom { font-size: 1.25rem; font-weight: 500; }
    .exam.soon .date-box { border-color: var(--primary-color); border-width: 2px; }
    .body { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
    .subject { font-weight: 500; overflow-wrap: anywhere; }
    .when, .name { font-size: 0.875rem; }
    .name { color: var(--secondary-text-color); overflow-wrap: anywhere; }
    .info { font-size: 0.875rem; overflow-wrap: anywhere; white-space: pre-line; }
  `;

  static getStubConfig(hass) {
    const found = firstStudentEntities(hass, ["upcoming_exams", "next_exam"]);
    return { entity: found.upcoming_exams || found.next_exam || "", max_items: 5 };
  }

  static getConfigForm() {
    return {
      schema: [
        { name: "entity", selector: { entity: { filter: { integration: DOMAIN, domain: "sensor" } } } },
        { name: "max_items", selector: { number: { min: 1, max: 30, mode: "box" } } },
        { name: "title", selector: { text: {} } },
      ],
      computeLabel: (item) => t(undefined, item.name),
    };
  }

  validateConfig(config) {
    if (config.max_items !== undefined && !(Number.isInteger(config.max_items) && config.max_items > 0)) {
      throw new Error("max_items must be a positive whole number");
    }
  }

  entityIds() {
    return [
      this.resolve("entity", "upcoming_exams") || findEntity(this._hass, this._config.student, "next_exam"),
    ].filter(Boolean);
  }

  renderCard(now) {
    const hass = this._hass;
    const entityId = this.entityIds()[0];
    const title = present(this._config.title)
      ? this._config.title
      : titleWithStudent(hass, t(hass, "exams"), entityId);
    const problem = entityProblem(hass, entityId);
    if (problem) return card(warning(problem), title);

    const attrs = attributes(hass, entityId);
    let exams = asList(attrs.exams).filter((exam) => exam && typeof exam === "object");
    // A single-exam sensor (next exam) has the exam's fields as its attributes
    if (!Array.isArray(attrs.exams) && present(attrs.subject) && present(attrs.date)) {
      exams = [attrs];
    }
    const today = isoDateIn(hass, now);
    const upcoming = exams
      .filter((exam) => !dateOnly(exam.date) || String(exam.date).slice(0, 10) >= today)
      .sort((a, b) => String(a.date ?? "").localeCompare(String(b.date ?? "")))
      .slice(0, this._config.max_items ?? 5);
    if (!upcoming.length) return card(empty(t(hass, "no_exams")), title);

    const rows = upcoming
      .map((exam) => {
        const days = daysBetween(today, exam.date);
        const when = days === null ? "" : relativeTime(hass, days, "day");
        const grade = present(exam.grade)
          ? ` <span class="badge outline">${esc(t(hass, "grade"))}: ${esc(exam.grade)}</span>`
          : "";
        return `<li class="exam${days !== null && days <= 1 ? " soon" : ""}">
          <time class="date-box"${datetimeAttr(exam.date)}>${
            dateOnly(exam.date)
              ? `<span class="dow">${esc(formatDate(hass, exam.date, { weekday: "short" }))}</span>
                 <span class="dom">${esc(formatDate(hass, exam.date, { day: "numeric" }))}</span>
                 <span class="month">${esc(formatDate(hass, exam.date, { month: "short" }))}</span>`
              : `<span class="dom">?</span>`
          }</time>
          <div class="body">
            <div class="subject">${esc(exam.subject ?? "—")}${grade}</div>
            ${present(exam.name) && exam.name !== exam.subject ? `<div class="name">${esc(exam.name)}</div>` : ""}
            ${when ? `<div class="when">${esc(when)}</div>` : ""}
            ${present(exam.info) ? `<div class="info">${esc(exam.info)}</div>` : ""}
            ${meta([{ icon: "mdi:account", label: t(hass, "teacher"), text: textList(exam.teachers).join(", ") }])}
          </div>
        </li>`;
      })
      .join("");
    return card(`<ul class="list">${rows}</ul>`, title);
  }

  cardSize() {
    const attrs = attributes(this._hass, this.entityIds()[0]);
    return 1 + 2 * Math.min(asList(attrs?.exams).length || 1, this._config?.max_items ?? 5);
  }
}

/* ---------- Dashboard strategy ---------- */

const DASHBOARD_DOCS_URL = "https://github.com/frwickst/wilma_ha#dashboard";

/* Parts of the generated dashboard that the `hide` option can leave out. */
const HIDEABLE = [
  "overview",
  "badges",
  "today",
  "week",
  "activity",
  "marks",
  "exams",
  "bulletins",
  "homework",
  "calendar",
  "account",
];

const ACCOUNT_KEYS = ["last_update", "problem"];
const FULL_WIDTH = { columns: 12 };
const HALF_WIDTH = { columns: 6 };

/* Throws for options that can never work, so a typo is reported instead of ignored. */
function strategyOptions(config) {
  const options = config && typeof config === "object" ? config : {};
  const { students, hide } = options;
  if (students !== undefined && !(Array.isArray(students) && students.every((s) => typeof s === "string"))) {
    throw new Error("Wilma dashboard: students must be a list of device IDs or first names");
  }
  if (hide !== undefined && !(Array.isArray(hide) && hide.every((h) => typeof h === "string"))) {
    throw new Error(`Wilma dashboard: hide must be a list of: ${HIDEABLE.join(", ")}`);
  }
  const unknown = asList(hide).filter((part) => !HIDEABLE.includes(part));
  if (unknown.length) {
    throw new Error(
      `Wilma dashboard: unknown hide value ${unknown.join(", ")}; use any of ${HIDEABLE.join(", ")}`
    );
  }
  return { students, hide: new Set(asList(hide)) };
}

function slug(text) {
  return String(text ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function firstName(hass, deviceId) {
  return deviceName(hass, deviceId).replace(/^Wilma\s+/i, "") || deviceId;
}

/* Every Wilma entity of a device, by translation key. */
function deviceEntities(hass, deviceId) {
  const found = {};
  for (const entry of wilmaEntities(hass)) {
    if (entry.device_id === deviceId && entry.translation_key && !found[entry.translation_key]) {
      found[entry.translation_key] = entry.entity_id;
    }
  }
  return found;
}

/*
 * The students to show, in order: those listed in `students` (by device ID or first name)
 * or else every student, ordered by name. View paths are unique and readable.
 */
function selectStudents(hass, selection) {
  const all = studentDevices(hass);
  let ids = all;
  const missing = [];
  if (selection !== undefined) {
    ids = [];
    for (const wanted of selection) {
      const id =
        all.find((deviceId) => deviceId === wanted) ||
        all.find((deviceId) => firstName(hass, deviceId).toLowerCase() === wanted.trim().toLowerCase());
      if (!id) missing.push(wanted);
      else if (!ids.includes(id)) ids.push(id);
    }
  }
  const paths = new Set(["overview"]);
  const students = ids.map((id, index) => {
    const name = firstName(hass, id);
    let path = slug(name) || `student-${index + 1}`;
    for (let n = 2; paths.has(path); n++) path = `${slug(name) || "student"}-${n}`;
    paths.add(path);
    return { id, name, path, entities: deviceEntities(hass, id) };
  });
  return { students, missing };
}

function configEntryIds(device) {
  const ids = new Set(asList(device?.config_entries));
  if (device?.config_entry_id) ids.add(device.config_entry_id);
  return ids;
}

/* The account devices (last update, problem) of the accounts the students belong to. */
function accountsFor(hass, students) {
  const deviceIds = [];
  for (const entry of wilmaEntities(hass)) {
    if (entry.device_id && ACCOUNT_KEYS.includes(entry.translation_key) && !deviceIds.includes(entry.device_id)) {
      deviceIds.push(entry.device_id);
    }
  }
  const entries = new Set();
  for (const student of students) {
    for (const id of configEntryIds(hass?.devices?.[student.id])) entries.add(id);
  }
  const matching = deviceIds.filter((id) =>
    [...configEntryIds(hass?.devices?.[id])].some((entry) => entries.has(entry))
  );
  // Without config entry details on the devices, every account is the students' account
  return (matching.length ? matching : deviceIds)
    .sort((a, b) => deviceName(hass, a).localeCompare(deviceName(hass, b)))
    .map((id) => deviceEntities(hass, id));
}

function compact(items) {
  return items.filter(Boolean);
}

function tile(entityId, name, gridOptions = HALF_WIDTH) {
  return entityId ? { type: "tile", entity: entityId, name, grid_options: gridOptions } : null;
}

function nextLessonCard(hass, e) {
  return e.next_lesson
    ? {
        type: "custom:wilma-next-lesson-card",
        entity: e.next_lesson,
        title: t(hass, "next_lesson"),
        grid_options: FULL_WIDTH,
      }
    : null;
}

function dayScheduleCard(hass, entityId) {
  return entityId
    ? { type: "custom:wilma-schedule-card", entity: entityId, mode: "day", title: t(hass, "schedule") }
    : null;
}

function activityCard(hass, e, maxItems) {
  const keys = ["latest_message", "attendance_count", "latest_bulletin", "latest_attendance_mark"];
  const config = { type: "custom:wilma-activity-card" };
  for (const key of keys) if (e[key]) config[key] = e[key];
  if (Object.keys(config).length === 1) return null;
  return { ...config, max_items: maxItems, title: t(hass, "activity") };
}

/* Jinja for the markdown card, which renders it in Home Assistant with the latest states. */
function bulletinMarkdown(hass, entityId) {
  return [
    `{%- set e = '${entityId}' -%}`,
    `{%- if states(e) in ['unknown', 'unavailable', ''] -%}`,
    t(hass, "no_bulletins"),
    `{%- else -%}`,
    `**{{ states(e) }}**`,
    ``,
    `{{ state_attr(e, 'date') or '' }}{% if state_attr(e, 'author') %} · {{ state_attr(e, 'author') }}{% endif %}`,
    ``,
    `{{ state_attr(e, 'content_markdown') or '' }}`,
    `{%- if state_attr(e, 'url') %}`,
    ``,
    `[${t(hass, "open_in_wilma")}]({{ state_attr(e, 'url') }})`,
    `{%- endif %}`,
    `{%- endif %}`,
  ].join("\n");
}

function homeworkMarkdown(hass, entityId) {
  return [
    `{%- set e = '${entityId}' -%}`,
    `{%- set items = state_attr(e, 'recent_homework') or [] -%}`,
    `{%- if not items and states(e) not in ['unknown', 'unavailable', ''] -%}`,
    `{%- set items = [{'date': state_attr(e, 'date'), 'subject': state_attr(e, 'subject'), 'text': states(e)}] -%}`,
    `{%- endif -%}`,
    `{%- for item in items[:5] %}`,
    `- **{{ item.subject or '' }}** ({{ item.date or '' }}): {{ (item.text or '') | replace('\\n', ' ') }}`,
    `{%- else -%}`,
    t(hass, "no_homework"),
    `{%- endfor %}`,
  ].join("\n");
}

function accountCard(hass, accounts) {
  const single = accounts.length === 1;
  const rows = [];
  for (const account of accounts) {
    for (const key of ACCOUNT_KEYS) {
      if (account[key]) rows.push(single ? { entity: account[key], name: t(hass, key) } : { entity: account[key] });
    }
  }
  return rows.length ? { type: "entities", title: t(hass, "account"), state_color: true, entities: rows } : null;
}

function problemBadges(hass, accounts) {
  return accounts
    .filter((account) => account.problem)
    .map((account) => ({
      type: "entity",
      entity: account.problem,
      name: t(hass, "problem"),
      show_name: true,
      color: "red",
      visibility: [{ condition: "state", entity: account.problem, state: "on" }],
    }));
}

function countBadge(entityId, name) {
  return entityId
    ? {
        type: "entity",
        entity: entityId,
        name,
        show_name: true,
        visibility: [{ condition: "numeric_state", entity: entityId, above: 0 }],
      }
    : null;
}

/* Sections without cards are left out, so hidden parts and missing entities leave no gaps. */
function sections(groups) {
  return groups
    .map((cards) => compact(cards))
    .filter((cards) => cards.length)
    .map((cards) => ({ type: "grid", cards }));
}

function studentView(hass, student, hide, accounts) {
  const e = student.entities;
  const show = (part, card) => (hide.has(part) ? null : card);
  const examsEntity = e.upcoming_exams || e.next_exam;
  const calendars = compact([e.schedule, e.exams]);
  const view = {
    title: student.name,
    path: student.path,
    type: "sections",
    max_columns: 4,
  };
  if (!hide.has("badges")) {
    view.badges = compact([
      countBadge(e.unread_count, t(hass, "unread_messages")),
      countBadge(e.unread_bulletin_count, t(hass, "new_bulletins")),
      ...(hide.has("account") ? [] : problemBadges(hass, accounts)),
    ]);
  }
  view.sections = sections([
    [
      show("today", nextLessonCard(hass, e)),
      show("today", dayScheduleCard(hass, e.lessons_today)),
      show("today", dayScheduleCard(hass, e.lessons_tomorrow)),
    ],
    [
      show(
        "week",
        e.lessons_this_week && {
          type: "custom:wilma-schedule-card",
          entity: e.lessons_this_week,
          mode: "week",
          title: t(hass, "this_week"),
        }
      ),
    ],
    [
      show("activity", activityCard(hass, e, 10)),
      show("activity", tile(e.unread_count, t(hass, "unread_messages"))),
      show("activity", tile(e.unread_bulletin_count, t(hass, "new_bulletins"))),
    ],
    [
      show(
        "marks",
        e.attendance_count && {
          type: "custom:wilma-marks-card",
          entity: e.attendance_count,
          recent: 3,
          title: t(hass, "marks"),
        }
      ),
    ],
    [
      show(
        "exams",
        examsEntity && {
          type: "custom:wilma-exams-card",
          entity: examsEntity,
          max_items: 5,
          title: t(hass, "exams"),
        }
      ),
      show("exams", tile(e.latest_exam_grade, t(hass, "latest_grade"), FULL_WIDTH)),
    ],
    [
      show(
        "bulletins",
        e.latest_bulletin && {
          type: "markdown",
          title: t(hass, "bulletin_title"),
          content: bulletinMarkdown(hass, e.latest_bulletin),
        }
      ),
      show(
        "homework",
        e.latest_homework && {
          type: "markdown",
          title: t(hass, "homework"),
          content: homeworkMarkdown(hass, e.latest_homework),
        }
      ),
    ],
    [
      show(
        "calendar",
        calendars.length && {
          type: "calendar",
          title: t(hass, "calendar"),
          initial_view: "listWeek",
          entities: calendars,
        }
      ),
    ],
    [show("account", accountCard(hass, accounts))],
  ]);
  return view;
}

/* Each student side by side (stacked on phones): next lesson, today and recent activity. */
function overviewView(hass, students, hide, accounts) {
  const view = {
    title: t(hass, "overview"),
    path: "overview",
    icon: "mdi:home-account",
    type: "sections",
    max_columns: Math.min(Math.max(students.length, 2), 4),
  };
  if (!hide.has("badges") && !hide.has("account")) view.badges = problemBadges(hass, accounts);
  const groups = students.map((student) => {
    const e = student.entities;
    const cards = compact([
      hide.has("today") ? null : nextLessonCard(hass, e),
      hide.has("today") ? null : dayScheduleCard(hass, e.lessons_today),
      hide.has("activity") ? null : activityCard(hass, e, 5),
    ]);
    return cards.length
      ? [{ type: "heading", heading: student.name, heading_style: "title", icon: "mdi:account-school" }, ...cards]
      : [];
  });
  groups.push([hide.has("account") ? null : accountCard(hass, accounts)]);
  view.sections = sections(groups);
  return view;
}

function messageView(hass, missing) {
  const lines = [`## ${t(hass, "no_students_title")}`, "", t(hass, "no_students_text")];
  if (missing.length) lines.push("", t(hass, "unknown_students", { names: missing.join(", ") }));
  lines.push("", `[Wilma for Home Assistant](${DASHBOARD_DOCS_URL})`);
  return {
    title: "Wilma",
    path: "wilma",
    type: "sections",
    max_columns: 2,
    sections: [{ type: "grid", cards: [{ type: "markdown", content: lines.join("\n") }] }],
  };
}

function dashboardViews(hass, config) {
  const { students: selection, hide } = strategyOptions(config);
  const { students, missing } = selectStudents(hass, selection);
  if (missing.length) console.warn(`Wilma dashboard: students not found: ${missing.join(", ")}`);
  if (!students.length) return [messageView(hass, missing)];
  // A student's view shows their own account; the overview shows every student's account
  const views = students.map((student) =>
    studentView(hass, student, hide, accountsFor(hass, [student]))
  );
  if (students.length > 1 && !hide.has("overview")) {
    views.unshift(overviewView(hass, students, hide, accountsFor(hass, students)));
  }
  return views;
}

/*
 * A dashboard whose configuration is `strategy: {type: custom:wilma}`: a view per student,
 * preceded by an overview when there are several. Home Assistant calls `generate` with the
 * strategy configuration whenever it loads the dashboard.
 */
class WilmaDashboardStrategy extends HTMLElement {
  // Its options (students, hide) are set in YAML; there is nothing to edit when creating it
  static noEditor = true;

  static getCreateSuggestions() {
    return { title: "Wilma", icon: "mdi:school" };
  }

  static async generate(config, hass) {
    // No title, so the header shows the name the user gave the dashboard
    return { views: dashboardViews(hass, config) };
  }
}

/*
 * A single view for another dashboard: `strategy: {type: custom:wilma, student: ...}` shows
 * that student, and without `student` it shows the only student or the overview.
 */
class WilmaViewStrategy extends HTMLElement {
  static async generate(config, hass) {
    const options = config && typeof config === "object" ? config : {};
    if (options.student !== undefined && typeof options.student !== "string") {
      throw new Error("Wilma view: student must be a device ID or first name");
    }
    const selection = options.student !== undefined ? [options.student] : options.students;
    const { hide } = strategyOptions({ ...options, students: selection });
    const { students, missing } = selectStudents(hass, selection);
    if (!students.length) return messageView(hass, missing);
    const accounts = accountsFor(hass, students);
    if (students.length === 1) return studentView(hass, students[0], hide, accounts);
    return overviewView(hass, students, hide, accounts);
  }
}

/* ---------- Registration ---------- */

const CARDS = [
  {
    type: "wilma-schedule-card",
    element: WilmaScheduleCard,
    name: "Wilma schedule",
    description: "A student's lessons for a day or the week, with the ongoing lesson highlighted.",
  },
  {
    type: "wilma-next-lesson-card",
    element: WilmaNextLessonCard,
    name: "Wilma next lesson",
    description: "When and where a student's next lesson starts.",
  },
  {
    type: "wilma-activity-card",
    element: WilmaActivityCard,
    name: "Wilma activity",
    description: "Recent messages, attendance marks and bulletins, newest first, with who sent them.",
  },
  {
    type: "wilma-marks-card",
    element: WilmaMarksCard,
    name: "Wilma attendance marks",
    description: "Attendance marks this school year by type, and the latest marks.",
  },
  {
    type: "wilma-exams-card",
    element: WilmaExamsCard,
    name: "Wilma exams",
    description: "A student's upcoming exams with subject, info and teachers.",
  },
];

window.customCards = window.customCards || [];
for (const { type, element, name, description } of CARDS) {
  if (customElements.get(type)) continue;
  customElements.define(type, element);
  window.customCards.push({ type, name, description, preview: true, documentationURL: DOCS_URL });
}

const STRATEGIES = [
  ["ll-strategy-dashboard-wilma", WilmaDashboardStrategy],
  ["ll-strategy-view-wilma", WilmaViewStrategy],
];
const strategiesAlreadyDefined = Boolean(customElements.get(STRATEGIES[0][0]));
for (const [name, element] of STRATEGIES) {
  if (!customElements.get(name)) customElements.define(name, element);
}
// Makes the dashboard selectable in "Add dashboard"; view strategies can't be picked there
window.customStrategies = window.customStrategies || [];
if (!strategiesAlreadyDefined) {
  window.customStrategies.push({
    type: "wilma",
    strategyType: "dashboard",
    name: "Wilma",
    description: "Schedule, activity, attendance marks, exams and bulletins for every student",
    documentationURL: DOCS_URL,
  });
}

console.info(`Wilma cards ${VERSION} loaded`);

export {
  WilmaActivityCard,
  WilmaDashboardStrategy,
  WilmaExamsCard,
  WilmaMarksCard,
  WilmaNextLessonCard,
  WilmaScheduleCard,
  WilmaViewStrategy,
};
