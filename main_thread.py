from threading import Thread, Event
from display_state import DisplayState
from volumio_thread import VolumioThread
from user_input import UserInput
from basic_state_thread import BasicStateThread
from utils import format_min_sec
import time

class MainThread(Thread):

  def __init__(self):
    super().__init__()
    self._user_input1 = UserInput(0x36)
    self._user_input2 = UserInput(0x37)
    self._user_input4 = UserInput(0x3a)
    self._display = DisplayState()
    self._display.display_temporary_texts(['ALLO'])
    self._volumio = VolumioThread()
    self._volumio.daemon = True
    self._volumio.start()
    self._basic_state = BasicStateThread(self._volumio,self._display)
    self._basic_state.daemon = True
    self._basic_state.start()
    now = time.time()
    self._last_input_time = now
    self._last_volume_input = now
    self._is_quiet_mode = False

  def _is_quiet(self):
    now = time.time()
    return now - self._last_input_time >= 60

  def _set_quiet_mode(self):
    if not self._is_quiet_mode:
      self._display.set_quiet_mode()
      self._is_quiet_mode = True

  def _set_active_mode(self):
    self._last_input_time = time.time()
    if self._is_quiet_mode:
      self._display.set_active_mode()
      self._is_quiet_mode = False

  def _get_volume_step(self) -> int:
    now = time.time()
    delay = now - self._last_volume_input
    self._last_volume_input = now
    if delay <= 0.10:
      return 4
    if delay <= 0.20:
      return 2
    return 1

  def run(self):
    while True:
      if self._is_quiet():
        self._set_quiet_mode()
      if self._user_input1.turned_right():
        if self._is_quiet():
          self._set_active_mode()
          continue
        self._set_active_mode()
        self._volumio.volume_up(self._get_volume_step())
        self._display.display_temporary_texts(['VOLUME '+str(self._volumio.get_volume())])
      if self._user_input1.turned_left():
        if self._is_quiet():
          self._set_active_mode()
          continue
        self._set_active_mode()
        self._volumio.volume_down(self._get_volume_step())
        self._display.display_temporary_texts(['VOLUME '+str(self._volumio.get_volume())])
      if self._user_input1.pressed():
        if self._is_quiet():
          self._set_active_mode()
          continue
        self._set_active_mode()
        print("Button 1 pressed")
      if self._user_input1.released():
        if self._is_quiet():
          self._set_active_mode()
          continue
        self._set_active_mode()
        print("Button 1 released")
      if self._user_input2.turned_right():
        if self._is_quiet():
          self._set_active_mode()
          continue
        self._set_active_mode()
        self._volumio.seek_up()
        self._display.display_temporary_texts(['+ 15 sec'])
      if self._user_input2.turned_left():
        if self._is_quiet():
          self._set_active_mode()
          continue
        self._set_active_mode()
        self._volumio.seek_down()
        self._display.display_temporary_texts(['- 15 sec'])
      if self._user_input2.pressed():
        if self._is_quiet():
          self._set_active_mode()
          continue
        self._set_active_mode()
        print("Button 2 pressed")
      if self._user_input2.released():
        if self._is_quiet():
          self._set_active_mode()
          continue
        self._set_active_mode()
        self._volumio.toggle_play_stop()
        print("Button 2 released")
      if self._user_input4.turned_right():
        if self._is_quiet():
          self._set_active_mode()
          continue
        self._set_active_mode()
        if self._volumio.get_current_service() == 'spop':
          next_track_text = None
        else:
          next_track_text = self._volumio.get_next_track()
        if next_track_text is None:
          next_track_text = '    SUIV >  '
        self._display.display_temporary_texts([next_track_text],None,True)
        self._volumio.next_track()
      if self._user_input4.turned_left():
        if self._is_quiet():
          self._set_active_mode()
          continue
        self._set_active_mode()
        if self._volumio.get_current_service() == 'spop':
          previous_track_text = None
        else:
          previous_track_text = self._volumio.get_previous_track()
        if previous_track_text is None:
          previous_track_text = '  < PREC    '
        self._display.display_temporary_texts([previous_track_text],None,True)
        self._volumio.previous_track()
      if self._user_input4.pressed():
        if self._is_quiet():
          self._set_active_mode()
          continue
        self._set_active_mode()
        print("Button 4 pressed")
      if self._user_input4.released():
        if self._is_quiet():
          self._set_active_mode()
          continue
        self._set_active_mode()
        self._volumio.toggle_play_stop()
        print("Button 4 released")

