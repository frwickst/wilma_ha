# Wilma for Home Assistant

A Home Assistant integration for the Wilma school platform, providing access to your messages,
attendance marks, bulletins, schedule, exams and homework.

## Features

- Read-only; polls Wilma every 30 minutes (configurable)
- Multiple students: a device per child on the account
- Events for new messages, attendance marks (absences, positive feedback, missing homework,
  behaviour notes, ...), bulletins, exams, exam grades and homework
- Schedule calendar, next lesson and today's, tomorrow's and this week's lessons
- Exam calendar, next exam, upcoming exams and latest exam grade
- Latest homework from the lesson diary
- Sensors for messages, unread count, attendance marks, bulletins and recent activity
- Dashboard cards (weekly timetable, schedule, next lesson, activity, attendance marks, exams), registered
  automatically
- A ready-made dashboard with a tab per student and an overview: just
  `strategy: {type: custom:wilma}`, or copy `dashboards/wilma.yaml`
- English, Finnish and Swedish

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