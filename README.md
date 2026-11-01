# Wilma for Home Assistant

A Home Assistant integration for the Wilma school platform. It brings each student's messages, attendance marks, bulletins, schedule, exams and homework from Wilma into Home Assistant.

## Features

- Read-only: it never sends, replies to or changes anything in Wilma
- **Multiple students**: every child on the account gets their own device (_Wilma {first
  name}_) with their own entities
- Events for every **new message**, **new attendance mark** (absence, lateness, positive
  feedback, missing homework, behaviour note, ...), **new bulletin**, **new exam**, **new exam
  grade** and **new homework**, so you can get a notification as soon as something comes in
- A **schedule calendar** per student, plus next lesson and today's, tomorrow's and this
  week's lessons
- **Exams**: next exam, upcoming exams, latest grade, and an exam calendar per student
- **Homework** entered by teachers in the lesson diary
- Sensors for messages, unread count, attendance marks, bulletins and recent activity
- **Dashboard cards** for the schedule, next lesson, recent activity, attendance marks and
  exams, and a **ready-made dashboard** (one line of configuration) with a tab per student
- Options for the update interval and how long new things count as recent
- English, Finnish and Swedish

Notes:

- Fetching a message's content marks it as read in Wilma. The integration fetches content only
  for new messages (and on first setup only for messages from the last 7 days).
- Wilma allows one session per account, so the integration logging in logs out the same
  account in the browser or app (and vice versa; the integration logs in again by itself).
- On first setup, existing messages, marks, bulletins, exams, grades and homework are recorded
  as already seen; only things that arrive afterwards fire events.
- Exams, grades and homework come from the student's overview in Wilma, which covers the
  current courses. Reading it does not mark grades as seen in Wilma.

## Installation

### HACS (Recommended)

1. Make sure you have [HACS](https://hacs.xyz/) installed
2. Add this repository as a custom repository in HACS:
   - Go to HACS → Integrations → ⋮ (menu) → Custom repositories
   - Add `https://github.com/frwickst/wilma_ha` with category "Integration"
3. Install the integration from HACS
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/wilma` folder from this repository to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration** and search for **Wilma**
2. Enter your school's Wilma address (e.g. `https://turku.inschool.fi` or
   `https://espoo.inschool.fi`), your username and password

The students on the account are found automatically. Under **Configure** on the integration
card you can change:

- **Update interval** (minutes, default 30)
- **Recent threshold** (hours, default 24): how long new messages, bulletins and attendance
  marks keep the _recent_ binary sensors on and count as new bulletins

## Usage

Entity IDs follow the device names, e.g. `sensor.wilma_anna_next_lesson` for a student called
Anna.

### Per student (device _Wilma {first name}_)

| Entity | Type | State and attributes |
| --- | --- | --- |
| Latest message | Sensor | Subject; id, sender, timestamp, content, content_markdown, `recent_messages` (the 5 newest: id, subject, sender, timestamp, unread) |
| Unread messages | Sensor | Number of unread messages in Wilma |
| Latest attendance mark | Sensor | Type description (e.g. "Aktivt deltagande"); date, hour, code, color, course, comment, teacher, `marks_this_school_year`, `counts_by_type` |
| Attendance marks | Sensor | Number of marks this school year; `by_type`, `by_code`, `types` (type_id, code, description, color, count of each type that occurs, most frequent first), `recent_marks` (the 10 newest: date, hour, code, description, color, course, comment, teacher) |
| Latest bulletin | Sensor | Title of the newest bulletin; date, author, audience, url, content_html, content_markdown, `recent_bulletins` (the 5 newest current ones: id, title, date, author, url) |
| New bulletins | Sensor | Bulletins that appeared within the recent threshold |
| Next lesson | Sensor | Subject of the next lesson that hasn't started; date, start, end, teachers, rooms |
| Lessons today / tomorrow | Sensor | Number of lessons (`0` on days off); date, start (first lesson), end (last lesson), lessons |
| Lessons this week | Sensor | Number of lessons; week_start, week_end, lessons |
| Next exam | Sensor | Subject of the next exam (today or later); id, date, subject, course, name, info, teachers, grade, verbal_grade, days_until |
| Upcoming exams | Sensor | Number of exams today or later; `exams` (soonest first, at most 15: date, subject, course, name, info, teachers, and grade when there is one) |
| Latest exam grade | Sensor | Grade (or verbal assessment) of the most recent graded exam; id, date, subject, course, name, info, teachers, grade, verbal_grade, seen, `graded_exams` (the 10 newest: date, subject, course, grade, verbal_grade) |
| Latest homework | Sensor | The newest homework text; date, subject, course, text, `recent_homework` (the 10 newest: date, subject, course, text) |
| Recent message | Binary sensor | On while the latest message is within the recent threshold |
| Recent bulletin | Binary sensor | On while a new bulletin appeared, or the latest is dated, within the threshold |
| Recent attendance mark | Binary sensor | On while a new mark appeared, or the latest is dated, within the threshold |
| Schedule | Calendar | Every lesson as an event (subject, room as location, teachers in the description); `on` during a lesson |
| Exams | Calendar | Every exam of the current courses as an all-day event (info, teachers and grade in the description); `on` on an exam day |

The calendar shows up in Home Assistant's calendar view, and `calendar.get_events` works for
any range: the current and next week are fetched with every update, other weeks when asked
for (at most 12 weeks per query, cached for an hour).

Long texts in attributes are shortened (300 characters in lists, 1000 for a single item, 255
for a state) to keep attributes small.

### Per account (device _Wilma ({username})_)

| Entity | Type | State and attributes |
| --- | --- | --- |
| Last update | Sensor | Time of the last successful update |
| Problem | Binary sensor | On when the last update failed or part of the data couldn't be fetched; `error`, `partial_errors` |

### Schedule examples

When does school start tomorrow?

```yaml
{{ state_attr('sensor.wilma_anna_lessons_tomorrow', 'start') }}
```

Remind the evening before about the first lesson:

```yaml
automation:
  - alias: "Wilma: tomorrow's first lesson"
    trigger:
      - platform: time
        at: "19:00:00"
    condition:
      - condition: numeric_state
        entity_id: sensor.wilma_anna_lessons_tomorrow
        above: 0
    action:
      - service: notify.mobile_app_my_phone
        data:
          title: "School tomorrow"
          message: >
            {% set first = state_attr('sensor.wilma_anna_lessons_tomorrow', 'lessons')[0] %}
            Starts {{ as_timestamp(first.start) | timestamp_custom('%H:%M') }} with {{ first.subject }}
```

Lessons of any week, e.g. next week, from a script or template:

```yaml
action: calendar.get_events
target:
  entity_id: calendar.wilma_anna_schedule
data:
  start_date_time: "{{ (today_at() + timedelta(days=7 - now().weekday())).isoformat() }}"
  duration:
    days: 7
response_variable: next_week
```

### Events

Every event includes `entry_id`, `student_id` and `student_name`.

| Event | Data |
| --- | --- |
| `wilma_new_message` | `id`, `subject`, `sender`, `timestamp`, `unread`, `content_html`, `content_markdown` |
| `wilma_new_attendance_mark` | `key`, `date`, `hour`, `type_id`, `code`, `description`, `color`, `name`, `course`, `comment`, `teacher`, `teacher_code`, `clarification`, `title` |
| `wilma_new_bulletin` | `id`, `title`, `date`, `section`, `author`, `url`, `content_html`, `content_markdown` |
| `wilma_new_exam` | `id`, `date`, `subject`, `course`, `name`, `info`, `teachers`, `grade`, `verbal_grade` |
| `wilma_new_exam_grade` | Same as `wilma_new_exam`, plus `previous_grade` (`null` unless a grade was changed) |
| `wilma_new_homework` | `key`, `date`, `subject`, `course`, `text` |

Mark types, codes and colours are configured per school. In Turku, for example, positive
feedback has the code `+` (purple, `#9191FF`), missing homework is `Ogjorda uppgifter`
(blue, `#0080FF`) and behaviour notes are `Beteende` (grey, `#D4D4D4`). The **Attendance
marks** sensor's `by_type` and `by_code` attributes show which types your school uses.

### Notify on new attendance marks

```yaml
automation:
  - alias: "Notify on new Wilma attendance mark"
    trigger:
      - platform: event
        event_type: wilma_new_attendance_mark
    action:
      - service: notify.mobile_app_my_phone
        data:
          title: "Wilma ({{ trigger.event.data.student_name }}): {{ trigger.event.data.description }}"
          message: >
            {{ trigger.event.data.date }}, {{ trigger.event.data.course or '' }}
            {{ trigger.event.data.comment or '' }} ({{ trigger.event.data.teacher }})
```

Only some kinds of marks, e.g. positive feedback, missing homework and behaviour notes:

```yaml
    trigger:
      - platform: event
        event_type: wilma_new_attendance_mark
    condition:
      - condition: template
        value_template: >
          {{ trigger.event.data.code in ['+', 'Ogjorda uppgifter', 'Beteende'] }}
```

### Exams and homework

Notify when an exam is added and when it gets a grade:

```yaml
automation:
  - alias: "Notify on new Wilma exam"
    trigger:
      - platform: event
        event_type: wilma_new_exam
    action:
      - service: notify.mobile_app_my_phone
        data:
          title: "Wilma ({{ trigger.event.data.student_name }}): exam {{ trigger.event.data.date }}"
          message: "{{ trigger.event.data.subject }}: {{ trigger.event.data.info or '' }}"
  - alias: "Notify on new Wilma exam grade"
    trigger:
      - platform: event
        event_type: wilma_new_exam_grade
    action:
      - service: notify.mobile_app_my_phone
        data:
          title: "Wilma ({{ trigger.event.data.student_name }}): {{ trigger.event.data.subject }}"
          message: "Grade {{ trigger.event.data.grade or trigger.event.data.verbal_grade }}"
```

Remind the evening before an exam:

```yaml
automation:
  - alias: "Wilma: exam tomorrow"
    trigger:
      - platform: time
        at: "18:00:00"
    condition:
      - condition: template
        value_template: "{{ state_attr('sensor.wilma_anna_next_exam', 'days_until') == 1 }}"
    action:
      - service: notify.mobile_app_my_phone
        data:
          title: "Exam tomorrow: {{ states('sensor.wilma_anna_next_exam') }}"
          message: "{{ state_attr('sensor.wilma_anna_next_exam', 'info') or '' }}"
```

New homework:

```yaml
automation:
  - alias: "Notify on new Wilma homework"
    trigger:
      - platform: event
        event_type: wilma_new_homework
    action:
      - service: notify.mobile_app_my_phone
        data:
          title: "Homework ({{ trigger.event.data.subject }})"
          message: "{{ trigger.event.data.text }}"
```

### Notify on new messages

```yaml
automation:
  - alias: "Notify on new Wilma message"
    trigger:
      - platform: event
        event_type: wilma_new_message
    action:
      - service: notify.mobile_app_my_phone
        data:
          title: "Wilma: {{ trigger.event.data.subject }}"
          message: "{{ trigger.event.data.sender }}"
```

### Notify on new bulletins

```yaml
automation:
  - alias: "Notify on new Wilma bulletin"
    trigger:
      - platform: event
        event_type: wilma_new_bulletin
    action:
      - service: notify.mobile_app_my_phone
        data:
          title: "Wilma bulletin: {{ trigger.event.data.title }}"
          message: "{{ (trigger.event.data.content_markdown or '')[:200] }}"
          data:
            url: "{{ trigger.event.data.url }}"
```

### AI Summarization Example

To use with Home Assistant's conversation agents for summarization:

```yaml
automation:
  - alias: "Summarize new Wilma message with AI"
    trigger:
      - platform: event
        event_type: wilma_new_message
    action:
      - service: conversation.process
        data:
          agent_id: homeassistant
          text: >
            Summarize this message in a concise way: {{ trigger.event.data.content_markdown }}
          agent_id: homeassistant
      - service: notify.mobile_app
        data:
          title: "New Wilma Message Summary"
          message: "{{ conversation.agent_response.response.speech.plain.text }}"
```

## Lovelace cards

The integration comes with dashboard cards. They are registered automatically when the
integration loads, so there is no dashboard resource to add: edit a dashboard, choose
**Add card** and search for _Wilma_. A card added from the picker starts with the first
student's entities; pick another student's entities in the card's settings. After upgrading
the integration, refresh the browser (or clear the app's frontend cache) to get the new cards.

Every card takes entity IDs, or instead `student`: the device ID of a student's _Wilma {first
name}_ device, from which the card finds the entities itself. `title` overrides the card's
title. The cards follow the dashboard theme and the language, time format and time zone of
your profile.

### Schedule

The lessons of a day, or of the week grouped by weekday. The ongoing lesson is highlighted and
marked _Now_, past lessons are greyed out and ticked, and days off show _No lessons_.

```yaml
type: custom:wilma-schedule-card
entity: sensor.wilma_anna_lessons_today   # or lessons_tomorrow
mode: day
```

```yaml
type: custom:wilma-schedule-card
entity: sensor.wilma_anna_lessons_this_week
mode: week
hide_past_days: true
```

| Option | Default | Description |
| --- | --- | --- |
| `entity` | | A lessons today, tomorrow or this week sensor |
| `mode` | `week` for the week sensor, else `day` | `day` or `week` |
| `day` | `today` | With `student` in day mode: `today` or `tomorrow` |
| `show_rooms`, `show_teachers` | `true` | Show rooms and teachers |
| `hide_past_days` | `false` | In week mode, leave out the days before today |

### Next lesson

A compact tile: subject, time until it starts (or the day and time), room and teacher.

```yaml
type: custom:wilma-next-lesson-card
entity: sensor.wilma_anna_next_lesson
```

### Activity

What happened lately and who did it: messages (sender), attendance marks (type with its
colour and code, course, comment, teacher) and bulletins (author) in one list, newest first.
Each entity is optional.

```yaml
type: custom:wilma-activity-card
latest_message: sensor.wilma_anna_latest_message
attendance_count: sensor.wilma_anna_attendance_marks
latest_bulletin: sensor.wilma_anna_latest_bulletin
max_items: 10
```

### Attendance marks

This school year's marks per type, with each type's colour, code and count, followed by the
latest marks.

```yaml
type: custom:wilma-marks-card
entity: sensor.wilma_anna_attendance_marks
recent: 3   # latest marks to show, 0 for none
```

### Exams

Upcoming exams with date, subject, info, teachers and grade when there is one.

```yaml
type: custom:wilma-exams-card
entity: sensor.wilma_anna_upcoming_exams
max_items: 5
```

## Dashboard

There are two ways to get a complete Wilma dashboard: a ready-made one that builds itself
from your students (a _dashboard strategy_), or a fixed YAML dashboard to copy and change.

### Ready-made dashboard

Go to **Settings → Dashboards → Add dashboard** and choose **Wilma**. It suggests the name
_Wilma_ and a school icon; change them if you like and create the dashboard. That's all.

If **Wilma** isn't in the list (refresh the browser after installing or upgrading), create
it by hand instead:

1. **Add dashboard → New dashboard from scratch**, give it a name and open it.
2. Open the **⋮** menu at the top right, choose **Edit dashboard**, then **⋮ → Raw
   configuration editor**.
3. Replace everything with the following and save:

```yaml
strategy:
  type: custom:wilma
```

The dashboard is generated every time it is opened, from the students the integration has
found, so new students appear by themselves and it follows the language of your profile.
After upgrading the integration, refresh the browser (or clear the app's frontend cache) if
the dashboard looks outdated or reports an unknown strategy.

What you get:

- **One tab per student**, named after the student, with these sections. On a wide screen
  they sit side by side in up to four columns; on a phone they stack in this order:
  - **Today**: the next lesson as a compact tile (subject, how soon, room and teacher),
    followed by today's and tomorrow's lessons with the ongoing lesson highlighted.
  - **This week**: the week's lessons grouped by weekday.
  - **Recent activity**: messages, attendance marks and bulletins in one list, newest
    first, each with who sent or entered it; below it, tiles with the number of unread
    messages and new bulletins.
  - **Attendance marks**: this school year's marks per type with their colours and counts,
    and the three latest marks.
  - **Exams**: upcoming exams with dates, info and teachers, and a tile with the latest
    exam grade.
  - **Bulletin and homework**: the latest bulletin in full (title, date, author, text and a
    link to Wilma) and the five latest homework entries.
  - **Calendar**: the schedule and exam calendars as a week list.
  - **Wilma account**: the time of the last update and the problem sensor, at the bottom.
  - Badges at the top for unread messages and new bulletins (only while there are any) and
    a red _Problem_ badge (only while updating from Wilma fails).
- With several students, an **overview tab** (house icon) comes first: a column per
  student with their name, next lesson, today's lessons and the five latest activities, so
  you see everyone's day at a glance.
- Without any Wilma students (for example before the integration is set up), the dashboard
  shows a short message explaining what to do instead.

Options go under `strategy`:

```yaml
strategy:
  type: custom:wilma
  students:          # which students to show, in this order (default: all, by name)
    - Anna           # a first name ...
    - 3f2a9c1e5b7d4e6f8a0b1c2d3e4f5a6b   # ... or a device ID
  hide:              # parts to leave out
    - calendar
    - homework
```

| Option | Default | Description |
| --- | --- | --- |
| `students` | all students, by name | First names or device IDs of the students to show, in the order of their tabs. The device ID is the last part of the address when you open the student's _Wilma {first name}_ device under **Settings → Devices & services** |
| `hide` | nothing | Any of `overview`, `badges`, `today`, `week`, `activity`, `marks`, `exams`, `bulletins`, `homework`, `calendar`, `account` |

To change the options later, choose **⋮ → Edit dashboard**: for a generated dashboard Home
Assistant opens a dialog whose menu has the code editor for the configuration above, and
**Take control**, which turns the dashboard into a normal one you can edit card by card
(it then no longer updates itself). Or start from the YAML file below.

A student's view can also be added to another dashboard as a tab of its own: add a view in
that dashboard's raw configuration editor with

```yaml
views:
  # ... the dashboard's other views
  - title: Anna
    path: anna
    strategy:
      type: custom:wilma
      student: Anna   # without `student`: the only student, or the overview
      hide: [calendar]
```

### YAML dashboard

[`dashboards/wilma.yaml`](dashboards/wilma.yaml) is the same dashboard as a fixed
configuration for one student called Anna, to copy and customise:

1. Create a dashboard and open the raw configuration editor as in steps 1 and 2 above.
2. Paste the contents of `dashboards/wilma.yaml`.
3. Replace `wilma_anna` in the entity IDs with your student's (e.g. `wilma_emil` for a
   student called Emil), `wilma_username` with your account device's (_Wilma ({username})_),
   and the view's `title` and `path`. For more students, copy the view and repeat.
4. Save. From then on you can edit cards in the dashboard editor as usual.

## Development

### Setup Development Environment

1. Clone the repository
   ```bash
   git clone https://github.com/frwickst/wilma-ha
   cd wilma-ha
   ```

2. Set up the development environment:
   ```bash
   uv venv -p 3.14 .venv
   VIRTUAL_ENV=$PWD/.venv uv pip install -r requirements_dev.txt
   source .venv/bin/activate
   ```

   `./scripts/setup.sh` additionally symlinks the integration into a local
   `.homeassistant/config` for running a development Home Assistant instance.

### Running Tests

This integration includes a comprehensive test suite to ensure functionality:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=custom_components.wilma

# Run a specific test file
pytest tests/test_sensor.py
```

### Quality Checks

```bash
# Run ruff for linting
ruff check custom_components/wilma

# Run mypy for type checking
mypy custom_components/wilma
```

### Releasing

1. Publish the required `wilhelmina` version to PyPI first.
2. Set `version` in `custom_components/wilma/manifest.json` (and the root `manifest.json`).
3. Commit, then push an annotated tag matching that version; its message becomes the release
   notes:
   ```bash
   git tag -a v0.3.0 -m "Release notes"
   git push origin v0.3.0
   ```
   The release workflow checks the tag against the manifest and creates the GitHub release,
   which HACS then offers as a version.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT
