import time
from enum import Enum
from itertools import cycle
from threading import Event, Lock

import board
import busio as io
import adafruit_ht16k33.segments

import logging_setup
from continuous_marquee_display_thread import ContinuousMarqueeDisplayThread
from persistent_display_thread import PersistentDisplayThread
from temporary_display_thread import TemporaryDisplayThread

logger = logging_setup.get_logger(__name__)


class ActivityLevel(Enum):
  """Display activity levels.

  CONTROL is the only unlocked level (a button was pressed recently); the two
  resting levels are locked. LISTENING is the resting level while music plays,
  STANDBY the resting level while paused or stopped (``home_holding`` /
  ``home_sleeping``)."""

  CONTROL = 'control'
  LISTENING = 'listening'
  STANDBY = 'standby'


# level -> (brightness, marquee_sleep_delay)
_ACTIVITY_LEVEL_SETTINGS: dict[ActivityLevel, tuple[float, float]] = {
  ActivityLevel.CONTROL: (1.0, 0.15),
  ActivityLevel.LISTENING: (0.5, 0.20),
  ActivityLevel.STANDBY: (0.05, 0.20),
}


class DisplayState:
  EMPTY_TEXT = '            '

  I2C_RETRY_AFTER_SEC = 0.05

  def __init__(self):
    i2c = io.I2C(board.SCL, board.SDA)
    self._display = adafruit_ht16k33.segments.Seg14x4(i2c, address=[0x70, 0x71, 0x72])
    self._stop_event = Event()
    self._persistent_display_daemon_stop_event = Event()
    self._temporary_display_daemon_stop_event = Event()
    self._print_lock = Lock()
    self.displaying_persistent = False
    self._persistent_texts: list[str] = ['.  ', '.. ', '...', ' ..', '  .', '']
    self._persistent_texts_iterable = cycle(self._persistent_texts)
    self._persistent_texts_continuous_marquee = False
    self._persistent_text_duration = 5.0
    self._sleep_mode = False
    self._latest_text: str = self.EMPTY_TEXT
    self.temporary_text_duration = 2.0
    self.temporary_text: str | None = None
    self.currently_selected_text: str | None = None
    self.marquee_sleep_delay = 0.20
    self._current_activity_level: ActivityLevel | None = None
    self.set_activity_level(ActivityLevel.STANDBY)

  def _safe_i2c_write(self, text: str) -> None:
    """Write to the HT16K33 with one retry on transient I²C errors.

    Volumio runs on a Pi where the I²C bus occasionally throws ENXIO/EIO.
    Swallowing these is preferable to taking the whole controller down."""
    try:
      self._display.print(text)
    except OSError as ex:
      logger.warning('I²C write failed (%s), retrying once', ex)
      time.sleep(self.I2C_RETRY_AFTER_SEC)
      try:
        self._display.print(text)
      except OSError:
        logger.exception('I²C write failed again, dropping frame')

  def _issue_stop_event(self) -> Event:
    self._stop_event.set()
    self._stop_event = Event()
    return self._stop_event

  def print(self, text: str | None = None, bypass_sleep_mode: bool = False) -> None:
    with self._print_lock:
      if text is not None:
        self._latest_text = text
      else:
        text = self.EMPTY_TEXT
      if self._sleep_mode and not bypass_sleep_mode:
        text = self.EMPTY_TEXT
      self._safe_i2c_write(text)

  def issue_persistent_display_daemon_stop_event(self) -> Event:
    self._persistent_display_daemon_stop_event.set()
    self._persistent_display_daemon_stop_event = Event()
    return self._persistent_display_daemon_stop_event

  def issue_temporary_display_daemon_stop_event(self) -> Event:
    self._temporary_display_daemon_stop_event.set()
    self._temporary_display_daemon_stop_event = Event()
    return self._temporary_display_daemon_stop_event

  def set_activity_level(self, level: ActivityLevel) -> None:
    if level is self._current_activity_level:
      return
    brightness, marquee_sleep_delay = _ACTIVITY_LEVEL_SETTINGS[level]
    with self._print_lock:
      try:
        self._display.brightness = brightness
      except OSError:
        logger.exception('failed to set %s brightness', level.value)
      self.marquee_sleep_delay = marquee_sleep_delay
      self._current_activity_level = level

  def enable_sleep_mode(self) -> None:
    if not self._sleep_mode:
      self._sleep_mode = True
      self.print()

  def disable_sleep_mode(self) -> None:
    if self._sleep_mode:
      self._sleep_mode = False
      self.print(self._latest_text)

  def display_persistent_texts(
    self,
    texts: list[str] | None = None,
    duration: float | None = None,
    continuous_marquee: bool | None = None,
    marquee_trim_start: bool = False,
    stop_daemons: bool = True,
  ) -> None:
    if continuous_marquee is not None:
      self._persistent_texts_continuous_marquee = continuous_marquee
    if duration is not None:
      self._persistent_text_duration = duration
    if stop_daemons:
      self.issue_persistent_display_daemon_stop_event()
      self.issue_temporary_display_daemon_stop_event()
    self.displaying_persistent = True
    if texts is not None:
      self.set_persistent_texts(texts)
    elif self._persistent_texts_continuous_marquee:
      ContinuousMarqueeDisplayThread(
        self,
        ' '.join(self._persistent_texts),
        self._issue_stop_event(),
      ).start()
    else:
      PersistentDisplayThread(
        self,
        next(self._persistent_texts_iterable),
        self._issue_stop_event(),
        self._persistent_text_duration,
        marquee_trim_start,
      ).start()

  def set_persistent_texts(
    self,
    texts: list[str],
    duration: float | None = None,
    continuous_marquee: bool | None = None,
  ) -> None:
    if continuous_marquee is not None:
      self._persistent_texts_continuous_marquee = continuous_marquee
    if duration is not None:
      self._persistent_text_duration = duration
    if texts != self._persistent_texts:
      self._persistent_texts = texts
      self._persistent_texts_iterable = cycle(texts)
      if self.displaying_persistent:
        if texts and texts[0] == self.currently_selected_text:
          next(self._persistent_texts_iterable)
        else:
          self._issue_stop_event()
          self.display_persistent_texts(stop_daemons=False)

  def display_temporary_text(
    self,
    text: str,
    duration: float = 2.0,
    marquee_trim_start: bool = False,
    wave: bool = False,
    align_left: bool = False,
    trim_next_persistent_marquee: bool = False,
    stop_daemons: bool = True,
  ) -> None:
    if stop_daemons:
      self.issue_temporary_display_daemon_stop_event()
    self.displaying_persistent = False
    self.temporary_text = text
    self.temporary_text_duration = duration
    TemporaryDisplayThread(
      self,
      self.temporary_text,
      self._issue_stop_event(),
      marquee_trim_start,
      align_left,
      wave,
      trim_next_persistent_marquee,
    ).start()

  def clear_temporary_display(self) -> None:
    self.issue_temporary_display_daemon_stop_event()
    self._issue_stop_event()

  def clear_persistent_display(self) -> None:
    self.issue_persistent_display_daemon_stop_event()
    self.set_persistent_texts(texts=[''])

  def shutdown(self) -> None:
    """Stop all display threads and blank the screen."""
    self.issue_persistent_display_daemon_stop_event()
    self.issue_temporary_display_daemon_stop_event()
    self._issue_stop_event()
    self.print()
