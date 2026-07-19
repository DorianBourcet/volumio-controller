import time
from threading import Event, Thread

import logging_setup
from constants import DISPLAY_POLL_INTERVAL_SEC
from display_state import DisplayState
from volumio_thread import VolumioThread

logger = logging_setup.get_logger(__name__)


class TrackSelectorThread(Thread):

  def __init__(
    self,
    index: int,
    name: str,
    volumio: VolumioThread,
    display: DisplayState,
    stop_event: Event,
    select_after_sec: float = 1.0,
  ):
    super().__init__(name='track-selector')
    self._start = None
    self._select_after_sec = select_after_sec
    self._volumio = volumio
    self._display = display
    self._index = index
    self._name = name
    self._stop_event = stop_event
    self.daemon = True

  def should_select(self) -> bool:
    if self._start is None:
      return False
    return time.time() - self._start >= self._select_after_sec

  def run(self) -> None:
    try:
      if self._volumio.get_current_queue_position() == self._index:
        return
      self._start = time.time()
      while not self._stop_event.is_set() and not self.should_select():
        time.sleep(DISPLAY_POLL_INTERVAL_SEC)
      if not self._stop_event.is_set():
        self._volumio.play_track(self._index)
        self._display.display_temporary_text(
          text=self._name, wave=True, duration=2.0, trim_next_persistent_marquee=True,
        )
    except Exception:
      logger.exception('track selector thread crashed')
