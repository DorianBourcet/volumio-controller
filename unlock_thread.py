from threading import Thread, Event
from display_state import DisplayState
import time

class UnlockThread(Thread):

  def __init__(self, display:DisplayState, locked_event: Event):
    super().__init__()
    self._display = display
    self._locked_event = locked_event
    self._start = None
    self._bump_number = 0
    self._can_unlock = False
    self.daemon = True
  
  def bump(self):
    self._bump_number += 2
    if self._bump_number >= 6:
      self._can_unlock = True
      # enough bumps, can unlock
      self._locked_event.clear()
  
  def should_go_quiet(self):
    return time.time() - self._start >= self._quiet_after_sec

  def run(self):
    self.bump()
    while self._bump_number > 1 and not self._can_unlock:
      self._bump_number -= 1
      self._display.display_temporary_text(text=str(self._bump_number))
      time.sleep(0.5)