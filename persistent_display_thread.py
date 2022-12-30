from display_thread import DisplayThread
from threading import Event

class PersistentDisplayThread(DisplayThread):

  def __init__(self, display_state, stop_event: Event):
    super().__init__(display_state,stop_event)
    self._persistent_texts = display_state.persistent_texts

  def _get_texts(self) -> list:
    return self._persistent_texts

  def _after_run(self):
    if not self._stop_event.is_set() and (len(self._get_texts()) > 1 or self._ran_marquee):
      self._display_state.display_persistent_texts()
