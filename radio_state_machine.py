from transitions.extensions import HierarchicalMachine
from volumio_thread import VolumioThread
from display_state import DisplayState
from playing_track_display_thread import PlayingTrackDisplayThread
from datetime_display_thread import DatetimeDisplayThread
from active_to_quiet_display_thread import ActiveToQuietDisplayThread
from playing_track_elapsed_time_display_thread import PlayingTrackElapsedTimeDisplayThread
from holding_track_elapsed_time_display_thread import HoldingTrackElapsedTimeDisplayThread
from threading import Event
import time

class RadioStateMachine(object):

  states = [
    'connecting',
    {
      'name': 'home',
      'children': [
        'playing',
        'holding',
        'sleeping',
      ]
    }
    #'menu',
  ]

  transitions = [
    #{ 'trigger': 'show_menu', 'source': 'standing', 'dest': 'menu' },
    #{ 'trigger': 'exit_menu', 'source': 'menu', 'dest': 'standing' },
    { 'trigger': 'wait_for_connection', 'source': '*', 'dest': 'connecting' },
    { 'trigger': 'back_home', 'source': '*', 'dest': 'home' },
    { 'trigger': 'refresh_home', 'source': ['home', 'home_*'], 'dest': 'home' },
    { 'trigger': 'play_track', 'source': ['home', 'home_sleeping', 'home_holding'], 'dest': 'home_playing', 'conditions': 'can_play' },
    { 'trigger': 'pause_track', 'source': ['home', 'home_playing'], 'dest': 'home_holding', 'conditions': 'can_pause' },
    { 'trigger': 'stop_track', 'source': ['home', 'home_playing'], 'dest': 'home_sleeping'},
  ]

  def __init__(self, volumio: VolumioThread, display: DisplayState) -> None:
    self._volumio = volumio
    self._display = display
    self._latest_persistent_display_stop_event = Event()
    self._latest_temporary_display_stop_event = Event()
    self._latest_active_to_quiet_stop_event = Event()
    self._quiet_event = Event()
    self._last_input_time = time.time()
    self.machine = HierarchicalMachine(
      model=self,
      states=RadioStateMachine.states,
      initial='connecting',
      transitions=RadioStateMachine.transitions
    )
  
  def _issue_new_persistent_display_stop_event(self):
    self._latest_persistent_display_stop_event.set()
    self._latest_persistent_display_stop_event = Event()
  
  def _issue_new_temporary_display_stop_event(self):
    self._latest_temporary_display_stop_event.set()
    self._latest_temporary_display_stop_event = Event()

  def _issue_new_active_to_quiet_stop_event(self):
    self._latest_active_to_quiet_stop_event.set()
    self._latest_active_to_quiet_stop_event = Event()

  def _is_quiet(self):
    now = time.time()
    return self._quiet_event.is_set()

  def _wake_up(self):
    self._issue_new_active_to_quiet_stop_event()
    active_to_quiet_thread = ActiveToQuietDisplayThread(self._display,self._latest_active_to_quiet_stop_event,self._quiet_event)
    active_to_quiet_thread.daemon = True
    active_to_quiet_thread.start()
  
  def on_enter_connecting(self):
    self._issue_new_active_to_quiet_stop_event()
    self._issue_new_persistent_display_stop_event()
    self._display.set_persistent_texts(['En attente de Volumio...'])
  
  def on_enter_home(self):
    if self._volumio.is_playing():
      self.play_track()
    elif self._volumio.is_on_pause():
      self.pause_track()
    elif self._volumio.has_status_stop():
      self.stop_track()
  
  def on_enter_home_playing(self):
    self._volumio.resume()
    self._issue_new_persistent_display_stop_event()
    playing_track_thread = PlayingTrackDisplayThread(self._volumio,self._display,self._latest_persistent_display_stop_event)
    playing_track_thread.daemon = True
    playing_track_thread.start()

  def on_enter_home_holding(self):
    self._volumio.pause()
    self._issue_new_persistent_display_stop_event()
    holding_track_thread = HoldingTrackElapsedTimeDisplayThread(self._volumio,self._display,self._latest_persistent_display_stop_event)
    holding_track_thread.daemon = True
    holding_track_thread.start()

  def on_enter_home_sleeping(self):
    self._volumio.stop()
    self._issue_new_persistent_display_stop_event()
    datetime_thread = DatetimeDisplayThread(self._display,self._latest_persistent_display_stop_event)
    datetime_thread.daemon = True
    datetime_thread.start()
  
  def can_play(self):
    return self._volumio.is_playing() or self._volumio.is_on_pause() or self._volumio.queue_is_not_empty()

  def can_pause(self):
    return self._volumio.is_on_pause() or (self._volumio.is_playing() and self._volumio.is_interactive_broadcast())

  def user_input_1_right(self):
    if self._is_quiet():
      self._wake_up()
      return
    self._wake_up()
    self._issue_new_temporary_display_stop_event()
    self._volumio.volume_up()
    self._display.display_temporary_texts(['VOLUME '+str(self._volumio.get_volume())])
  
  def user_input_1_left(self):
    if self._is_quiet():
      self._wake_up()
      return
    self._wake_up()
    self._issue_new_temporary_display_stop_event()
    self._volumio.volume_down()
    self._display.display_temporary_texts(['VOLUME '+str(self._volumio.get_volume())])

  def user_input_2_right(self):
    if self._is_quiet():
      self._wake_up()
      return
    self._wake_up()
    self._volumio.seek_up()
    self._issue_new_temporary_display_stop_event()
    track_elapsed = PlayingTrackElapsedTimeDisplayThread(self._volumio,self._display,self._latest_temporary_display_stop_event)
    track_elapsed.daemon = True
    track_elapsed.start()

  def user_input_2_left(self):
    if self._is_quiet():
      self._wake_up()
      return
    self._wake_up()
    self._volumio.seek_down()
    self._issue_new_temporary_display_stop_event()
    track_elapsed = PlayingTrackElapsedTimeDisplayThread(self._volumio,self._display,self._latest_temporary_display_stop_event)
    track_elapsed.daemon = True
    track_elapsed.start()

  def user_input_2_released(self):
    if self._is_quiet():
      self._wake_up()
      return
    self._wake_up()
    state = self.state
    if state == 'home_playing' and self.can_pause():
      self.pause_track()
    elif state == 'home_holding':
      self.play_track()

  def user_input_4_right(self):
    if self._is_quiet():
      self._wake_up()
      return
    self._wake_up()
    next_track_text = self._volumio.get_next_track()
    if next_track_text is None:
      next_track_text = '    SUIV >  '
    self._display.display_temporary_texts([next_track_text],None,True)
    self._volumio.next_track()
  
  def user_input_4_left(self):
    if self._is_quiet():
      self._wake_up()
      return
    self._wake_up()
    previous_track_text = self._volumio.get_previous_track()
    if previous_track_text is None:
      previous_track_text = '  < PREC    '
    self._display.display_temporary_texts([previous_track_text],None,True)
    self._volumio.previous_track()

  def user_input_4_pressed(self):
    if self._is_quiet():
      self._wake_up()
      return
    self._wake_up()

  def user_input_4_released(self):
    if self._is_quiet():
      self._wake_up()
      return
    self._wake_up()
    state = self.state
    if state == 'home_playing':
      self.stop_track()
    elif state == 'home_holding':
      self.play_track()
    elif state == 'home_sleeping':
      self.play_track()