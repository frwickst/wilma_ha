"""Constants for the Wilma integration."""

from datetime import timedelta

DOMAIN = "wilma"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SERVER_URL = "server_url"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=30)

# On first setup, only messages this recent get their content fetched (which marks them as
# read in Wilma); older messages are recorded as already seen.
INITIAL_MESSAGE_LOOKBACK = timedelta(days=7)
# Upper bound on content fetches per update, each of which marks a message as read
MAX_CONTENT_FETCHES_PER_UPDATE = 10
MAX_STORED_MESSAGES = 50
# Seen attendance mark keys older than this are forgotten
SEEN_MARK_RETENTION = timedelta(days=400)
# Weeks the calendar fetches beyond the current and next week are cached this long, and at
# most this many weeks are fetched or kept for one calendar query
WEEK_CACHE_TTL = timedelta(hours=1)
MAX_CACHED_WEEKS = 12

EVENT_NEW_MESSAGE = f"{DOMAIN}_new_message"
EVENT_NEW_ATTENDANCE_MARK = f"{DOMAIN}_new_attendance_mark"

ATTR_CONTENT = "content"
ATTR_CONTENT_MARKDOWN = "content_markdown"
ATTR_SENDER = "sender"
ATTR_SUBJECT = "subject"
ATTR_TIMESTAMP = "timestamp"
ATTR_ID = "id"

SENSOR_LATEST_MESSAGE = "latest_message"
SENSOR_LATEST_ATTENDANCE_MARK = "latest_attendance_mark"
SENSOR_LAST_UPDATE = "last_update"
SENSOR_LESSONS_TODAY = "lessons_today"
SENSOR_LESSONS_TOMORROW = "lessons_tomorrow"
SENSOR_LESSONS_THIS_WEEK = "lessons_this_week"
CALENDAR_SCHEDULE = "schedule"

STORAGE_KEY = f"{DOMAIN}_messages"
STORAGE_VERSION = 1
