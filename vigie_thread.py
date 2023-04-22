from threading import Thread, Event
from display_state import DisplayState
from volumio_thread import VolumioThread
from radio_state_machine import RadioStateMachine
from datetime import datetime
import time

class VigieThread(Thread):

  def __init__(self, volumio:VolumioThread, radio:RadioStateMachine, stop_event: Event):
    super().__init__()
    self._volumio = volumio
    self._radio = radio
    self._latest_volumio_status = self._volumio.get_status()
    self._stop_event = stop_event
    self.daemon = True

  def run(self):
    while not self._stop_event.is_set():
      if self._radio.is_home(allow_substates=True) and self._volumio.get_status() != self._latest_volumio_status:
        self._radio.refresh_home()
        self._latest_volumio_status = self._volumio.get_status()
      time.sleep(0.25)
    print('exiting vigie...')