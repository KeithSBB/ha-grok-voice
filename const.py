"""Constants for the Grok Voice integration."""

DOMAIN = "grok_voice"

DEFAULT_HOST = "192.168.1.100"
DEFAULT_PORT = 10700
DEFAULT_SCAN_INTERVAL = 30  # seconds
DEFAULT_STATE_PUSH_INTERVAL = 900  # 15 minutes

CONF_HOST = "host"
CONF_PORT = "port"
CONF_TOKEN = "token"
CONF_SYSTEM_PROMPT = "system_prompt"
CONF_PERSONALITY_MODULATORS = "personality_modulators"

UNIQUE_ID_PREFIX = "grok_voice"

PLATFORMS = ["sensor", "number", "select"]

VOICE_OPTIONS = [
    "ara", "atlas", "altair", "carina", "castor", "celeste", "cosmo",
    "helix", "helios", "iris", "kepler", "lumen", "luna", "lux", "naksh",
    "orion", "perseus", "rex", "rigel", "sal", "sirius", "ursa", "zagan",
    "eve", "leo",
]

MODEL_OPTIONS = [
    "grok-voice-latest",
    "grok-voice-think-fast-1.0",
    "grok-voice-think-fast-2.0",
    "latest",
]

SYSTEM_PROMPT_MAX_LENGTH = 8192


ASPECT_OPTIONS = [
    "warmth",
    "verbosity",
    "humor",
    "energy",
    "caution",
    "creativity",
]

ASPECT_LABELS = {
    "warmth": "Warmth",
    "verbosity": "Verbosity",
    "humor": "Humor",
    "energy": "Energy",
    "caution": "Caution",
    "creativity": "Creativity",
}

CURVE_OPTIONS = ["linear", "sigmoid", "step"]