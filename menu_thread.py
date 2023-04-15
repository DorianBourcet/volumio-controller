from threading import Thread, Event
from display_state import DisplayState
from volumio_thread import VolumioThread
from radio_state_machine import RadioStateMachine
from datetime import datetime
import volumio_api
import pytz
import time
import math

class MenuThread(Thread):

  fake_menu = [
    {
      'display_name': 'Option 1',
      'id': 'option-1',
      'type': 'VOLUMIO',
    },
    {
      'display_name': 'Option 2',
      'id': 'option-2',
      'type': 'VOLUMIO',
    },
    {
      'display_name': 'Option 3',
      'id': 'option-3',
      'type': 'VOLUMIO',
    },
    {
      'display_name': '< RETOUR',
      'id': 'back',
      'type': 'INTERNAL',
    },
  ]

  def __init__(self, display:DisplayState, radio:RadioStateMachine):
    super().__init__()
    self._display = display
    self._radio = radio
    self._stop_event = None
    self._selected_index = 0
    self._current_options = []
    self._history = []
    self._current_volumio_folder = ''
    self.daemon = True
  
  def build_menu(self):
    current_volumio_folder = self._current_volumio_folder
    raw_menu = volumio_api.browse(current_volumio_folder)
    raw_options = raw_menu['navigation']['lists']
    current_options = list(map(
      lambda x: {'display_name': x['name'], 'id': x['uri'], 'type': 'VOLUMIO'},
      raw_options
    ))
    current_options.append({
      'display_name': '< RETOUR',
      'id': 'back',
      'type': 'INTERNAL',
    })
    self._current_options = current_options

  def _get_option_name(self, index: int):
    return self._current_options[index]['display_name']
  
  def _get_option(self, index: int):
    return self._current_options[index]
  
  def display_first(self):
    self._selected_index = 0
    self._display.set_persistent_texts(texts=[self._get_option_name(self._selected_index)],continuous_marquee=True)
  
  def display_next(self):
    next_selected_index = self._selected_index + 1
    if next_selected_index >= len(self._current_options):
      next_selected_index = 0
    self._selected_index = next_selected_index
    self._display.set_persistent_texts(texts=[self._get_option_name(self._selected_index)],continuous_marquee=True)
  
  def display_previous(self):
    previous_selected_index = self._selected_index - 1
    if previous_selected_index < 0:
      previous_selected_index = len(self._current_options) - 1
    self._selected_index = previous_selected_index
    self._display.set_persistent_texts(texts=[self._get_option_name(self._selected_index)],continuous_marquee=True)
  
  def select_current(self):
    print('select current')
    option = self._get_option(self._selected_index)
    option_type = option['type']
    option_id = option['id']
    if option_type == 'INTERNAL':
      print('is internal')
      self._select_internal(option_id)
    print('is not internal')
  
  def _select_internal(self, option_id: str):
    if option_id == 'back':
      print('select back')
      self.close()
  
  def close(self):
    if not self.is_alive():
      raise Exception("Sorry, cannot close menu thread before it has started") 
    if self._stop_event:
      self._stop_event.set()
    self._radio.close_menu()

  def run(self):
    print('opened menu thread')
    self._stop_event = self._display.issue_persistent_display_daemon_stop_event()
    self.build_menu()
    self.display_first()
    while not self._stop_event.is_set():
      time.sleep(0.25)
    print('closed menu thread')