# Volumio Controller

A physical hardware controller for [Volumio](https://volumio.com/), built around rotary encoders and a 12-character alphanumeric LED display. Designed to run on a Raspberry Pi alongside a Volumio music server, it provides a hands-on physical interface for playback control, volume, seeking, and library browsing — no screen or keyboard required.

## Features

- Real-time playback control via 4 rotary encoders
- 12-character 14-segment LED display showing track info, artist, elapsed time, and clock
- Scrolling marquee for long titles
- Interactive music library browser with per-URI cache
- Sleep mode with display dimming
- Safety lock (unlocker mechanism)
- Graceful shutdown (cooperative thread stop, blanks the display, optionally halts the Pi)
- Resilient Volumio connection: bounded exponential backoff on connect, automatic state re-sync on reconnect, I²C bus errors retried once before being dropped
- Structured logging routed to systemd-journald (`VC_LOG_LEVEL` env var)
- Runs as a systemd service on boot

## Hardware

| Component | Details |
|-----------|---------|
| Rotary encoders | 4x Adafruit Seesaw (I2C addresses `0x36`, `0x37`, `0x38`, `0x3a`) |
| LED display | 3x Adafruit HT16K33 14-segment 4-char modules, 12 chars total (I2C addresses `0x70`, `0x71`, `0x72`) |
| Host | Raspberry Pi running Volumio |

## Controls

| Encoder | Rotation | Press |
|---------|----------|-------|
| 1 | Volume up / down | System shutdown |
| 2 | Seek forward / backward | Back / cancel |
| 3 | Toggle sleep mode | Open music library menu |
| 4 | Next / previous track | Play / Pause / Stop |

## Architecture

The application is **multi-threaded and event-driven**, built around a hierarchical state machine.

```
__main__.py                     — entry point, configures logging, runs graceful shutdown
└── main_thread.py              — orchestrator with cooperative stop()
    ├── volumio_thread.py       — Socket.IO connection (RLock-protected state, bounded backoff)
    ├── volumio_client.py       — REST transport (urllib3 Retry, timeout, env-configurable URL)
    ├── volumio_menu.py         — library browsing with per-URI cache (DI on the REST client)
    ├── radio_state_machine.py  — hierarchical state machine
    ├── user_input_listener.py  — input polling threads
    ├── display_state.py        — display coordinator (I²C lock + safe-write retry)
    │   ├── PersistentDisplayThread
    │   ├── TemporaryDisplayThread
    │   ├── ContinuousMarqueeDisplayThread
    │   ├── PlayingTrackDisplayThread
    │   ├── PlayingTrackElapsedTimeDisplayThread
    │   ├── DatetimeDisplayThread
    │   └── ActiveToQuietDisplayThread
    ├── menu_thread.py          — interactive library browser UI
    ├── vigie_thread.py         — monitors Volumio state changes
    ├── unlocker.py             — 12-step safety unlock
    └── graceful_killer.py      — signal handler + shared kill Event
```

### State machine states

- `connecting` — waiting for Volumio connection
- `home_playing` — music is playing
- `home_holding` — music is paused
- `home_sleeping` — stopped / idle
- `menu` — browsing music library
- `shutting_down` — graceful shutdown in progress

## Installation

### Software prerequisites

- Volumio OS 4 for Raspberry Pi (I²C must be enabled)

### Hardware prerequisites

- 1 x Raspberry Pi compatible with Volumio OS 4
- 3 x Adafruit 14-segment LED Alphanumeric Backpack - STEMMA QT
- 3 x Dual Alphanumeric Display - White 0.54" Digit Height - Pack of 2
- 4 x Adafruit I2C Stemma QT Rotary Encoder Breakout
- 4 x Rotary Encoders compatible with Stemma QT Rotary Encoder Breakout

### Automated install

Run the install script from the Volumio device:

```bash
bash install.sh
```

The script verifies that `/dev/i2c-1` is available, clones (or pulls) the repository, installs the Python dependencies, deploys the systemd unit, and starts it automatically.

### Manual install

```bash
sudo apt update && sudo apt install -y python3-pip
pip3 install -r requirements.txt
python3 .
```

## Configuration

Behavior is tuned through environment variables (set them in the systemd unit's `Environment=` lines):

| Variable | Default | Purpose |
|---|---|---|
| `VC_LOG_LEVEL` | `INFO` | Log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `VC_VOLUMIO_URL` | `http://localhost:3000` | Base URL for both Socket.IO and REST |
| `VC_VOLUMIO_HTTP_TIMEOUT` | `10` | Per-request timeout (seconds) for REST calls |

## Logs

The service writes structured logs to stderr, captured by systemd-journald:

```bash
journalctl -u volumio-controller -f
```

## Tests

A `pytest` suite covers the modules that don't depend on the Pi hardware (utilities, Volumio REST client, menu cache, Volumio thread state-management — including regression tests for the previous-track and queue-bounds bugs). Hardware modules (`board`, `busio`, `adafruit_*`) are stubbed in `tests/conftest.py`, so the suite runs on any dev machine.

### Recommended workflow: `uv`

[`uv`](https://docs.astral.sh/uv/) is a fast, isolated Python package manager. The virtualenv is local to the project (`.venv/`, ignored by git) and can be wiped at any time.

```bash
# Install uv once (Astral installer)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Per-project: create venv + install dev deps + run tests
uv venv
uv pip install -r requirements-dev.txt
uv run pytest -v

# Drop the env when done
rm -rf .venv
```

`uv run <cmd>` activates the venv transparently, so you don't need to `source .venv/bin/activate`.

### Alternative: stdlib `venv`

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -v
deactivate
```

### Docker: run against the target Python version

The device runs Python 3.11 (Volumio OS 4 / Debian bookworm), which may differ from
your host's Python. The provided `Dockerfile` + `docker-compose.yml` run the suite in
a `python:3.11-slim-bookworm` container, similar to Volumio OS 4.
Only `requirements-dev.txt` is installed, the Adafruit hardware packages are stubbed by `tests/conftest.py`.

```bash
# Run the whole suite in the target Python (3.11)
docker compose run --rm tests

# Rebuild the image after changing requirements-dev.txt
docker compose build
```

The source tree is bind-mounted, so code and test edits are picked up without rebuilding.

## Dependencies

Runtime (`requirements.txt`):

| Package | Version | Purpose |
|---------|---------|---------|
| `Adafruit-Blinka` | 8.69.0 | GPIO / I²C abstraction layer |
| `adafruit-circuitpython-ht16k33` | 4.6.15 | 14-segment LED display driver |
| `adafruit-circuitpython-seesaw` | 1.16.8 | Rotary encoder driver |
| `python-socketio` | 4.6.1 | Real-time communication with Volumio (pinned: Volumio's server speaks Socket.IO v2) |
| `transitions` | 0.9.3 | Hierarchical state machine |
| `Unidecode` | 1.4.0 | Accent/diacritic removal for display |
| `requests` | 2.32.5 | Volumio REST API calls |
| `pytz` | 2025.2 | Timezone support for clock display |

Dev (`requirements-dev.txt`): `pytest`, `pytest-mock`, `responses`.
