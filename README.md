# Wilma for Home Assistant

A Home Assistant integration for the Wilma school platform. This integration allows you to fetch and display your Wilma messages in Home Assistant.

## Features

- Polls Wilma for new messages every 15 minutes
- Provides sensors for latest message, latest unread message, and last update time
- Stores message content for access by automations
- Allows creating automations based on new messages

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

After setup, the integration will provide the following sensors:

- `sensor.latest_message`: The most recent message (subject as state, content in attributes)
- `sensor.last_update`: Timestamp of the last successful data update

### Automation Example

Here's an example automation that sends a notification when a new message is received:

```yaml
automation:
  - alias: "Notify on new Wilma message"
    trigger:
      platform: state
      entity_id: sensor.latest_message
    action:
      - service: notify.mobile_app
        data:
          title: "New Wilma Message"
          message: "{{ trigger.to_state.state }}"
          data:
            clickAction: /lovelace/wilma
```

### AI Summarization Example

To use with Home Assistant's conversation agents for summarization:

```yaml
automation:
  - alias: "Summarize new Wilma message with AI"
    trigger:
      platform: state
      entity_id: sensor.latest_message
    action:
      - service: conversation.process
        data:
          agent_id: homeassistant
          text: >
            Summarize this message in a concise way: {{ state_attr('sensor.latest_message', 'content_markdown') }}
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
   ./scripts/setup.sh
   ```

3. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

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
