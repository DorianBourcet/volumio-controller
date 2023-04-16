from threading import Thread, Event
from display_state import DisplayState
from volumio_thread import VolumioThread
from radio_state_machine import RadioStateMachine
from datetime import datetime
from volumio_menu import VolumioMenu
import volumio_api
import pytz
import time
import math

class MenuThread(Thread):

  def __init__(self, display:DisplayState, radio:RadioStateMachine):
    super().__init__()
    self._display = display
    self._radio = radio
    self._stop_event = None
    self._selected_index = 0
    self._current_options = []
    self._history = []
    self._current_volumio_folder = ''
    self._volumio_menu = VolumioMenu('volumio')
    self.daemon = True
  
  def home(self):
    print('in home')
    options = self._volumio_menu.browse()
    self._render_options(options)
    self._history = []
  
  def select(self, selected_option: dict):
    print('select:')
    print(selected_option)
    provider = selected_option['provider']
    uri = selected_option['uri']
    result = self._browse_provider(provider,uri)
    result_type = type(result)
    print(result)
    if result_type is list:
      # result is a list, then needs to render it
      self._render_options(result)
      self._history.append(selected_option)
    elif result_type is dict:
      print('is dict')
      # result is a dict, then display a temporary message and exit menu if required
      message = result['message']
      must_close = result['terminated']
      self._display.display_temporary_text(text=message,wave=True,duration=3.5)
      if must_close:
        self.close()
  
  def _browse_provider(self, provider: str, uri: str):
    if provider == 'volumio':
      return self._volumio_menu.browse(uri)
    if provider == 'internal':
      return self._select_internal(uri)
  
  def _render_options(self, options: list):
    self._current_options = []
    options.append({
      'name': '< RETOUR',
      'uri': 'back',
      'provider': 'internal'
    })
    self._current_options = options
    print(self._current_options)
    self._display_first()

  def _get_option_name(self, index: int):
    return self._current_options[index]['name']
  
  def _get_option(self, index: int):
    return self._current_options[index]
  
  def _display_first(self):
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
    self._display.set_persistent_texts(texts=['...'],continuous_marquee=False)
    print('select current')
    option = self._get_option(self._selected_index)
    self.select(option)
  
  def _select_internal(self, uri: str):
    if uri == 'back':
      print('select back')
      if not self._history:
        self.close()
      else:
        self._history.pop()
        if self._history:
          option = self._history[len(self._history)-1]
          return self._browse_provider(option['provider'],option['uri'])
        return self._volumio_menu.browse()
  
  def back(self):
    if not self._history:
      self.close()
    else:
      self._history.pop()
      if self._history:
        option = self._history[len(self._history)-1]
        result = self._browse_provider(option['provider'],option['uri'])
      result = self._volumio_menu.browse()
      self._render_options(result)
  
  def close(self):
    if not self.is_alive():
      raise Exception("Sorry, cannot close menu thread before it has started") 
    if self._stop_event:
      self._stop_event.set()
    self._radio.close_menu()

  def run(self):
    print('opened menu thread')
    self._stop_event = self._display.issue_persistent_display_daemon_stop_event()
    self.home()
    while not self._stop_event.is_set():
      time.sleep(0.25)
    print('closed menu thread')