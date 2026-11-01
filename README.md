# Wilma for Home Assistant

A Home Assistant integration for the Wilma school platform. This integration allows you to fetch and display your Wilma messages in Home Assistant.

## Features

- Read-only: it never sends, replies to or changes anything in Wilma
- **Multiple students**: every child on the account gets their own device (_Wilma {first
  name}_) with their own entities
- Events for every **new message**, **new attendance mark** (absence, lateness, positive
  feedback, missing homework, behaviour note, ...) and **new bulletin**, so you can get a
  notification as soon as something comes in
- A **schedule calendar** per student, plus next lesson and today's, tomorrow's and this
  week's lessons
- Sensors for messages, unread count, attendance marks, bulletins and recent activity
- Options for the update interval and how long new things count as recent
- English, Finnish and Swedish

Notes:

- Fetching a message's content marks it as read in Wilma. The integration fetches content only
  for new messages (and on first setup only for messages from the last 7 days).
- Wilma allows one session per account, so the integration logging in logs out the same
  account in the browser or app (and vice versa; the integration logs in again by itself).
- On first setup, existing messages, marks and bulletins are recorded as already seen; only
  things that arrive afterwards fire events.

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
| Latest message | Sensor | Subject; id, sender, timestamp, content, content_markdown |
| Unread messages | Sensor | Number of unread messages in Wilma |
| Latest attendance mark | Sensor | Type description (e.g. "Aktivt deltagande"); date, hour, code, color, course, comment, teacher, `marks_this_school_year`, `counts_by_type` |
| Attendance marks | Sensor | Number of marks this school year; `by_type`, `by_code` |
| Latest bulletin | Sensor | Title of the newest bulletin; date, author, audience, url, content_html, content_markdown |
| New bulletins | Sensor | Bulletins that appeared within the recent threshold |
| Next lesson | Sensor | Subject of the next lesson that hasn't started; date, start, end, teachers, rooms |
| Lessons today / tomorrow | Sensor | Number of lessons (`0` on days off); date, start (first lesson), end (last lesson), lessons |
| Lessons this week | Sensor | Number of lessons; week_start, week_end, lessons |
| Recent message | Binary sensor | On while the latest message is within the recent threshold |
| Recent bulletin | Binary sensor | On while a new bulletin appeared, or the latest is dated, within the threshold |
| Recent attendance mark | Binary sensor | On while a new mark appeared, or the latest is dated, within the threshold |
| Schedule | Calendar | Every lesson as an event (subject, room as location, teachers in the description); `on` during a lesson |

The calendar shows up in Home Assistant's calendar view, and `calendar.get_events` works for
any range: the current and next week are fetched with every update, other weeks when asked
for (at most 12 weeks per query, cached for an hour).

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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT
