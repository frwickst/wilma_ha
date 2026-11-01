# Wilma for Home Assistant

A Home Assistant integration for the Wilma school platform. This integration allows you to fetch and display your Wilma messages in Home Assistant.

## Features

- Polls Wilma every 30 minutes (read-only: it never sends, replies to or changes anything)
- Fires an event for every **new message** and every **new attendance mark** (absence,
  lateness, positive feedback, missing homework, behaviour note, ...), so you can get a
  notification as soon as something comes in
- A **schedule calendar** with the student's lessons, and sensors for today's, tomorrow's and
  this week's lessons
- Sensors for the latest message, the latest attendance mark and the last update time
- Stores the latest 50 messages with their content for use in automations

Notes:

- Fetching a message's content marks it as read in Wilma. The integration fetches content only
  for new messages (and on first setup only for messages from the last 7 days).
- Wilma allows one session per account, so the integration logging in logs out the same
  account in the browser or app (and vice versa; the integration logs in again by itself).
- On first setup, existing messages and marks are recorded as already seen; only things that
  arrive afterwards fire events.

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

1. Go to Configuration → Integrations → Add Integration
2. Search for "Wilma" and select it
3. Enter your Wilma server URL, username, and password
4. Click "Submit"

## Usage

After setup, the integration provides these sensors (entity IDs depend on the account name,
e.g. `sensor.wilma_<username>_latest_message`):

- **Latest message**: subject as state; id, sender, timestamp, content and
  content_markdown as attributes
- **Latest attendance mark**: the mark type's description as state (e.g. "Aktivt deltagande");
  date, hour, code, color, course, comment, teacher, plus `marks_this_school_year` and
  `counts_by_type` as attributes
- **Last update**: time of the last successful update
- **Lessons today** / **Lessons tomorrow**: number of lessons as state; `date`, `start` (first
  lesson), `end` (last lesson) and `lessons` (start, end, subject, teachers, rooms) as
  attributes. They switch over at midnight. `0` means a day without lessons (weekend,
  holiday).
- **Lessons this week**: number of lessons this week, with `week_start`, `week_end` and
  `lessons` as attributes

And a calendar:

- **Schedule** (`calendar.wilma_<username>_schedule`): every lesson as a calendar event
  (subject, room as location, teachers in the description). Its state is `on` during a lesson,
  and its attributes describe the ongoing or next lesson. It shows up in Home Assistant's
  calendar view, and `calendar.get_events` works for any range (the current and next week
  are fetched with every update; other weeks are fetched when asked for, at most 12 weeks
  per query, and cached for an hour).

### Schedule examples

When does school start tomorrow?

```yaml
{{ state_attr('sensor.wilma_testuser_lessons_tomorrow', 'start') }}
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
        entity_id: sensor.wilma_testuser_lessons_tomorrow
        above: 0
    action:
      - service: notify.mobile_app_my_phone
        data:
          title: "School tomorrow"
          message: >
            {% set first = state_attr('sensor.wilma_testuser_lessons_tomorrow', 'lessons')[0] %}
            Starts {{ as_timestamp(first.start) | timestamp_custom('%H:%M') }} with {{ first.subject }}
```

Lessons of any week, e.g. next week, from a script or template:

```yaml
action: calendar.get_events
target:
  entity_id: calendar.wilma_testuser_schedule
data:
  start_date_time: "{{ (today_at() + timedelta(days=7 - now().weekday())).isoformat() }}"
  duration:
    days: 7
response_variable: next_week
```

### Events

| Event | Data |
| --- | --- |
| `wilma_new_message` | `entry_id`, `id`, `subject`, `sender`, `timestamp`, `content_markdown` |
| `wilma_new_attendance_mark` | `entry_id`, `key`, `date`, `hour`, `type_id`, `code`, `description`, `color`, `name`, `course`, `comment`, `teacher`, `teacher_code`, `clarification`, `title` |

Mark types, codes and colours are configured per school. In Turku, for example, positive
feedback has the code `+` (purple, `#9191FF`), missing homework is `Ogjorda uppgifter`
(blue, `#0080FF`) and behaviour notes are `Beteende` (grey, `#D4D4D4`). The **Latest
attendance mark** sensor's `counts_by_type` attribute shows which types your school uses.

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
          title: "Wilma: {{ trigger.event.data.description }}"
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
