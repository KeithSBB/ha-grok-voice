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
CONF_SYSTEM_PROMPT = "system_prompt"

# Entity unique ID prefixes
UNIQUE_ID_PREFIX = "grok_voice"

# Platform list (Phase A) — system prompt moved to Options Flow
PLATFORMS = ["sensor", "number", "select"]

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

# Model options (must include values the microservice actually uses)
MODEL_OPTIONS = [
    "grok-voice-latest",
    "grok-voice-think-fast-1.0",
    "grok-voice-think-fast-2.0",
    "latest",
]

# System prompt max length (for Options Flow validation)
SYSTEM_PROMPT_MAX_LENGTH = 8192