from threading import Event
from track_elapsed_time_display_thread import TrackElapsedTimeDisplayThread
from display_state import DisplayState
from volumio_thread import VolumioThread
import time

class PlayingTrackElapsedTimeDisplayThread(TrackElapsedTimeDisplayThread):

  def __init__(self, volumio:VolumioThread, display:DisplayState, stop_event:Event, duration:float=6.0):
    super().__init__(volumio,display,stop_event)
    self._duration = duration

  def run(self):
    start = time.time()
    while not self._stop_event.is_set() and time.time() - start <= self._duration:
      self._display.display_temporary_texts([self._produce_elapsed_time_text()],0.25)
      time.sleep(0.25)