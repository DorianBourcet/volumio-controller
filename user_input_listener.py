from threading import Thread, Event
from display_state import DisplayState
from volumio_thread import VolumioThread
from user_input import UserInput
from utils import format_min_sec
import time
from radio_state_machine import RadioStateMachine

class UserInputListener(Thread):

  def __init__(self, user_input: UserInput, radio: RadioStateMachine, input_number: int):
    super().__init__()
    self._user_input = user_input
    self._radio = radio
    self._input_number = input_number

  def run(self):
    while True:
      if self._user_input.turned_right():
        self._radio.user_input_right(self._input_number)
      elif self._user_input.turned_left():
        self._radio.user_input_left(self._input_number)
      elif self._user_input.pressed():
        self._radio.user_input_pressed(self._input_number)
      elif self._user_input.released():
        self._radio.user_input_released(self._input_number)
      time.sleep(0.05)

