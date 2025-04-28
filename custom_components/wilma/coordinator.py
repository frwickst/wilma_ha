"""DataUpdateCoordinator for the Wilma integration."""

import logging
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from wilhelmina import AuthenticationError, WilmaClient, WilmaError

from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class WilmaCoordinator(DataUpdateCoordinator):
    """Coordinator for fetching data from Wilma."""

    def __init__(
        self,
        hass: HomeAssistant,
        server_url: str,
        username: str,
        password: str,
        entry_id: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.server_url = server_url
        self.username = username
        self.password = password
        self.entry_id = entry_id
        self.client = None
        self.store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry_id}")
        self.last_update_success_time = None

    async def _async_update_data(self):
        """Fetch data from Wilma."""
        data = await self.store.async_load() or {}
        stored_messages = data.get("messages", [])

        try:
            if self.client is None:
                self.client = WilmaClient(self.server_url)
                _LOGGER.debug(
                    f"Connecting to Wilma server {self.server_url} as {self.username}"
                )
                await self.client.login(self.username, self.password)

            # Get the timestamp of the latest message if available
            # Otherwise, use one week ago as default
            after_timestamp = None
            if stored_messages and stored_messages[0].get("timestamp"):
                try:
                    after_timestamp = datetime.fromisoformat(
                        stored_messages[0]["timestamp"]
                    )
                    _LOGGER.debug(f"Fetching messages after: {after_timestamp}")
                except (ValueError, TypeError) as err:
                    _LOGGER.error(f"Error parsing timestamp: {err}")
            else:
                # If no stored messages, use one week ago as default
                after_timestamp = dt_util.utcnow() - dt_util.dt.timedelta(days=7)
                _LOGGER.debug(
                    f"No stored messages, fetching messages from one week ago: {after_timestamp}"
                )
            messages = await self.client.get_messages(
                with_content=True, after=after_timestamp
            )

            _LOGGER.debug(f"Fetched {len(messages)} messages from Wilma")

            # Update stored messages
            got_new_messages = False
            for message in messages:
                msg_dict = message.__dict__
                # Convert datetime objects to strings for storage
                if "timestamp" in msg_dict and isinstance(
                    msg_dict["timestamp"], datetime
                ):
                    _LOGGER.debug("Converting timestamp to string")
                    msg_dict["timestamp"] = msg_dict["timestamp"].isoformat()

                _LOGGER.debug("Adding markdown content to message")
                msg_dict["content_markdown"] = message.content_markdown
                stored_messages.append(msg_dict)
                got_new_messages = True

            _LOGGER.debug(f"Stored {len(stored_messages)} messages in storage")

            # Save updated messages
            if got_new_messages:
                await self.store.async_save({"messages": stored_messages})

            # Update last successful update time
            self.last_update_success_time = dt_util.utcnow()

            _LOGGER.debug(f"storing messages: {stored_messages}")

            return {
                "messages": stored_messages,
                "latest_message": stored_messages[0] if stored_messages else None,
                "last_update": dt_util.as_local(self.last_update_success_time),
            }

        except AuthenticationError as err:
            self.client = None
            _LOGGER.error("Authentication to Wilma failed: %s", err)
            raise UpdateFailed("Authentication failed") from err
        except WilmaError as err:
            _LOGGER.error("Error communicating with Wilma: %s", err)
            raise UpdateFailed(f"Error communicating with Wilma: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error updating from Wilma: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def async_close_client(self):
        """Close the Wilma client."""
        if self.client:
            try:
                await self.client.close()
            except Exception as err:
                _LOGGER.error("Error closing Wilma client: %s", err)
            finally:
                self.client = None
