from transitions.extensions import HierarchicalMachine
from volumio_thread import VolumioThread
from volumio_browser import VolumioBrowser
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
    'in_menu',
  ]

  transitions = [
    #{ 'trigger': 'show_menu', 'source': 'standing', 'dest': 'menu' },
    #{ 'trigger': 'exit_menu', 'source': 'menu', 'dest': 'standing' },
    { 'trigger': 'wait_for_connection', 'source': '*', 'dest': 'connecting' },
    { 'trigger': 'back_home', 'source': '*', 'dest': 'home' },
    { 'trigger': 'refresh_home', 'source': ['home', 'home_*'], 'dest': 'home' },
    { 'trigger': 'play_track', 'source': ['home', 'home_sleeping', 'home_holding'], 'dest': 'home_playing', 'conditions': 'can_play' },
    { 'trigger': 'pause_track', 'source': ['home', 'home_playing'], 'dest': 'home_holding', 'conditions': 'can_pause' },
    { 'trigger': 'stop_track', 'source': ['home', 'home_playing'], 'dest': 'home_sleeping' },
    { 'trigger': 'turn_volume_up', 'source': ['home', 'in_menu'], 'dest': None, 'before': 'volume_up' },
    { 'trigger': 'turn_volume_down', 'source': ['home', 'in_menu'], 'dest': None, 'before': 'volume_down' },
    { 'trigger': 'open_menu', 'source': 'home', 'dest': 'in_menu' },
    { 'trigger': 'enter_menu', 'source': 'in_menu', 'dest': None, 'before': 'select_menu' },
    { 'trigger': 'exit_menu', 'source': 'in_menu', 'dest': None, 'before': 'cancel_menu', 'conditions': 'is_in_sub_menu' },
    { 'trigger': 'close_menu', 'source': 'in_menu', 'dest': 'home' },
  ]

  fake_menu = [
    {
      'name': 'Menu 1',
      'items': [
        {
          'name': 'Menu 1-1',
        },
        {
          'name': 'Menu 1-2',
        },
        {
          'name': 'Menu 1-3',
        },
      ]
    },
    {
      'name': 'Menu 2',
      'items': [
        {
          'name': 'Menu 2-1',
        },
        {
          'name': 'Menu 2-2',
        },
        {
          'name': 'Menu 2-3',
        },
      ]
    },
  ]

  def __init__(self, volumio: VolumioThread, browser: VolumioBrowser, display: DisplayState) -> None:
    self._volumio = volumio
    self._browser = browser
    self._display = display
    self._latest_persistent_display_stop_event = Event()
    self._latest_temporary_display_stop_event = Event()
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
  
  def _issue_new_persistent_display_stop_event(self):
    self._latest_persistent_display_stop_event.set()
    self._latest_persistent_display_stop_event = Event()
  
  def _issue_new_temporary_display_stop_event(self):
    self._latest_temporary_display_stop_event.set()
    self._latest_temporary_display_stop_event = Event()

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
    active_to_quiet_thread.daemon = True
    active_to_quiet_thread.start()
  
  def on_enter_connecting(self, event):
    self._issue_new_persistent_display_stop_event()
    self._display.set_persistent_texts(['En attente de Volumio...'])

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
    self._issue_new_persistent_display_stop_event()
    playing_track_thread = PlayingTrackDisplayThread(self._volumio,self._display,self._latest_persistent_display_stop_event)
    playing_track_thread.daemon = True
    playing_track_thread.start()

  def on_enter_home_holding(self, event):
    context = self._event_to_context(event)
    if not context['silent']:
      self._display.display_temporary_text(text='PAUSE',wave=True)
    self._volumio.pause()
    self._issue_new_persistent_display_stop_event()
    self._display.set_persistent_texts(['En pause...'])

  def on_enter_home_sleeping(self, event):
    context = self._event_to_context(event)
    if not context['silent']:
      self._display.display_temporary_text(text='STOP',wave=True)
    self._volumio.stop()
    self._issue_new_persistent_display_stop_event()
    datetime_thread = DatetimeDisplayThread(self._display,self._latest_persistent_display_stop_event)
    datetime_thread.daemon = True
    datetime_thread.start()

  def on_enter_in_menu(self, event):
    self._issue_new_persistent_display_stop_event()
    self._display.display_persistent_texts(['the menu'])
  
  def can_play(self, event=None):
    return self._volumio.is_playing() or self._volumio.is_on_pause() or self._volumio.queue_is_not_empty()

  def can_pause(self, event=None):
    return self._volumio.is_on_pause() or (self._volumio.is_playing() and self._volumio.is_interactive_broadcast())
  
  def volume_up(self, event=None):
    self._issue_new_temporary_display_stop_event()
    self._volumio.volume_up()
    self._display.display_temporary_text('VOLUME '+str(self._volumio.get_volume()))

  def volume_down(self, event=None):
    self._issue_new_temporary_display_stop_event()
    self._volumio.volume_down()
    self._display.display_temporary_text('VOLUME '+str(self._volumio.get_volume()))

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
        print('Button 3 right')
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
        print('Button 3 left')
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
    self._issue_new_temporary_display_stop_event()
    track_elapsed = PlayingTrackElapsedTimeDisplayThread(self._volumio,self._display,self._latest_temporary_display_stop_event)
    track_elapsed.daemon = True
    track_elapsed.start()

  def user_input_2_left(self):
    self._volumio.seek_down()
    self._issue_new_temporary_display_stop_event()
    track_elapsed = PlayingTrackElapsedTimeDisplayThread(self._volumio,self._display,self._latest_temporary_display_stop_event)
    track_elapsed.daemon = True
    track_elapsed.start()

  def user_input_2_released(self):
    state = self.state
    if state == 'home_playing' and self.can_pause():
      self.pause_track(silent=False)
    elif state == 'home_holding':
      self.play_track(silent=False)
    elif state == 'in_menu':
      self.close_menu()
  
  def user_input_3_released(self):
    self.open_menu()

  def user_input_4_right(self):
    if self._volumio.can_browse_queue():
      idx = self._volumio.selected_index_next()
      name = utils.shorten_text(self._volumio.get_track(idx))
      self._display.display_temporary_text(text=name,marquee_trim_start=True)
      self._issue_new_track_selector_stop_event()
      track_selector = TrackSelectorThread(idx,name,self._volumio,self._display,self._latest_track_selector_stop_event)
      track_selector.daemon = True
      track_selector.start()
    else:
      self._display.display_temporary_text(text='  SUIV >',wave=True, duration=3.5)
      self._volumio.next_track()
  
  def user_input_4_left(self):
    if self._volumio.can_browse_queue():
      idx = self._volumio.selected_index_previous()
      name = utils.shorten_text(self._volumio.get_track(idx))
      self._display.display_temporary_text(text=name,marquee_trim_start=True)
      self._issue_new_track_selector_stop_event()
      track_selector = TrackSelectorThread(idx,name,self._volumio,self._display,self._latest_track_selector_stop_event)
      track_selector.daemon = True
      track_selector.start()
    else:
      self._display.display_temporary_text(text='< PREC  ',wave=True,duration=3.5)
      self._volumio.previous_track()

  def user_input_4_released(self):
    state = self.state
    if state == 'home_playing':
      self.stop_track(silent=False)
    elif state == 'home_holding':
      self.play_track(silent=False)
    elif state == 'home_sleeping':
      self.play_track(silent=False)