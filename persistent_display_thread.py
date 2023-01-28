from display_thread import DisplayThread
from threading import Event, Lock

class PersistentDisplayThread(DisplayThread):

  def __init__(self, display_state, lock:Lock, stop_event: Event, quiet_stop_event:Event=None):
    super().__init__(display_state,stop_event)
    self._persistent_texts = display_state.persistent_texts
    self._lock = lock
    self._quiet_stop_event = quiet_stop_event

  def _get_texts(self) -> list:
    return self._persistent_texts

  def _starting(self):
    self._lock.acquire()

  def _exiting(self):
    self._lock.release()
  
  def _can_exit_while_printing(self) -> bool:
    return self._quiet_stop_event is None or not self._quiet_stop_event.is_set()


  def _after_run(self):
    if not self._stop_event.is_set() and (len(self._get_texts()) > 1 or self._ran_marquee):
      self._display_state.display_persistent_texts()
