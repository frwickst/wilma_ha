"""Tests for the Wilma config flow."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from wilhelmina import AuthenticationError, WilmaError

from custom_components.wilma.const import (
    CONF_PASSWORD,
    CONF_SERVER_URL,
    CONF_USERNAME,
    DOMAIN,
)

USER_INPUT = {
    CONF_SERVER_URL: "https://test.inschool.fi/",
    CONF_USERNAME: " testuser ",
    CONF_PASSWORD: "testpass",
}


@pytest.fixture
def flow_client() -> Generator[MagicMock]:
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.login = AsyncMock()
    client.get_messages = AsyncMock(return_value=[])
    with (
        patch("custom_components.wilma.config_flow.WilmaClient", return_value=client),
        patch("custom_components.wilma.async_setup_entry", return_value=True),
    ):
        yield client


async def _submit(hass: HomeAssistant, user_input: dict) -> dict:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    return await hass.config_entries.flow.async_configure(result["flow_id"], user_input)


async def test_create_entry(hass: HomeAssistant, flow_client: MagicMock) -> None:
    result = await _submit(hass, USER_INPUT)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Wilma (testuser)"
    assert result["data"] == {
        CONF_SERVER_URL: "https://test.inschool.fi",
        CONF_USERNAME: "testuser",
        CONF_PASSWORD: "testpass",
    }
    assert result["result"].unique_id == "https://test.inschool.fi|testuser"
    flow_client.login.assert_awaited_once_with("testuser", "testpass")


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (AuthenticationError("bad"), "invalid_auth"),
        (WilmaError("down"), "cannot_connect"),
        (RuntimeError("boom"), "unknown"),
    ],
)
async def test_errors(
    hass: HomeAssistant, flow_client: MagicMock, error: Exception, expected: str
) -> None:
    flow_client.login.side_effect = error

    result = await _submit(hass, USER_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected}


async def test_already_configured(
    hass: HomeAssistant, flow_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    mock_config_entry.add_to_hass(hass)

    result = await _submit(hass, {**USER_INPUT, CONF_USERNAME: "TestUser"})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    flow_client.login.assert_not_awaited()
