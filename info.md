# Wilma for Home Assistant

A Home Assistant integration for the Wilma school platform, providing access to your messages.

## Features

- Polls Wilma for new messages every 15 minutes
- Provides sensors for:
  - Latest message
  - Latest unread message
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
      platform: state
      entity_id: sensor.latest_message
    action:
      - service: conversation.process
        data:
          agent_id: homeassistant
          text: >
            Summarize this message concisely: {{ state_attr('sensor.latest_message', 'content_markdown') }}
      - service: notify.mobile_app
        data:
          title: "Wilma Message Summary"
          message: "{{ conversation.agent_response.response.speech.plain.text }}"
```

## Troubleshooting

- Check Home Assistant logs for any error messages
- Verify your Wilma credentials and server URL
- For support, open an issue on GitHub