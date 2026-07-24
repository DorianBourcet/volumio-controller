import time
from threading import Thread

import logging_setup
from constants import DISPLAY_POLL_INTERVAL_SEC
from display_state import DisplayState
from volumio_thread import VolumioThread

logger = logging_setup.get_logger(__name__)


class PlayingTrackDisplayThread(Thread):

  def __init__(self, volumio: VolumioThread, display: DisplayState):
    super().__init__(name='playing-track')
    self._volumio = volumio
    self._display = display
    self.daemon = True

  def run(self) -> None:
    try:
      stop_event = self._display.issue_persistent_display_daemon_stop_event()
      while not stop_event.is_set():
        if self._volumio.is_playing():
          self._display.set_persistent_texts(
            texts=self._volumio.get_playing_track(),
            duration=4.0,
            continuous_marquee=False,
          )
        else:
          self._display.set_persistent_texts(texts=['...'], continuous_marquee=False)
        time.sleep(DISPLAY_POLL_INTERVAL_SEC)
    except Exception:
      logger.exception('playing track display thread crashed')
