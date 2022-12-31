from threading import Thread, Event
from display_state import DisplayState
from volumio_thread import VolumioThread
from user_input import UserInput
from utils import format_min_sec
import time
from radio_state_machine import RadioStateMachine
from vigie_thread import VigieThread

class MainThread(Thread):

  def __init__(self):
    super().__init__()
    self._user_input1 = UserInput(0x36)
    self._user_input2 = UserInput(0x37)
    self._user_input4 = UserInput(0x3a)
    self._display = DisplayState()
    self._display.display_temporary_texts(['ROSS x Volumio'])
    self._volumio = VolumioThread()
    self._volumio.daemon = True
    self._volumio.start()
    self._radio = RadioStateMachine(self._volumio,self._display)
    self._vigie = VigieThread(self._volumio,self._radio)
    self._vigie.daemon = True
    self._vigie.start()

  def run(self):
    while True:
      if self._volumio.is_connected():
        self._radio.back_home()
      while self._volumio.is_connected():
        if self._user_input1.turned_right():
          self._radio.user_input_1_right()
        if self._user_input1.turned_left():
          self._radio.user_input_1_left()
        if self._user_input1.pressed():
          print("Button 1 pressed")
        if self._user_input1.released():
          print("Button 1 released")
        if self._user_input2.turned_right():
          self._volumio.seek_up()
          self._display.display_temporary_texts(['+ 15 sec'])
        if self._user_input2.turned_left():
          self._volumio.seek_down()
          self._display.display_temporary_texts(['- 15 sec'])
        if self._user_input2.pressed():
          print("Button 2 pressed")
        if self._user_input2.released():
          self._volumio.toggle_play_stop()
          print("Button 2 released")
        if self._user_input4.turned_right():
          self._radio.user_input_4_right()
        if self._user_input4.turned_left():
          self._radio.user_input_4_left()
        if self._user_input4.pressed():
          self._radio.user_input_4_pressed()
        if self._user_input4.released():
          self._radio.user_input_4_released()
      self._radio.wait_for_connection()
      time.sleep(1)

