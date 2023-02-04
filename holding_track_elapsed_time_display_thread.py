from threading import Event
from track_elapsed_time_display_thread import TrackElapsedTimeDisplayThread
from display_state import DisplayState
from volumio_thread import VolumioThread
import time

class HoldingTrackElapsedTimeDisplayThread(TrackElapsedTimeDisplayThread):

  def __init__(self, volumio:VolumioThread, display:DisplayState, stop_event:Event):
    super().__init__(volumio,display,stop_event)
    self._last_blink = None
    self._must_display_text = True

  def run(self):
    text = self._produce_elapsed_time_text()
    self._last_blink = time.time()
    while not self._stop_event.is_set():
      now = time.time()
      if now - self._last_blink >= 0.5:
        self._last_blink = now
        self._must_display_text = not self._must_display_text
      self._display.display_persistent_texts([text if self._must_display_text else ''])
      time.sleep(0.25)