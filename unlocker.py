from threading import Thread, Event
from display_state import DisplayState
import time

class Unlocker:

  def __init__(self, display:DisplayState, locked_event: Event):
    self._display = display
    self._locked_event = locked_event
    self._has_run_event = Event()
    self._can_unlock = False
    self._thread = None

  def bump(self):
    if not self._locked_event.is_set():
      raise Exception('locked_event is not set, there is nothing to nothing to bump')
    if self._thread is None:
      print('no thread, creating...')
      self._thread = UnlockerThread(self._display,self._locked_event,self._has_run_event)
      self._thread.start()
      return
    if self._has_run_event.is_set():
      self._has_run_event.clear()
      print('has run, recreating...')
      self._thread = UnlockerThread(self._display,self._locked_event,self._has_run_event)
      self._thread.start()
      return
    self._thread.bump()

class UnlockerThread(Thread):

  def __init__(self, display:DisplayState, locked_event: Event, has_run_event: Event):
    super().__init__()
    self._display = display
    self._locked_event = locked_event
    self._has_run_event = has_run_event
    self._last_bump_time = None
    self._bump_number = 0
    self._reached_unlock = False
    self.daemon = True
  
  def bump(self):
    print('called bump in thread')
    if not self.is_alive():
      raise Exception('Cannot call bump if the thread is not alive')
    self._last_bump_time = time.time()
    self._increase_bump_number()
    if self._bump_number >= 12:
      self._locked_event.clear()
      self._display.set_active_mode()
      self._reached_unlock = True
    
  def _increase_bump_number(self):
    increased = self._bump_number + 4
    self._bump_number = min(increased,12)
    self._display.display_temporary_text(text=self._bump_number*'.',duration=0.5)
    print('increased bump number')
  
  def _decrease_bump_number(self):
    self._bump_number -= 2
    self._display.display_temporary_text(text=self._bump_number*'.',duration=0.05)
    print('decreased bump number')
  
  def _should_decrease(self):
    return time.time() - self._last_bump_time >= 0.50

  def run(self):
    print('called run on unlocker_thread')
    self.bump()
    while self._bump_number > 0 and not self._reached_unlock:
      if self._should_decrease():
        self._decrease_bump_number()
      time.sleep(0.05)
    #self._display.clear_temporary_display()
    print('finished running')
    self._has_run_event.set()
    