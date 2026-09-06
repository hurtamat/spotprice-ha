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
ICON_START = "mdi:play-circle-outline"
ICON_STOP = "mdi:stop-circle-outline"
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
ENTITY_KEY_PRICE = "price"
ENTITY_KEY_PRICE_LEVEL = "price_level"
ENTITY_KEY_NEXT_START = "next_start"
ENTITY_KEY_NEXT_END = "next_end"
ENTITY_KEY_ENABLED_SWITCH = "enabled"
ENTITY_KEY_CONTINUOUS_SWITCH = "continuous_block"
ENTITY_KEY_UNAVAILABLE_SWITCH = "unavailable_window"
ENTITY_KEY_DURATION_NUMBER = "duration_hours"
ENTITY_KEY_READY_BY_TIME = "ready_by"
ENTITY_KEY_UNAVAILABLE_FROM_TIME = "unavailable_from"
ENTITY_KEY_UNAVAILABLE_TO_TIME = "unavailable_to"
ENTITY_KEY_REFRESH_BUTTON = "refresh_plan"

# Configuration keys
CONF_DEVICE_NAME = "device_name"
CONF_BASE_URL = "base_url"
CONF_ZONE_CODE = "zone_code"
# Optional: an entity SpotBuddy switches directly, so no automation is needed.
CONF_CONTROLLED_SWITCH = "controlled_switch"

# Price levels, mirroring the backend PriceQuantile enum (0/1/2).
PRICE_LEVELS = ["green", "yellow", "red"]

# The bundled Lovelace card, shipped inside the integration so HACS carries it.
CARD_FILENAME = "spotbuddy-card.js"
CARD_SOURCE_PATH = f"custom_components/{DOMAIN}/www/{CARD_FILENAME}"
CARD_URL = f"/{DOMAIN}/{CARD_FILENAME}"

# Backend
SCHEDULE_PATH = "/api/homeassistant/schedule"
# The zone list, which the config flow turns into a dropdown. Doubles as the reachability probe.
ZONES_PATH = "/api/zones"
ZONE_RESOLVE_PATH = "/api/zones/resolve"
API_TIMEOUT_SECONDS = 30

# Defaults
# TODO: the hosted backend; replace with `terraform output backend_url` before release.
DEFAULT_BASE_URL = "http://host.docker.internal:5262"
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
