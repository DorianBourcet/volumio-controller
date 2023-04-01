from threading import Event
from track_elapsed_time_display_thread import TrackElapsedTimeDisplayThread
from display_state import DisplayState
from volumio_thread import VolumioThread
import time

class PlayingTrackElapsedTimeDisplayThread(TrackElapsedTimeDisplayThread):

  def __init__(self, volumio:VolumioThread, display:DisplayState, duration:float=6.0):
    super().__init__(volumio,display)
    self._duration = duration
    self.daemon = True

  def run(self):
    start = time.time()
    stop_event = self._display.issue_temporary_display_daemon_stop_event()
    while not stop_event.is_set() and time.time() - start <= self._duration:
      self._display.display_temporary_text(
        text=self._produce_elapsed_time_text(),
        duration=0.25,
        stop_daemons=False
      )
      time.sleep(0.25)