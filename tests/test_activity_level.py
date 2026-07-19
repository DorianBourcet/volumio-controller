"""Tests for the three-level activity system (Control / Listening / Standby).

Covers the brightness + marquee mapping and idempotence in
``DisplayState.set_activity_level``, and the resting-level reconciliation in
``RadioStateMachine`` — including the external-stop path that regressed
(clock shown but stuck at Listening instead of Standby)."""
import time
from threading import Event
from unittest.mock import MagicMock, patch

import pytest

import radio_state_machine
from display_state import ActivityLevel, DisplayState
from unlocker import UnlockerThread


@pytest.mark.parametrize(
  'level, brightness, marquee',
  [
    (ActivityLevel.CONTROL, 1.0, 0.15),
    (ActivityLevel.LISTENING, 0.5, 0.20),
    (ActivityLevel.STANDBY, 0.05, 0.20),
  ],
)
def test_set_activity_level_applies_brightness_and_marquee(level, brightness, marquee):
  display = DisplayState()
  display.set_activity_level(level)
  assert display._display.brightness == brightness
  assert display.marquee_sleep_delay == marquee


def test_set_activity_level_is_idempotent():
  display = DisplayState()
  display.set_activity_level(ActivityLevel.CONTROL)
  # A repeated call at the same level must not touch the hardware again.
  display._display.brightness = 'sentinel'
  display.set_activity_level(ActivityLevel.CONTROL)
  assert display._display.brightness == 'sentinel'


def _make_state_machine():
  volumio = MagicMock()
  volumio.is_playing.return_value = True
  volumio.is_on_pause.return_value = False
  volumio.has_status_stop.return_value = False
  volumio.get_status.return_value = 'play'
  display = MagicMock()
  # Patch threads spawned during construction / transitions so tests don't
  # leak real background threads and don't race with our assertions.
  with patch.object(radio_state_machine, 'ActivityTimeoutThread'), \
       patch.object(radio_state_machine, 'DatetimeDisplayThread'), \
       patch.object(radio_state_machine, 'PlayingTrackDisplayThread'):
    sm = radio_state_machine.RadioStateMachine(volumio, display, Event())
  display.reset_mock()
  return sm, display, volumio


def test_reconcile_standby_when_sleeping():
  sm, display, _volumio = _make_state_machine()
  with patch.object(radio_state_machine, 'DatetimeDisplayThread'):
    sm.machine.set_state('home_sleeping')
  sm._is_locked_event.set()
  display.reset_mock()
  sm.reconcile_activity_level()
  display.set_activity_level.assert_called_once_with(ActivityLevel.STANDBY)


def test_reconcile_listening_when_not_sleeping():
  sm, display, _volumio = _make_state_machine()
  with patch.object(radio_state_machine, 'PlayingTrackDisplayThread'):
    sm.machine.set_state('home_playing')
  sm._is_locked_event.set()
  display.reset_mock()
  sm.reconcile_activity_level()
  display.set_activity_level.assert_called_once_with(ActivityLevel.LISTENING)


def test_reconcile_noop_when_unlocked():
  sm, display, _volumio = _make_state_machine()
  with patch.object(radio_state_machine, 'DatetimeDisplayThread'):
    sm.machine.set_state('home_sleeping')
  sm._is_locked_event.clear()
  display.reset_mock()
  sm.reconcile_activity_level()
  display.set_activity_level.assert_not_called()


def test_external_stop_while_locked_reaches_standby():
  """Regression: locked + playing, Volumio stops externally (via vigie's
  refresh_home) -> the display must settle on STANDBY, not stay at LISTENING."""
  sm, display, volumio = _make_state_machine()
  with patch.object(radio_state_machine, 'DatetimeDisplayThread'):
    sm.machine.set_state('home_playing')
    sm._is_locked_event.set()
    display.reset_mock()
    # Volumio is now stopped; vigie would notice and call refresh_home().
    volumio.is_playing.return_value = False
    volumio.is_on_pause.return_value = False
    volumio.has_status_stop.return_value = True
    volumio.get_status.return_value = 'stop'
    sm.refresh_home()
  assert sm.state == 'home_sleeping'
  levels = [c.args[0] for c in display.set_activity_level.call_args_list]
  assert levels, 'expected set_activity_level to be called'
  assert levels[-1] is ActivityLevel.STANDBY


def test_external_play_while_locked_reaches_listening():
  """Symmetric case: resting in STANDBY (locked, stopped), playback starts from
  the app -> the display must lift to LISTENING (still locked)."""
  sm, display, volumio = _make_state_machine()
  with patch.object(radio_state_machine, 'DatetimeDisplayThread'), \
       patch.object(radio_state_machine, 'PlayingTrackDisplayThread'):
    sm.machine.set_state('home_sleeping')
    sm._is_locked_event.set()
    display.reset_mock()
    # Volumio starts playing; vigie notices and calls refresh_home().
    volumio.is_playing.return_value = True
    volumio.is_on_pause.return_value = False
    volumio.has_status_stop.return_value = False
    volumio.get_status.return_value = 'play'
    volumio.can_play.return_value = True
    volumio.queue_is_not_empty.return_value = True
    sm.refresh_home()
  assert sm.state == 'home_playing'
  assert sm._is_locked_event.is_set()
  levels = [c.args[0] for c in display.set_activity_level.call_args_list]
  assert levels, 'expected set_activity_level to be called'
  assert levels[-1] is ActivityLevel.LISTENING


def test_reflected_stop_does_not_command_volumio():
  """A silent (externally-reflected) stop must NOT re-command Volumio: calling
  hold_on() there emits `pause` back and flips the state to home_holding."""
  sm, _display, volumio = _make_state_machine()
  with patch.object(radio_state_machine, 'DatetimeDisplayThread'), \
       patch.object(radio_state_machine, 'PlayingTrackDisplayThread'):
    sm.machine.set_state('home_playing')
    volumio.reset_mock()
    volumio.is_playing.return_value = False
    volumio.is_on_pause.return_value = False
    volumio.has_status_stop.return_value = True
    volumio.get_status.return_value = 'stop'
    sm.refresh_home()  # vigie path -> silent
  assert sm.state == 'home_sleeping'
  volumio.hold_on.assert_not_called()


def test_user_stop_commands_volumio():
  """A user-initiated stop (button 4, silent=False) still commands Volumio."""
  sm, _display, volumio = _make_state_machine()
  with patch.object(radio_state_machine, 'DatetimeDisplayThread'), \
       patch.object(radio_state_machine, 'PlayingTrackDisplayThread'):
    sm.machine.set_state('home_playing')
    volumio.reset_mock()
    sm.stop_track(silent=False)
  assert sm.state == 'home_sleeping'
  volumio.hold_on.assert_called_once()


def test_external_interactive_stop_stays_standby_no_bounce():
  """Full regression for the reported bug: locked + playing an interactive source,
  Volumio stops externally. Reflecting it must NOT emit `pause` (which would bounce
  the machine to home_holding / LISTENING). Driven through the vigie tick logic."""
  sm, display, volumio = _make_state_machine()
  volumio.is_interactive_broadcast.return_value = True
  # If hold_on() were (wrongly) called, it would emit pause -> status 'pause'.
  volumio.hold_on.side_effect = lambda: volumio.get_status.configure_mock(return_value='pause')
  with patch.object(radio_state_machine, 'DatetimeDisplayThread'), \
       patch.object(radio_state_machine, 'PlayingTrackDisplayThread'):
    sm.machine.set_state('home_playing')
    sm._is_locked_event.set()
    display.reset_mock()
    volumio.is_playing.return_value = False
    volumio.is_on_pause.return_value = False
    volumio.has_status_stop.return_value = True
    volumio.get_status.return_value = 'stop'
    # Simulate several vigie ticks (refresh_home + reconcile).
    for _ in range(5):
      sm.refresh_home()
      sm.reconcile_activity_level()
  assert sm.state == 'home_sleeping'
  volumio.hold_on.assert_not_called()
  levels = [c.args[0] for c in display.set_activity_level.call_args_list]
  assert levels and levels[-1] is ActivityLevel.STANDBY


def test_locked_pause_is_standby():
  """A pause (state 'home_holding') rests at STANDBY, same as a stop."""
  sm, display, _volumio = _make_state_machine()
  with patch.object(radio_state_machine, 'DatetimeDisplayThread'):
    sm.machine.set_state('home_holding')
  sm._is_locked_event.set()
  display.reset_mock()
  sm.reconcile_activity_level()
  display.set_activity_level.assert_called_once_with(ActivityLevel.STANDBY)


def test_start_activity_timeout_spawns_thread():
  sm, _display, _volumio = _make_state_machine()
  with patch.object(radio_state_machine, 'ActivityTimeoutThread') as timer_cls:
    sm._start_activity_timeout()
  timer_cls.assert_called_once()
  assert timer_cls.call_args.kwargs['apply_resting'] == sm.reconcile_activity_level
  timer_cls.return_value.start.assert_called_once()


def test_unlocker_is_wired_to_restart_activity_timeout():
  sm, _display, _volumio = _make_state_machine()
  assert sm._unlocker._on_unlock == sm._start_activity_timeout


def test_gesture_unlock_restarts_activity_timeout():
  """Regression: after the 12-bump gesture unlock the display must not stay
  stuck in CONTROL — a fresh ActivityTimeoutThread has to be started so it
  returns to its resting level after 30 s."""
  display = MagicMock()
  locked = Event()
  locked.set()
  has_run = Event()
  on_unlock = MagicMock()
  thread = UnlockerThread(display, locked, has_run, on_unlock)
  thread.start()
  # Feed bumps quickly (< DECREASE_AFTER_SEC) until the threshold is reached.
  for _ in range(4):
    thread.bump()
    time.sleep(0.02)
  thread.join(timeout=2)
  assert not thread.is_alive()
  assert not locked.is_set()          # unlocked
  on_unlock.assert_called_once()      # timer restarted exactly once
  display.set_activity_level.assert_called_with(ActivityLevel.CONTROL)
