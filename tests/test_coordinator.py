"""Test the Wilma data update coordinator."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from wilma import AuthenticationError, WilmaError

from custom_components.wilma.coordinator import WilmaCoordinator


async def test_coordinator_update(hass, mock_wilma_client):
    """Test successful coordinator update."""
    # Create coordinator
    coordinator = WilmaCoordinator(
        hass, "https://test.inschool.fi", "testuser", "testpass", "test_entry_id"
    )
    
    # Test update
    data = await coordinator._async_update_data()
    
    # Verify results
    assert "messages" in data
    assert len(data["messages"]) == 2
    
    assert data["latest_message"].id == 1
    assert data["latest_message"].subject == "Test Message 1"
    
    assert data["latest_unread_message"].id == 1
    assert data["latest_unread_message"].unread is True
    
    assert "last_update" in data
    
    # Verify client was initialized and called properly
    assert coordinator.client is not None
    mock_wilma_client.login.assert_called_once_with("testuser", "testpass")
    mock_wilma_client.get_messages.assert_called_once()


async def test_coordinator_auth_error(hass):
    """Test authentication error handling in coordinator."""
    client = MagicMock()
    client.login = AsyncMock(side_effect=AuthenticationError("Auth failed"))
    
    with patch("wilma.WilmaClient", return_value=client):
        # Create coordinator
        coordinator = WilmaCoordinator(
            hass, "https://test.inschool.fi", "testuser", "testpass", "test_entry_id"
        )
        
        # Test update with auth error
        with pytest.raises(UpdateFailed, match="Authentication failed"):
            await coordinator._async_update_data()
        
        # Verify client was cleared
        assert coordinator.client is None


async def test_coordinator_wilma_error(hass):
    """Test general Wilma error handling in coordinator."""
    client = MagicMock()
    client.login = AsyncMock()
    client.get_messages = AsyncMock(side_effect=WilmaError("API Error"))
    
    with patch("wilma.WilmaClient", return_value=client):
        # Create coordinator
        coordinator = WilmaCoordinator(
            hass, "https://test.inschool.fi", "testuser", "testpass", "test_entry_id"
        )
        
        # Test update with API error
        with pytest.raises(UpdateFailed, match="Error communicating with Wilma"):
            await coordinator._async_update_data()


async def test_coordinator_close(hass, mock_wilma_client):
    """Test the coordinator's close method."""
    # Create coordinator
    coordinator = WilmaCoordinator(
        hass, "https://test.inschool.fi", "testuser", "testpass", "test_entry_id"
    )
    
    # Update to initialize client
    await coordinator._async_update_data()
    assert coordinator.client is not None
    
    # Close client
    await coordinator.async_close_client()
    
    # Verify client was closed and reset
    mock_wilma_client.close.assert_called_once()
    assert coordinator.client is None