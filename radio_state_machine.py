from transitions.extensions import HierarchicalMachine
from volumio_thread import VolumioThread
from display_state import DisplayState
from playing_track_display_thread import PlayingTrackDisplayThread
from datetime_display_thread import DatetimeDisplayThread
from active_to_quiet_display_thread import ActiveToQuietDisplayThread
from playing_track_elapsed_time_display_thread import PlayingTrackElapsedTimeDisplayThread
from track_selector_thread import TrackSelectorThread
from threading import Event
import time
import utils

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
    },
    'menu',
  ]

  transitions = [
    { 'trigger': 'wait_for_connection', 'source': '*', 'dest': 'connecting' },
    { 'trigger': 'back_home', 'source': '*', 'dest': 'home' },
    { 'trigger': 'refresh_home', 'source': ['home', 'home_*'], 'dest': 'home' },
    { 'trigger': 'play_track', 'source': ['home', 'home_sleeping', 'home_holding'], 'dest': 'home_playing', 'conditions': 'can_play' },
    { 'trigger': 'pause_track', 'source': ['home', 'home_playing'], 'dest': 'home_holding', 'conditions': 'can_pause' },
    { 'trigger': 'stop_track', 'source': ['home', 'home_playing'], 'dest': 'home_sleeping' },
    { 'trigger': 'turn_volume_up', 'source': ['home', 'menu'], 'dest': None, 'before': 'volume_up' },
    { 'trigger': 'turn_volume_down', 'source': ['home', 'menu'], 'dest': None, 'before': 'volume_down' },
    { 'trigger': 'open_menu', 'source': 'home', 'dest': 'menu' },
    { 'trigger': 'enter_menu', 'source': 'menu', 'dest': None, 'before': 'select_menu' },
    { 'trigger': 'back_menu', 'source': 'menu', 'dest': None, 'before': 'cancel_menu' },
    { 'trigger': 'close_menu', 'source': 'menu', 'dest': 'home' },
  ]

  def __init__(self, volumio: VolumioThread, display: DisplayState) -> None:
    self._volumio = volumio
    self._display = display
    self._latest_active_to_quiet_stop_event = Event()
    self._latest_track_selector_stop_event = Event()
    self._quiet_event = Event()
    self._last_input_time = time.time()
    self.machine = HierarchicalMachine(
      model=self,
      send_event=True,
      states=RadioStateMachine.states,
      initial='connecting',
      transitions=RadioStateMachine.transitions
    )
    self._wake_up()

  def _issue_new_active_to_quiet_stop_event(self):
    self._latest_active_to_quiet_stop_event.set()
    self._latest_active_to_quiet_stop_event = Event()
  
  def _issue_new_track_selector_stop_event(self):
    self._latest_track_selector_stop_event.set()
    self._latest_track_selector_stop_event = Event()

  def _is_quiet(self):
    return self._quiet_event.is_set()

  def _wake_up(self):
    self._issue_new_active_to_quiet_stop_event()
    active_to_quiet_thread = ActiveToQuietDisplayThread(self._display,self._latest_active_to_quiet_stop_event,self._quiet_event)
    active_to_quiet_thread.start()
  
  def on_enter_connecting(self, event):
    self._display.display_persistent_texts(texts=['En attente de Volumio...'],continuous_marquee=True)

  def _event_to_context(self, event) -> dict:
    return {
      'silent': event.kwargs.get('silent',True)
    }
  
  def on_enter_home(self, event):
    context = self._event_to_context(event)
    if self._volumio.is_playing():
      self.play_track(**context)
    elif self._volumio.is_on_pause():
      self.pause_track(**context)
    elif self._volumio.has_status_stop():
      self.stop_track(**context)
  
  def on_enter_home_playing(self, event):
    context = self._event_to_context(event)
    if not context['silent']:
      self._display.display_temporary_text(text='LECTURE',wave=True)
    self._volumio.resume()
    playing_track_thread = PlayingTrackDisplayThread(self._volumio,self._display)
    playing_track_thread.start()

  def on_enter_home_holding(self, event):
    context = self._event_to_context(event)
    if not context['silent']:
      self._display.display_temporary_text(text='PAUSE',wave=True)
    self._volumio.pause()
    datetime_thread = DatetimeDisplayThread(self._display)
    datetime_thread.start()

  def on_enter_home_sleeping(self, event):
    context = self._event_to_context(event)
    if not context['silent']:
      self._display.display_temporary_text(text='STOP',wave=True)
    self._volumio.hold_on()
    datetime_thread = DatetimeDisplayThread(self._display)
    datetime_thread.start()

  def on_enter_menu(self, event):
    from menu_thread import MenuThread
    self._display.issue_persistent_display_daemon_stop_event()
    self._display.display_temporary_text(text='MENU',wave=True,duration=0.5)
    self._menu = MenuThread(self._display,self)
    self._menu.start()
  
  def on_exit_menu(self, event):
    context = self._event_to_context(event)
    if not context['silent']:
      self._menu.close()
      self._menu = None
  
  def can_play(self, event=None):
    return self._volumio.is_playing() or self._volumio.is_on_pause() or self._volumio.queue_is_not_empty()

  def can_pause(self, event=None):
    return self._volumio.is_on_pause() or (self._volumio.is_playing() and self._volumio.is_interactive_broadcast())
  
  def volume_up(self, event=None):
    self._volumio.volume_up()
    self._display.display_temporary_text('VOLUME '+str(self._volumio.get_volume()))

  def volume_down(self, event=None):
    self._volumio.volume_down()
    self._display.display_temporary_text('VOLUME '+str(self._volumio.get_volume()))
  
  def select_menu(self, event=None):
    self._menu.select_current()

  def cancel_menu(self, event=None):
    self._menu.back()

  def user_input_right(self, input_number: int):
    if self._is_quiet():
      self._wake_up()
      return
    self._wake_up()
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
  
  def user_input_left(self, input_number: int):
    if self._is_quiet():
      self._wake_up()
      return
    self._wake_up()
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
  
  def user_input_pressed(self, input_number: int):
    if self._is_quiet():
      self._wake_up()
      return
    self._wake_up()
    state = self.state
    if state == 'connecting':
      return
    if input_number == 1:
        print('Button 1 pressed')
    elif input_number == 2:
        print('Button 2 pressed')
    elif input_number == 3:
        print('Button 3 pressed')
    elif input_number == 4:
        print('Button 4 pressed')
  
  def user_input_released(self, input_number: int):
    if self._is_quiet():
      self._wake_up()
      return
    self._wake_up()
    state = self.state
    if state == 'connecting':
      return
    if input_number == 1:
        print('Button 1 released')
    elif input_number == 2:
        self.user_input_2_released()
    elif input_number == 3:
        self.user_input_3_released()
    elif input_number == 4:
        self.user_input_4_released()

  def user_input_1_right(self):
    self.turn_volume_up(silent=False)
  
  def user_input_1_left(self):
    self.turn_volume_down(silent=False)

  def user_input_2_right(self):
    self._volumio.seek_up()
    track_elapsed = PlayingTrackElapsedTimeDisplayThread(self._volumio,self._display)
    track_elapsed.start()
  
  def user_input_3_right(self):
    state = self.state
    if state == 'menu':
      self._menu.display_next()

  def user_input_2_left(self):
    self._volumio.seek_down()
    track_elapsed = PlayingTrackElapsedTimeDisplayThread(self._volumio,self._display)
    track_elapsed.start()

  def user_input_3_left(self):
    state = self.state
    if state == 'menu':
      self._menu.display_previous()

  def user_input_2_released(self):
    state = self.state
    # if state == 'home_playing' and self.can_pause():
    #   self.pause_track(silent=False)
    # elif state == 'home_holding':
    #   self.play_track(silent=False)
    if state == 'menu':
      self.back_menu(silent=False)
  
  def user_input_3_released(self):
    state = self.state
    if state != 'menu':
      self.open_menu()
    else:
      self.enter_menu()

  def user_input_4_right(self):
    if self._volumio.can_browse_queue():
      idx = self._volumio.selected_index_next()
      name = utils.shorten_text(self._volumio.get_track(idx))
      self._display.display_temporary_text(text=name,marquee_trim_start=True)
      self._issue_new_track_selector_stop_event()
      track_selector = TrackSelectorThread(idx,name,self._volumio,self._display,self._latest_track_selector_stop_event)
      track_selector.start()
    else:
      self._display.display_temporary_text(text='  SUIV. >',wave=True, duration=3.5)
      self._volumio.next_track()
  
  def user_input_4_left(self):
    if self._volumio.can_browse_queue():
      idx = self._volumio.selected_index_previous()
      name = utils.shorten_text(self._volumio.get_track(idx))
      self._display.display_temporary_text(text=name,marquee_trim_start=True)
      self._issue_new_track_selector_stop_event()
      track_selector = TrackSelectorThread(idx,name,self._volumio,self._display,self._latest_track_selector_stop_event)
      track_selector.start()
    else:
      self._display.display_temporary_text(text='< PREC.  ',wave=True,duration=3.5)
      self._volumio.previous_track()

  def user_input_4_released(self):
    state = self.state
    if state == 'home_playing':
      self.stop_track(silent=False)
    elif state == 'home_holding':
      self.play_track(silent=False)
    elif state == 'home_sleeping':
      self.play_track(silent=False)