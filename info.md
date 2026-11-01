# Wilma for Home Assistant

A Home Assistant integration for the Wilma school platform, providing access to your messages,
attendance marks and schedule.

## Features

- Polls Wilma every 30 minutes (read-only)
- Fires `wilma_new_message` and `wilma_new_attendance_mark` events for new messages and new
  attendance marks (absences, positive feedback, missing homework, behaviour notes, ...)
- A schedule calendar with the student's lessons
- Provides sensors for:
  - Latest message
  - Latest attendance mark
  - Lessons today, tomorrow and this week
  - Last update time
- Stores message content for access by automations
- Perfect for creating AI-powered notification workflows

## Usage

After installation, add the integration through the Home Assistant UI:
1. Go to Configuration → Integrations → Add Integration
2. Search for "Wilma" and follow the setup process
3. Enter your Wilma server URL, username, and password

## Example Automation for AI Summarization

```yaml
automation:
  - alias: "Summarize new Wilma message"
    trigger:
      - platform: event
        event_type: wilma_new_message
    action:
      - service: conversation.process
        data:
          agent_id: homeassistant
          text: >
            Summarize this message concisely: {{ trigger.event.data.content_markdown }}
      - service: notify.mobile_app
        data:
          title: "Wilma Message Summary"
          message: "{{ conversation.agent_response.response.speech.plain.text }}"
```

## Troubleshooting

- Check Home Assistant logs for any error messages
- Verify your Wilma credentials and server URL
- For support, open an issue on GitHub