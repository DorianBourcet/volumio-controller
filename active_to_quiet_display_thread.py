import time
from threading import Event, Thread

import logging_setup
from display_state import DisplayState

logger = logging_setup.get_logger(__name__)

POLL_INTERVAL_SEC = 0.25


class ActiveToQuietDisplayThread(Thread):

  def __init__(
    self,
    display: DisplayState,
    stop_event: Event,
    quiet_event: Event,
    quiet_after_sec: int = 30,
  ):
    super().__init__(name='active-to-quiet')
    self._display = display
    self._start = None
    self._quiet_after_sec = quiet_after_sec
    self._stop_event = stop_event
    self._quiet_event = quiet_event
    self.daemon = True

  def should_go_quiet(self) -> bool:
    if self._start is None:
      return False
    return time.time() - self._start >= self._quiet_after_sec

  def run(self) -> None:
    try:
      self._display.set_active_mode()
      self._quiet_event.clear()
      self._start = time.time()
      while not self._stop_event.is_set() and not self.should_go_quiet():
        time.sleep(POLL_INTERVAL_SEC)
      if not self._stop_event.is_set():
        self._display.set_quiet_mode()
        self._quiet_event.set()
    except Exception:
      logger.exception('active-to-quiet thread crashed')
