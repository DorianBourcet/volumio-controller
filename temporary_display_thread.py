from display_thread import DisplayThread
from threading import Event

class TemporaryDisplayThread(DisplayThread):

  def __init__(self, display_state, text_to_display: str, stop_event: Event, marquee_trim_start: bool = False, wave:bool = False):
    super().__init__(display_state,text_to_display,stop_event,wave)
    self._duration = display_state.temporary_text_duration
    self._marquee_trim_start = marquee_trim_start

  def _get_duration(self, length: int) -> float:
    if self._duration:
      return self._duration
    return super()._get_duration(length)

  def _after_run(self):
    if not self._stop_event.is_set():
      self._display_state.display_persistent_texts()

  def _on_marquee_must_trim_start(self):
    return self._marquee_trim_start
