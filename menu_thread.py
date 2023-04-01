from threading import Thread, Event
from display_state import DisplayState
from volumio_thread import VolumioThread
from datetime import datetime
import pytz
import time
import math

class MenuThread(Thread):

  def __init__(self, display:DisplayState):
    super().__init__()
    self._display = display
    self._stop_event = None
    self.daemon = True
  
  def close(self):
    if self._stop_event:
      self._stop_event.set()

  def run(self):
    self._stop_event = self._display.issue_persistent_display_daemon_stop_event()
    while not self._stop_event.is_set():
      self._display.set_persistent_texts(['in the menu'])
      time.sleep(0.25)