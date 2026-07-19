from threading import Event

from transitions.extensions import HierarchicalMachine

import graceful_killer
import logging_setup
import utils
from activity_timeout_thread import ActivityTimeoutThread
from datetime_display_thread import DatetimeDisplayThread
from display_state import ActivityLevel, DisplayState
from playing_track_display_thread import PlayingTrackDisplayThread
from playing_track_elapsed_time_display_thread import PlayingTrackElapsedTimeDisplayThread
from track_selector_thread import TrackSelectorThread
from unlocker import Unlocker
from volumio_thread import VolumioThread

logger = logging_setup.get_logger(__name__)


class RadioStateMachine(object):

  states = [
    'connecting',
    'shutting_down',
    {
      'name': 'home',
      'children': [
        'playing',
        'holding',
        'sleeping',
      ]
    },
    'menu',
  ]

  transitions = [
    {'trigger': 'wait_for_connection', 'source': '*', 'dest': 'connecting'},
    {'trigger': 'shut_down', 'source': '*', 'dest': 'shutting_down'},
    {'trigger': 'back_home', 'source': '*', 'dest': 'home'},
    {'trigger': 'refresh_home', 'source': ['home', 'home_*'], 'dest': 'home'},
    {'trigger': 'play_track', 'source': ['home', 'home_sleeping', 'home_holding'], 'dest': 'home_playing', 'conditions': 'can_play'},
    {'trigger': 'pause_track', 'source': ['home', 'home_playing'], 'dest': 'home_holding', 'conditions': 'can_pause'},
    {'trigger': 'stop_track', 'source': ['home', 'home_playing'], 'dest': 'home_sleeping'},
    {'trigger': 'turn_volume_up', 'source': ['home', 'menu'], 'dest': None, 'before': 'volume_up'},
    {'trigger': 'turn_volume_down', 'source': ['home', 'menu'], 'dest': None, 'before': 'volume_down'},
    {'trigger': 'fast_forward', 'source': ['home', 'menu'], 'dest': None, 'before': 'seek_up', 'conditions': 'is_playing'},
    {'trigger': 'rewind', 'source': ['home', 'menu'], 'dest': None, 'before': 'seek_down', 'conditions': 'is_playing'},
    {'trigger': 'open_menu', 'source': 'home', 'dest': 'menu'},
    {'trigger': 'enter_menu', 'source': 'menu', 'dest': None, 'before': 'select_menu'},
    {'trigger': 'back_menu', 'source': 'menu', 'dest': None, 'before': 'cancel_menu'},
    {'trigger': 'close_menu', 'source': 'menu', 'dest': 'home'},
  ]

  def __init__(self, volumio: VolumioThread, display: DisplayState, vigie_stop_event: Event) -> None:
    self._volumio = volumio
    self._display = display
    self._latest_activity_timeout_stop_event = Event()
    self._latest_track_selector_stop_event = Event()
    self._vigie_stop_event = vigie_stop_event
    self._is_locked_event = Event()
    self._unlocker = Unlocker(
      self._display, self._is_locked_event, on_unlock=self._start_activity_timeout
    )
    self._menu = None
    self.machine = HierarchicalMachine(
      model=self,
      send_event=True,
      states=RadioStateMachine.states,
      initial='connecting',
      transitions=RadioStateMachine.transitions,
      after_state_change='_refresh_locked_activity',
    )
    self._bump()

  def _issue_new_activity_timeout_stop_event(self) -> None:
    self._latest_activity_timeout_stop_event.set()
    self._latest_activity_timeout_stop_event = Event()

  def reconcile_activity_level(self) -> None:
    """Keep the resting brightness aligned with the state machine.

    No-op while unlocked (CONTROL), so a state change during the active window
    doesn't dim the display. While locked, the resting level is driven by the
    machine state: STANDBY when stopped or paused (``home_sleeping`` /
    ``home_holding``), LISTENING while actually playing.
    Idempotent (``DisplayState`` skips no-op writes), so it is safe to call on
    every ``VigieThread`` tick and from the ``after_state_change`` hook."""
    if not self._is_locked():
      return
    resting_standby = self.state in ('home_sleeping', 'home_holding')
    level = ActivityLevel.STANDBY if resting_standby else ActivityLevel.LISTENING
    self._display.set_activity_level(level)

  def _refresh_locked_activity(self, event) -> None:
    self.reconcile_activity_level()

  def _issue_new_track_selector_stop_event(self) -> None:
    self._latest_track_selector_stop_event.set()
    self._latest_track_selector_stop_event = Event()

  def _is_locked(self) -> bool:
    return self._is_locked_event.is_set()

  def _bump(self, force_unlock: bool = False) -> None:
    if force_unlock:
      self._is_locked_event.clear()
    if self._is_locked():
      self._bump_unlocker()
    else:
      self._start_activity_timeout()

  def _start_activity_timeout(self) -> None:
    """Start the 30 s inactivity window: CONTROL now, resting level once it
    elapses. Called whenever we become (or stay) unlocked — including after the
    Unlocker's gesture unlock — so 'unlocked implies a live timer' always holds
    and the display reliably returns to its resting level."""
    self._issue_new_activity_timeout_stop_event()
    ActivityTimeoutThread(
      self._display,
      self._latest_activity_timeout_stop_event,
      self._is_locked_event,
      apply_resting=self.reconcile_activity_level,
    ).start()

  def _bump_unlocker(self) -> None:
    self._unlocker.bump()

  def on_enter_connecting(self, event) -> None:
    self._display.display_persistent_texts(
      texts=['.  ', '.. ', '...', ' ..', '  .', ''],
      duration=0.25,
      continuous_marquee=False,
    )

  def on_enter_shutting_down(self, event) -> None:
    self._display.display_persistent_texts(texts=['BYE BYE'])
    self._volumio.stop()
    graceful_killer.killer.request_shutdown(halt_machine=True)

  def _event_to_context(self, event) -> dict:
    return {
      'silent': event.kwargs.get('silent', True)
    }

  def on_enter_home(self, event) -> None:
    context = self._event_to_context(event)
    if self._volumio.is_playing():
      self.play_track(**context)
    elif self._volumio.is_on_pause():
      self.pause_track(**context)
    elif self._volumio.has_status_stop():
      self.stop_track(**context)

  def on_enter_home_playing(self, event) -> None:
    context = self._event_to_context(event)
    # Only command Volumio on a user-initiated transition; when merely reflecting
    # Volumio's own state (silent, e.g. VigieThread.refresh_home) re-issuing the
    # command fights Volumio and causes a status flip-flop.
    if not context['silent']:
      self._display.display_temporary_text(text='LECTURE', wave=True)
      self._volumio.resume()
    PlayingTrackDisplayThread(self._volumio, self._display).start()

  def on_enter_home_holding(self, event) -> None:
    context = self._event_to_context(event)
    if not context['silent']:
      self._display.display_temporary_text(text='PAUSE', wave=True)
      self._volumio.pause()
    DatetimeDisplayThread(self._display).start()

  def on_enter_home_sleeping(self, event) -> None:
    context = self._event_to_context(event)
    if not context['silent']:
      self._display.display_temporary_text(text='STOP', wave=True)
      self._volumio.hold_on()
    DatetimeDisplayThread(self._display).start()

  def on_enter_menu(self, event) -> None:
    from menu_thread import MenuThread
    self._display.issue_persistent_display_daemon_stop_event()
    self._display.display_temporary_text(text='MENU', wave=True, duration=0.5)
    try:
      self._menu = MenuThread(self._display, self)
      self._menu.start()
    except Exception:
      logger.exception('failed to start menu thread')
      self._menu = None
      self.close_menu()

  def on_exit_menu(self, event) -> None:
    context = self._event_to_context(event)
    if not context['silent'] and self._menu is not None:
      try:
        self._menu.close()
      except Exception:
        logger.exception('error while closing menu')
      self._menu = None

  def can_play(self, event=None) -> bool:
    return (
      self._volumio.is_playing()
      or self._volumio.is_on_pause()
      or self._volumio.queue_is_not_empty()
    )

  def can_pause(self, event=None) -> bool:
    return self._volumio.is_on_pause() or (
      self._volumio.is_playing() and self._volumio.is_interactive_broadcast()
    )

  def is_playing(self, event=None) -> bool:
    return self._volumio.is_playing()

  def volume_up(self, event=None) -> None:
    self._volumio.volume_up()
    self._display.display_temporary_text(f'VOLUME {self._volumio.get_volume()}')

  def volume_down(self, event=None) -> None:
    self._volumio.volume_down()
    self._display.display_temporary_text(f'VOLUME {self._volumio.get_volume()}')

  def seek_up(self, event=None) -> None:
    self._volumio.seek_up()
    PlayingTrackElapsedTimeDisplayThread(self._volumio, self._display).start()

  def seek_down(self, event=None) -> None:
    self._volumio.seek_down()
    PlayingTrackElapsedTimeDisplayThread(self._volumio, self._display).start()

  def select_menu(self, event=None) -> None:
    if self._menu is not None:
      self._menu.select_current()

  def cancel_menu(self, event=None) -> None:
    if self._menu is not None:
      self._menu.back()

  def user_input_right(self, input_number: int) -> None:
    self._bump()
    if self._is_locked():
      return
    state = self.state
    if state == 'connecting':
      return
    if input_number == 1:
      self.user_input_1_right()
    elif input_number == 2:
      self.user_input_2_right()
    elif input_number == 3:
      self.user_input_3_right()
    elif input_number == 4:
      self.user_input_4_right()

  def user_input_left(self, input_number: int) -> None:
    self._bump()
    if self._is_locked():
      return
    state = self.state
    if state == 'connecting':
      return
    if input_number == 1:
      self.user_input_1_left()
    elif input_number == 2:
      self.user_input_2_left()
    elif input_number == 3:
      self.user_input_3_left()
    elif input_number == 4:
      self.user_input_4_left()

  def user_input_pressed(self, input_number: int) -> None:
    self._bump(True)
    state = self.state
    if state == 'connecting':
      return
    if input_number == 1:
      self.user_input_1_pressed()
    elif input_number == 2:
      self.user_input_2_pressed()
    elif input_number == 3:
      self.user_input_3_pressed()
    elif input_number == 4:
      self.user_input_4_pressed()

  def user_input_released(self, input_number: int) -> None:
    if self._is_locked():
      return
    state = self.state
    if state == 'connecting':
      return
    logger.debug('button %d released', input_number)

  def user_input_1_right(self) -> None:
    self.turn_volume_up(silent=False)

  def user_input_1_left(self) -> None:
    self.turn_volume_down(silent=False)

  def user_input_1_pressed(self) -> None:
    self.shut_down()

  def user_input_2_right(self) -> None:
    self.fast_forward()

  def user_input_2_left(self) -> None:
    self.rewind()

  def user_input_3_right(self) -> None:
    if self.state == 'menu':
      if self._menu is not None:
        self._menu.display_next()
    else:
      self._display.disable_sleep_mode()

  def user_input_3_left(self) -> None:
    if self.state == 'menu':
      if self._menu is not None:
        self._menu.display_previous()
    else:
      self._display.enable_sleep_mode()

  def user_input_2_pressed(self) -> None:
    if self.state == 'menu':
      self.back_menu(silent=False)

  def user_input_3_pressed(self) -> None:
    if self.state != 'menu':
      self.open_menu()
    else:
      self.enter_menu()

  def user_input_4_right(self) -> None:
    if self._volumio.can_browse_queue():
      idx = self._volumio.selected_index_next()
      track = self._volumio.get_track(idx)
      if track is None:
        return
      name = utils.fit_text(track)
      self._display.display_temporary_text(text=name, marquee_trim_start=True)
      self._issue_new_track_selector_stop_event()
      TrackSelectorThread(
        idx, name, self._volumio, self._display, self._latest_track_selector_stop_event
      ).start()
    else:
      self._display.display_temporary_text(text='  SUIV. >', wave=True, duration=3.5)
      self._volumio.next_track()

  def user_input_4_left(self) -> None:
    if self._volumio.can_browse_queue():
      idx = self._volumio.selected_index_previous()
      track = self._volumio.get_track(idx)
      if track is None:
        return
      name = utils.fit_text(track)
      self._display.display_temporary_text(text=name, marquee_trim_start=True)
      self._issue_new_track_selector_stop_event()
      TrackSelectorThread(
        idx, name, self._volumio, self._display, self._latest_track_selector_stop_event
      ).start()
    else:
      self._display.display_temporary_text(text='< PREC.  ', wave=True, duration=3.5)
      self._volumio.previous_track()

  def user_input_4_pressed(self) -> None:
    state = self.state
    if state == 'home_playing':
      self.stop_track(silent=False)
    elif state == 'home_holding':
      self.play_track(silent=False)
    elif state == 'home_sleeping':
      self.play_track(silent=False)
