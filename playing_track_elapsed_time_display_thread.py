import time

import logging_setup
from display_state import DisplayState
from track_elapsed_time_display_thread import TrackElapsedTimeDisplayThread
from volumio_thread import VolumioThread

logger = logging_setup.get_logger(__name__)

POLL_INTERVAL_SEC = 0.25


class PlayingTrackElapsedTimeDisplayThread(TrackElapsedTimeDisplayThread):

  def __init__(self, volumio: VolumioThread, display: DisplayState, duration: float = 6.0):
    super().__init__(volumio, display)
    self._duration = duration
    self.daemon = True

  def run(self) -> None:
    try:
      start = time.time()
      stop_event = self._display.issue_temporary_display_daemon_stop_event()
      while not stop_event.is_set() and time.time() - start <= self._duration:
        self._display.display_temporary_text(
          text=self._produce_elapsed_time_text(),
          duration=0.25,
          stop_daemons=False,
        )
        time.sleep(POLL_INTERVAL_SEC)
    except Exception:
      logger.exception('elapsed time display thread crashed')
