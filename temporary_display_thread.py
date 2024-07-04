from display_thread import DisplayThread
from threading import Event

class TemporaryDisplayThread(DisplayThread):

  def __init__(
    self,
    display_state,
    text_to_display: str,
    stop_event: Event,
    marquee_trim_start: bool = False,
    align_left: bool = False,
    wave: bool = False,
    trim_next_persistent_marquee: bool = False
  ):
    super().__init__(display_state,text_to_display,stop_event,display_state.temporary_text_duration,align_left,wave)
    self._marquee_trim_start = marquee_trim_start
    self._trim_next_persistent_marquee = trim_next_persistent_marquee

  def _after_run(self):
    if not self._stop_event.is_set():
      self._display_state.display_persistent_texts(stop_daemons=False, marquee_trim_start = self._trim_next_persistent_marquee)

  def _on_marquee_must_trim_start(self):
    return self._marquee_trim_start
