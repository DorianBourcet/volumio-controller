from display_thread import DisplayThread
from threading import Event

class PersistentDisplayThread(DisplayThread):

  def __init__(self, display_state, text_to_display: str, stop_event: Event, quiet_stop_event:Event):
    super().__init__(display_state,text_to_display,stop_event,quiet_stop_event)

  def _after_run(self):
    if not self._stop_event.is_set():
      self._display_state.display_persistent_texts()
