from threading import Thread, Event
from display_state import DisplayState
from volumio_thread import VolumioThread
from user_input import UserInput
from utils import format_min_sec
import time
from radio_state_machine import RadioStateMachine
from vigie_thread import VigieThread
from user_input_listener import UserInputListener

class MainThread(Thread):

  def __init__(self):
    super().__init__()
    display = DisplayState()
    display.display_persistent_texts(stop_daemons=False,duration=0.25)
    self._volumio = VolumioThread()
    self._volumio.daemon = True
    self._volumio.start()
    vigie_stop_event = Event()
    self._radio = RadioStateMachine(self._volumio,display,vigie_stop_event)
    vigie = VigieThread(self._volumio,self._radio,vigie_stop_event)
    vigie.start()
    input_1 = UserInputListener(UserInput(0x36),self._radio,1)
    input_1.daemon = True
    input_1.start()
    input_2 = UserInputListener(UserInput(0x37),self._radio,2)
    input_2.daemon = True
    input_2.start()
    input_3 = UserInputListener(UserInput(0x38),self._radio,3)
    input_3.daemon = True
    input_3.start()
    input_4 = UserInputListener(UserInput(0x3a),self._radio,4)
    input_4.daemon = True
    input_4.start()
    self.daemon = True

  def run(self):
    while True:
      if self._volumio.is_connected():
        self._radio.back_home()
      while self._volumio.is_connected():
        time.sleep(1)
      self._radio.wait_for_connection()
      time.sleep(1)

