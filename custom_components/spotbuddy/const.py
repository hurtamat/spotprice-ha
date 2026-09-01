"""Constants for the SpotBuddy integration."""

from homeassistant.const import Platform
from homeassistant.const import __version__ as HA_VERSION

NAME = "SpotBuddy"
DOMAIN = "spotbuddy"
VERSION = "0.1.0"
ISSUE_URL = "https://github.com/hurtamat/spotprice-ha/issues"

# Icons
ICON = "mdi:flash"
ICON_CASH = "mdi:cash"
ICON_REFRESH = "mdi:refresh"
ICON_TIME = "mdi:clock-time-four-outline"
ICON_TIMER_OFF = "mdi:timer-off-outline"

# Platforms
BINARY_SENSOR = Platform.BINARY_SENSOR
BUTTON = Platform.BUTTON
NUMBER = Platform.NUMBER
SENSOR = Platform.SENSOR
SWITCH = Platform.SWITCH
TIME = Platform.TIME
PLATFORMS = [BINARY_SENSOR, SENSOR, NUMBER, SWITCH, TIME, BUTTON]

# Entity keys
ENTITY_KEY_RUNNING = "running"
ENTITY_KEY_STATUS = "status"
ENTITY_KEY_PRICE = "price"
ENTITY_KEY_PRICE_LEVEL = "price_level"
ENTITY_KEY_ENABLED_SWITCH = "enabled"
ENTITY_KEY_CONTINUOUS_SWITCH = "continuous_block"
ENTITY_KEY_DURATION_NUMBER = "duration_hours"
ENTITY_KEY_READY_BY_TIME = "ready_by"
ENTITY_KEY_UNAVAILABLE_FROM_TIME = "unavailable_from"
ENTITY_KEY_UNAVAILABLE_TO_TIME = "unavailable_to"
ENTITY_KEY_REFRESH_BUTTON = "refresh_plan"

# Configuration keys
CONF_DEVICE_NAME = "device_name"
CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
# Optional: an entity SpotBuddy switches directly, so no automation is needed.
CONF_CONTROLLED_SWITCH = "controlled_switch"

# Status sensor states. Kept as slugs so automations are language-independent.
STATUS_DISABLED = "disabled"
STATUS_WAITING_FOR_PLAN = "waiting_for_plan"
STATUS_NO_PLAN = "no_plan"
STATUS_WAITING_TO_START = "waiting_to_start"
STATUS_RUNNING = "running"
STATUS_UNAVAILABLE = "backend_unavailable"

# Price levels, mirroring the backend PriceQuantile enum (0/1/2).
PRICE_LEVELS = ["green", "yellow", "red"]

# Backend
SCHEDULE_PATH = "/api/homeassistant/schedule"
API_TIMEOUT_SECONDS = 30

# Defaults
DEFAULT_BASE_URL = "http://localhost:8080"
DEFAULT_DURATION_HOURS = 3.0
DEFAULT_READY_BY = "06:00:00"

# The backend publishes tomorrow's day-ahead prices in the early afternoon,
# so the plan is (re)fetched shortly after that and again after midnight.
PLAN_REFRESH_HOURS_UTC = [0, 13]
PLAN_REFRESH_MINUTE = 5

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
Home Assistant: {HA_VERSION}
-------------------------------------------------------------------
"""
