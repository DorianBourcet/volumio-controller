# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A Python hardware controller for [Volumio](https://volumio.com/) (open-source music server) running on a Raspberry Pi. It drives 4 Adafruit Seesaw rotary encoders (I2C) and 3 Adafruit HT16K33 12-character LED alphanumeric displays to provide physical playback control without a screen.

Designed to run as a systemd service on Volumio OS 4. Target Python is **3.11** (Volumio OS 4 ships Python 3.11.2 on Debian bookworm). Use modern typing: built-in generics (`list[str]`, `dict[str, Any]`, PEP 585) and `X | None` unions (PEP 604) - not `List`/`Dict`/`Optional` from `typing`. `typing.Any` is still imported from `typing` (no built-in equivalent).

## Running the project

```bash
# Run directly (requires Pi hardware + Volumio reachable)
python3 .

# Install as a systemd service on the Volumio device
bash install.sh

# Service management (after install)
systemctl start volumio-controller
systemctl stop volumio-controller
systemctl restart volumio-controller
systemctl status volumio-controller

# Tail structured logs
journalctl -u volumio-controller -f
```

Runtime dependencies: `pip3 install -r requirements.txt`. Dev/test dependencies (pytest, responses): `pip install -r requirements-dev.txt`.

## Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `VC_LOG_LEVEL` | `INFO` | Log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `VC_VOLUMIO_URL` | `http://localhost:3000` | Base URL for Socket.IO + REST |
| `VC_VOLUMIO_HTTP_TIMEOUT` | `10` | Per-request timeout (seconds) for `VolumioRestClient` |

Set these via `Environment=` in `service.txt` / `install.sh`.

## Tests

Run from any dev machine (macOS/Linux):

```bash
pip install -r requirements-dev.txt
python3 -m pytest -v
```

`tests/conftest.py` stubs hardware-only modules (`board`, `busio`, `adafruit_ht16k33`, `adafruit_seesaw`) so the suite imports cleanly without a Pi. Tests cover `utils`, `volumio_client` (HTTP behaviour via `responses`), `volumio_menu` (cache + invalidation), and `volumio_thread` (state, threading, regression tests for the previous-track and queue-bounds fixes). `tests/test_imports.py` is a smoke test that the whole module graph imports cleanly.

## Architecture

The application is **multi-threaded and event-driven**, built around a hierarchical state machine. All Python modules are at the root level (flat structure), plus a `tests/` folder.

### Thread model

| File | Thread/Class | Role |
|------|-------------|------|
| `__main__.py` | Entry point | Configures logging, creates `DisplayState`, starts `MainThread`, waits on the kill Event, drives graceful shutdown |
| `logging_setup.py` | - | Configures stdlib logging once (stderr → journald), level via `VC_LOG_LEVEL` |
| `graceful_killer.py` | `GracefulKiller` (singleton `killer`) | SIGINT/SIGTERM handler, owns a `kill_event: threading.Event` and a `shutdown_machine` flag |
| `main_thread.py` | `MainThread` | Orchestrator; cooperative `stop()` signals all sub-threads via Events and joins them |
| `volumio_thread.py` | `VolumioThread` | Socket.IO client; **`RLock`-protected** state and queue; bounded exponential backoff on connect; re-emits `getState`/`getQueue` on every (re)connect; `_safe_emit` no-ops while disconnected |
| `volumio_client.py` | `VolumioRestClient` | REST transport: `requests.Session`, `urllib3 Retry` (5xx + connect errors), explicit timeout, returns `None`/`False` on failure rather than raising |
| `volumio_menu.py` | `VolumioMenu` | Library browsing; accepts a `VolumioRestClient` via DI; keeps a per-URI dict cache |
| `vigie_thread.py` | `VigieThread` | Monitors Volumio state changes; cooperative stop via Event |
| `user_input_listener.py` | `UserInputListener` | 4 polling threads at 50 ms; per-tick `try/except` on encoder I2C errors so a glitch doesn't kill the listener |
| `user_input.py` | `UserInput` | Low-level Adafruit Seesaw I2C driver for a single encoder |
| `menu_thread.py` | `MenuThread` | Interactive music library browser; auto-closes after 30 s inactivity |
| `unlocker.py` | `Unlocker` + `UnlockerThread` | 12-step safety unlock on any input |

Every long-running `run()` is wrapped in `try/except Exception: logger.exception(...)` - a crashing thread is logged, not silently lost.

### State machine (`radio_state_machine.py`)

Uses the `transitions` library. States:

```
connecting
home
  ├── playing   (music is playing)
  ├── holding   (paused)
  └── sleeping  (stopped/idle - display dims)
menu
shutting_down
```

User input flows: `UserInputListener` → `RadioStateMachine` triggers → side effects on `DisplayState` and `VolumioThread`. `shutting_down` calls `graceful_killer.killer.request_shutdown(halt_machine=True)` to wake `__main__`'s wait, which then halts the Pi.

### Display system (`display_state.py` + `display_thread.py` and subclasses)

`DisplayState` is the single coordinator for the 12-char LED display. `set_activity_level(ActivityLevel)` applies one of three levels - `CONTROL` (brightness 1.0, marquee 0.15, encoders unlocked), `LISTENING` (0.5 / 0.20, locked), `STANDBY` (0.05 / 0.20, locked) - and the I2C write are **serialised under a `Lock`**. `_safe_i2c_write` retries once on `OSError` before dropping the frame - Pi I2C glitches no longer crash the controller. `shutdown()` blanks the screen on exit.

Activity levels (three, driven by `activity_timeout_thread.py` + `radio_state_machine.py`): any button press bumps to `CONTROL` for 30 s (bright, unlocked). After 30 s of inactivity the display **locks** and drops to its resting level. While locked, `RadioStateMachine.reconcile_activity_level()` picks the resting level from the **machine state**: `STANDBY` when stopped or paused (`home_sleeping` / `home_holding`), `LISTENING` only while actually playing (`home_playing`). It is called both from the machine's `after_state_change` hook (`_refresh_locked_activity`, immediate reaction) and from every `VigieThread` tick (continuous reconciliation). `VigieThread` first runs `refresh_home()` - which re-maps the live Volumio status to a substate (`stop` → `home_sleeping`) - then reconciles, so a locked display converges to `STANDBY` within one poll once Volumio settles on `stop`, with no button press (a `LISTENING` → `STANDBY` transition that never passes through `CONTROL`). `DisplayState.set_activity_level` skips no-op writes (`_current_activity_level`) so per-tick reconciliation costs no extra I2C traffic. This is distinct from the manual screen-blank feature (`enable_sleep_mode`/`disable_sleep_mode`, encoder 3).

Display thread subclasses (handle scrolling marquee, elapsed time, datetime clock, brightness transitions, etc.) - `display_thread.py` holds the shared `_pretty_print`/`_pretty_marquee` logic and the `try/except` wrapper around `run()`.

### Volumio integration

- **Real-time state**: Socket.IO (`python-socketio==4.6.1`, pinned because Volumio's server speaks Socket.IO v2) connecting to `VC_VOLUMIO_URL`. `_init_socketIO` retries with exponential backoff (1s → 30s cap), logging each attempt. Reconnects re-emit `getState`/`getQueue` to refresh state.
- **Library browsing**: REST via `VolumioRestClient` (Session + retries + timeout). `VolumioMenu` keeps a per-URI dict cache.

### Display constraints

The 12-character limit is a hard physical constraint (`DISPLAY_WIDTH = 12` in `display_thread.py` and `utils.py`). `utils.py` provides helpers for text fitting, truncation, and regex-based splitting; regexes are pre-compiled. `Unidecode` strips accents/diacritics before display.
