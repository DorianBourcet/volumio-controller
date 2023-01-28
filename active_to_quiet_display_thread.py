from threading import Thread, Event
from display_state import DisplayState
import time

class ActiveToQuietDisplayThread(Thread):

  def __init__(self, display:DisplayState, stop_event:Event, quiet_event:Event, quiet_after_sec:int=30):
    super().__init__()
    self._display = display
    self._start = None
    self._quiet_after_sec = quiet_after_sec
    self._stop_event = stop_event
    self._quiet_event = quiet_event
  
  def should_go_quiet(self):
    return time.time() - self._start >= self._quiet_after_sec

  def run(self):
    self._display.set_active_mode()
    self._quiet_event.clear()
    self._start = time.time()
    while not self._stop_event.is_set() and not self.should_go_quiet():
      time.sleep(0.25)
    if not self._stop_event.is_set():
      self._display.set_quiet_mode()
      self._quiet_event.set()