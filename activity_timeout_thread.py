import time
from collections.abc import Callable
from threading import Event, Thread

import logging_setup
from display_state import ActivityLevel, DisplayState

logger = logging_setup.get_logger(__name__)

POLL_INTERVAL_SEC = 0.25


class ActivityTimeoutThread(Thread):
  """Drives the display from CONTROL back to a locked resting level.

  On start the display is set to CONTROL (bright, unlocked). After
  ``timeout_sec`` without a new bump, the display locks and the resting level
  is applied by ``apply_resting`` (which picks STANDBY vs LISTENING from the
  real playback status)."""

  def __init__(
    self,
    display: DisplayState,
    stop_event: Event,
    lock_event: Event,
    apply_resting: Callable[[], None],
    timeout_sec: int = 30,
  ):
    super().__init__(name='activity-timeout')
    self._display = display
    self._start = None
    self._timeout_sec = timeout_sec
    self._stop_event = stop_event
    self._lock_event = lock_event
    self._apply_resting = apply_resting
    self.daemon = True

  def _timed_out(self) -> bool:
    if self._start is None:
      return False
    return time.time() - self._start >= self._timeout_sec

  def run(self) -> None:
    try:
      self._display.set_activity_level(ActivityLevel.CONTROL)
      self._lock_event.clear()
      self._start = time.time()
      while not self._stop_event.is_set() and not self._timed_out():
        time.sleep(POLL_INTERVAL_SEC)
      if not self._stop_event.is_set():
        self._lock_event.set()
        self._apply_resting()
    except Exception:
      logger.exception('activity-timeout thread crashed')
