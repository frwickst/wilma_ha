"""Constants for the Wilma integration."""

from datetime import timedelta

DOMAIN = "wilma"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SERVER_URL = "server_url"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=30)

ATTR_CONTENT = "content"
ATTR_CONTENT_MARKDOWN = "content_markdown"
ATTR_SENDER = "sender"
ATTR_SUBJECT = "subject"
ATTR_TIMESTAMP = "timestamp"
ATTR_ID = "id"

SENSOR_LATEST_MESSAGE = "latest_message"

STORAGE_KEY = f"{DOMAIN}_messages"
STORAGE_VERSION = 1
