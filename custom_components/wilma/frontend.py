"""Serve the integration's Lovelace cards and add them to the frontend."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback
from homeassistant.loader import async_get_integration
from homeassistant.setup import async_when_setup
from homeassistant.util.hass_dict import HassKey

from .const import DOMAIN

FRONTEND_DIR = Path(__file__).parent / "frontend"
URL_BASE = f"/{DOMAIN}_frontend"
CARDS_MODULE = "wilma-cards.js"

DATA_FRONTEND: HassKey[bool] = HassKey(f"{DOMAIN}_frontend")


@callback
def async_setup_frontend(hass: HomeAssistant) -> None:
    """Serve the cards and load them in the frontend, once per Home Assistant instance.

    Safe to call for every config entry. Registration waits for the frontend integration
    and never happens without it, so the integration also works where there is no UI.
    """
    if DATA_FRONTEND in hass.data:
        return
    hass.data[DATA_FRONTEND] = True
    async_when_setup(hass, "frontend", _async_register)


async def _async_register(hass: HomeAssistant, _component: str) -> None:
    """Serve the frontend folder and add the cards module to every frontend page."""
    integration = await async_get_integration(hass, DOMAIN)
    # The version changes the module URL with every release, so browsers load the new
    # cards instead of a cached copy.
    version = integration.version or "0"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_BASE, str(FRONTEND_DIR), cache_headers=False)]
    )
    add_extra_js_url(hass, cards_url(version))


def cards_url(version: object) -> str:
    """The URL the frontend loads the cards module from."""
    return f"{URL_BASE}/{CARDS_MODULE}?v={version}"
