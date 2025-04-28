"""Fixtures for Wilma integration tests."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wilma.const import (
    CONF_PASSWORD,
    CONF_SERVER_URL,
    CONF_USERNAME,
    DOMAIN,
)


@pytest.fixture
def mock_config_entry():
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_SERVER_URL: "https://test.inschool.fi",
            CONF_USERNAME: "testuser",
            CONF_PASSWORD: "testpass",
        },
        entry_id="test",
    )


class MockWilmaMessage:
    """Mock Wilma message."""

    def __init__(self, msg_id, subject, sender, timestamp, unread=False, content_html=None):
        """Initialize mock message."""
        self.id = msg_id
        self.subject = subject
        self.sender = sender
        self.timestamp = timestamp
        self.unread = unread
        self.content_html = content_html

    def format_timestamp(self):
        """Return timestamp."""
        # Mock implementation
        return self.timestamp

    @property
    def content_markdown(self):
        """Return content as markdown."""
        if not self.content_html:
            raise ValueError("Message content is not available")
        return f"Markdown version of: {self.content_html}"


@pytest.fixture
def mock_wilma_client():
    """Return a mock Wilma client."""
    messages = [
        MockWilmaMessage(
            1,
            "Test Message 1",
            "Sender 1",
            "2023-01-01 12:00",
            True,
            "<p>Test content 1</p>"
        ),
        MockWilmaMessage(
            2,
            "Test Message 2",
            "Sender 2",
            "2023-01-02 12:00",
            False,
            "<p>Test content 2</p>"
        ),
    ]

    client = MagicMock()
    client.login = AsyncMock()
    client.get_messages = AsyncMock(return_value=messages)
    client.get_message_content = AsyncMock(return_value=messages[0])
    client.close = AsyncMock()
    
    with patch("wilma.WilmaClient", return_value=client):
        yield client


@pytest.fixture
def mock_wilma_exception_client():
    """Return a mock Wilma client that raises exceptions."""
    from wilma import AuthenticationError
    
    client = MagicMock()
    client.login = AsyncMock(side_effect=AuthenticationError("Auth failed"))
    
    with patch("wilma.WilmaClient", return_value=client):
        yield client


@pytest.fixture
def mock_setup_integration(hass, mock_config_entry, mock_wilma_client):
    """Set up the Wilma integration in Home Assistant."""

    async def _setup_integration():
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        return mock_config_entry

    return _setup_integration