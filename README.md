# ha-grok-voice

Home Assistant custom component for the **Grok Voice Microservice**  
(xAI Realtime speech-to-speech + ESPHome Linux-Voice-Assistant / Voice PE satellites).

**Repository**: https://github.com/KeithSBB/ha-grok-voice  
**Microservice**: https://github.com/KeithSBB/grok-voice-microservice

## Purpose

Provides a clean UI inside Home Assistant for:

- Full **system prompt** editing (TextEntity with `native_max = 8192`)
- **Voice** and **Model** selection
- Conversation timeout & persistence numbers
- Service status, token usage, estimated cost, and active satellite count sensors

This component talks to the microservice over **REST** using a shared Bearer token  
(the same `notify_token` / `ha_token` already present in the microservice `secrets.yaml`).

MQTT Discovery remains the recommended path for per-satellite controls (mute, sensitivities, volumes, wake-word, status).  
This integration focuses on the AI-layer settings that cannot be exposed via MQTT text entities.

## Phase A Entities

| Platform | Entity                  | Notes                                      |
|----------|-------------------------|--------------------------------------------|
| `text`   | System Prompt           | Full prompt, max 8192 characters           |
| `select` | Voice                   | Full xAI flagship voice list               |
| `select` | Model                   | `grok-voice-think-fast-1.0` / `2.0` / `latest` |
| `number` | Conversation Timeout    | seconds (default 10)                       |
| `number` | Conversation Persistence| seconds (default 300)                      |
| `sensor` | Service Status          | online / offline / reconnecting / http_xxx |
| `sensor` | Input Tokens            | total increasing                           |
| `sensor` | Output Tokens           | total increasing                           |
| `sensor` | Estimated Cost          | USD                                        |
| `sensor` | Active Satellites       | connected count                            |

## Installation

### Manual

1. Copy the `custom_components/grok_voice` folder into your Home Assistant  
   `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for **Grok Voice**.
4. Enter:
   - Host / IP of the Fedora server running the microservice
   - Port (default `10700`)
   - Bearer token (value of `notify_token` or `ha_token` from `/etc/grok-voice-microservice/secrets.yaml`)

### HACS (recommended once published)

Add as a custom repository:  
`https://github.com/KeithSBB/ha-grok-voice` → type **Integration**.

## Prerequisites on the Microservice Side

The following REST endpoints are expected (they will be added to the microservice in a follow-up change):

- `GET  /health`   → `{ "status": "online", "active_satellites": N, ... }`
- `GET  /config`   → current system_prompt, voice, model, timeouts
- `PUT  /config`   → partial update of the above keys
- `GET  /usage`    → input/output tokens + estimated cost

Until those endpoints exist the component still loads and shows placeholder values.  
Config changes will fail gracefully until the microservice implements `PUT /config`.

## Architecture Notes

- Pure client – no MCP tool execution, no wake-word logic, no satellite protocol.
- Authentication re-uses the existing notify token pattern.
- Live updates are pushed by the microservice `ConfigManager` to running `VoiceAgent` sessions.
- Future phases will add PSI influencer configuration UI (Phase C).

## License

MIT – see [LICENSE](LICENSE).
