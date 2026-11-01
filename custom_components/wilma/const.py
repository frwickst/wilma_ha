"""Constants for the Wilma integration."""

from datetime import timedelta

DOMAIN = "wilma"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SERVER_URL = "server_url"
CONF_SCAN_INTERVAL_MINUTES = "scan_interval_minutes"
CONF_RECENT_THRESHOLD_HOURS = "recent_threshold_hours"

DEFAULT_SCAN_INTERVAL_MINUTES = 30
DEFAULT_RECENT_THRESHOLD_HOURS = 24

# On first setup, only messages this recent get their content fetched (which marks them as
# read in Wilma); older messages are recorded as already seen.
INITIAL_MESSAGE_LOOKBACK = timedelta(days=7)
# Upper bound on content fetches per update, each of which marks a message as read
MAX_CONTENT_FETCHES_PER_UPDATE = 10
MAX_STORED_MESSAGES = 50
# Upper bound on bulletin content fetches per student and update
MAX_BULLETIN_FETCHES_PER_UPDATE = 5
MAX_CACHED_BULLETINS = 20
# Seen attendance mark keys older than this are forgotten
SEEN_MARK_RETENTION = timedelta(days=400)
# Weeks the calendar fetches beyond the current and next week are cached this long, and at
# most this many weeks are fetched or kept for one calendar query
WEEK_CACHE_TTL = timedelta(hours=1)
MAX_CACHED_WEEKS = 12

EVENT_NEW_MESSAGE = f"{DOMAIN}_new_message"
EVENT_NEW_ATTENDANCE_MARK = f"{DOMAIN}_new_attendance_mark"
EVENT_NEW_BULLETIN = f"{DOMAIN}_new_bulletin"

ATTR_CONTENT = "content"
ATTR_CONTENT_MARKDOWN = "content_markdown"
ATTR_SENDER = "sender"
ATTR_SUBJECT = "subject"
ATTR_TIMESTAMP = "timestamp"
ATTR_ID = "id"
ATTR_STUDENT_ID = "student_id"
ATTR_STUDENT_NAME = "student_name"

SENSOR_LATEST_MESSAGE = "latest_message"
SENSOR_LATEST_ATTENDANCE_MARK = "latest_attendance_mark"
SENSOR_LAST_UPDATE = "last_update"
SENSOR_LESSONS_TODAY = "lessons_today"
SENSOR_LESSONS_TOMORROW = "lessons_tomorrow"
SENSOR_LESSONS_THIS_WEEK = "lessons_this_week"
SENSOR_UNREAD_COUNT = "unread_count"
SENSOR_NEXT_LESSON = "next_lesson"
SENSOR_ATTENDANCE_COUNT = "attendance_count"
SENSOR_LATEST_BULLETIN = "latest_bulletin"
SENSOR_UNREAD_BULLETIN_COUNT = "unread_bulletin_count"
BINARY_SENSOR_RECENT_MESSAGE = "recent_message"
BINARY_SENSOR_RECENT_BULLETIN = "recent_bulletin"
BINARY_SENSOR_RECENT_ATTENDANCE = "recent_attendance"
BINARY_SENSOR_PROBLEM = "problem"
CALENDAR_SCHEDULE = "schedule"

# Entities that belonged to the single student before multi-student support; their unique
# IDs are migrated to the account's primary student.
LEGACY_STUDENT_ENTITY_KEYS = (
    SENSOR_LATEST_MESSAGE,
    SENSOR_LATEST_ATTENDANCE_MARK,
    SENSOR_LESSONS_TODAY,
    SENSOR_LESSONS_TOMORROW,
    SENSOR_LESSONS_THIS_WEEK,
    CALENDAR_SCHEDULE,
)

STORAGE_KEY = f"{DOMAIN}_messages"
STORAGE_VERSION = 1
