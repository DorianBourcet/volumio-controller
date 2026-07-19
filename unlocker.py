import time
from collections.abc import Callable
from threading import Event, Thread

import logging_setup
from display_state import ActivityLevel, DisplayState

logger = logging_setup.get_logger(__name__)


class Unlocker:

  def __init__(self, display: DisplayState, locked_event: Event, on_unlock: Callable[[], None]):
    self._display = display
    self._locked_event = locked_event
    self._on_unlock = on_unlock
    self._has_run_event = Event()
    self._can_unlock = False
    self._thread = None

  def _spawn_thread(self) -> None:
    self._thread = UnlockerThread(
      self._display, self._locked_event, self._has_run_event, self._on_unlock
    )
    self._thread.start()

  def bump(self) -> None:
    if not self._locked_event.is_set():
      logger.warning('bump called while unlocked, ignoring')
      return
    if self._thread is None:
      logger.debug('unlocker: spawning new thread')
      self._spawn_thread()
      return
    if self._has_run_event.is_set():
      self._has_run_event.clear()
      logger.debug('unlocker: thread finished, respawning')
      self._spawn_thread()
      return
    self._thread.bump()


class UnlockerThread(Thread):

  UNLOCK_BUMPS = 12
  BUMP_STEP = 4
  DECREASE_STEP = 2
  DECREASE_AFTER_SEC = 0.50
  POLL_INTERVAL_SEC = 0.05

  def __init__(
    self,
    display: DisplayState,
    locked_event: Event,
    has_run_event: Event,
    on_unlock: Callable[[], None],
  ):
    super().__init__(name='unlocker')
    self._display = display
    self._locked_event = locked_event
    self._has_run_event = has_run_event
    self._on_unlock = on_unlock
    self._last_bump_time = None
    self._bump_number = 0
    self._reached_unlock = False
    self.daemon = True

  def bump(self) -> None:
    if not self.is_alive():
      logger.warning('unlocker thread bump called while dead')
      return
    self._last_bump_time = time.time()
    self._increase_bump_number()
    if self._bump_number >= self.UNLOCK_BUMPS and not self._reached_unlock:
      self._locked_event.clear()
      self._display.set_activity_level(ActivityLevel.CONTROL)
      self._reached_unlock = True
      logger.debug('unlocker: reached unlock threshold')
      # Restart the 30 s inactivity window so the display returns to its
      # resting level (e.g. STANDBY at home_sleeping) after the gesture unlock.
      self._on_unlock()

  def _increase_bump_number(self) -> None:
    self._bump_number = min(self._bump_number + self.BUMP_STEP, self.UNLOCK_BUMPS)
    self._display.display_temporary_text(text=self._bump_number * '.', duration=0.5)

  def _decrease_bump_number(self) -> None:
    self._bump_number -= self.DECREASE_STEP
    self._display.display_temporary_text(text=self._bump_number * '.', duration=0.05)

  def _should_decrease(self) -> bool:
    return time.time() - self._last_bump_time >= self.DECREASE_AFTER_SEC

  def run(self) -> None:
    try:
      self.bump()
      while self._bump_number > 0 and not self._reached_unlock:
        if self._should_decrease():
          self._decrease_bump_number()
        time.sleep(self.POLL_INTERVAL_SEC)
      self._has_run_event.set()
    except Exception:
      logger.exception('unlocker thread crashed')
      self._has_run_event.set()
