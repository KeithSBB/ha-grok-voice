"""Constants for the Grok Voice integration."""

DOMAIN = "grok_voice"

# Default connection settings
DEFAULT_HOST = "192.168.1.100"
DEFAULT_PORT = 10700
DEFAULT_SCAN_INTERVAL = 30  # seconds

# Config entry keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_TOKEN = "token"

# Entity unique ID prefixes
UNIQUE_ID_PREFIX = "grok_voice"

# Platform list (Phase A)
PLATFORMS = ["sensor", "number", "select", "text"]

# Voice options (xAI flagship set as of 2026)
VOICE_OPTIONS = [
    "ara",
    "atlas",
    "altair",
    "carina",
    "castor",
    "celeste",
    "cosmo",
    "helix",
    "helios",
    "iris",
    "kepler",
    "lumen",
    "luna",
    "lux",
    "naksh",
    "orion",
    "perseus",
    "rex",
    "rigel",
    "sal",
    "sirius",
    "ursa",
    "zagan",
    "eve",
    "leo",
]

# Model options (extend as new models appear)
MODEL_OPTIONS = [
    "grok-voice-think-fast-1.0",
    "grok-voice-think-fast-2.0",
    "latest",
]

# System prompt max length (HA TextEntity native_max)
SYSTEM_PROMPT_MAX_LENGTH = 8192
