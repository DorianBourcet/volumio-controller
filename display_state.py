import time
from enum import Enum
from threading import Event, Lock

import board
import busio as io
import adafruit_ht16k33.segments

import logging_setup
from persistent_display_thread import PersistentDisplayThread
from temporary_display_thread import TemporaryDisplayThread

logger = logging_setup.get_logger(__name__)


class ActivityLevel(Enum):

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
    self._persistent_texts_continuous_marquee = False
    self._persistent_text_duration = 5.0
    self._sleep_mode = False
    self._latest_text: str = self.EMPTY_TEXT
    self.temporary_text_duration = 2.0
    self.temporary_text: str | None = None
    self.currently_selected_text: str | None = None
    self.marquee_sleep_delay = 0.20
    self._persistent_gen = 0
    self._persistent_loop: PersistentDisplayThread | None = None
    self._current_activity_level: ActivityLevel | None = None
    self.set_activity_level(ActivityLevel.STANDBY)

  def _safe_i2c_write(self, text: str) -> None:
    """Write to the HT16K33 with one retry on transient I2C errors.

    Volumio runs on a Pi where the I2C bus occasionally throws ENXIO/EIO.
    Ignoring these is preferable to taking the whole controller down."""
    try:
      self._display.print(text)
    except OSError as ex:
      logger.warning('I2C write failed (%s), retrying once', ex)
      time.sleep(self.I2C_RETRY_AFTER_SEC)
      try:
        self._display.print(text)
      except OSError:
        logger.exception('I2C write failed again, dropping frame')

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

  def persistent_gen(self) -> int:
    return self._persistent_gen

  def persistent_render_spec(self) -> tuple[list[str], bool, float, int]:
    with self._print_lock:
      return (
        list(self._persistent_texts),
        self._persistent_texts_continuous_marquee,
        self._persistent_text_duration,
        self._persistent_gen,
      )

  def _ensure_persistent_loop(self, marquee_trim_start: bool = False) -> None:
    self.displaying_persistent = True
    if self._persistent_loop is not None and self._persistent_loop.is_running():
      return
    self._persistent_loop = PersistentDisplayThread(
      self, self._issue_stop_event(), marquee_trim_start,
    )
    self._persistent_loop.start()

  def display_persistent_texts(
    self,
    texts: list[str] | None = None,
    duration: float | None = None,
    continuous_marquee: bool | None = None,
    marquee_trim_start: bool = False,
    stop_daemons: bool = True,
  ) -> None:
    changed = False
    if continuous_marquee is not None:
      if continuous_marquee != self._persistent_texts_continuous_marquee:
        changed = True
      self._persistent_texts_continuous_marquee = continuous_marquee
    if duration is not None:
      if duration != self._persistent_text_duration:
        changed = True
      self._persistent_text_duration = duration
    if stop_daemons:
      self.issue_persistent_display_daemon_stop_event()
      self.issue_temporary_display_daemon_stop_event()
    if texts is not None and texts != self._persistent_texts:
      self._persistent_texts = texts
      changed = True
    loop_running = self._persistent_loop is not None and self._persistent_loop.is_running()
    if changed or not loop_running:
      self._persistent_gen += 1
    self._ensure_persistent_loop(marquee_trim_start)

  def set_persistent_texts(
    self,
    texts: list[str],
    duration: float | None = None,
    continuous_marquee: bool | None = None,
  ) -> None:
    changed = False
    if continuous_marquee is not None:
      if continuous_marquee != self._persistent_texts_continuous_marquee:
        changed = True
      self._persistent_texts_continuous_marquee = continuous_marquee
    if duration is not None:
      if duration != self._persistent_text_duration:
        changed = True
      self._persistent_text_duration = duration
    if texts != self._persistent_texts:
      self._persistent_texts = texts
      changed = True
    if changed:
      self._persistent_gen += 1
      if self.displaying_persistent:
        self._ensure_persistent_loop()

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

  def shutdown(self) -> None:
    """Stop all display threads and blank the screen."""
    self.issue_persistent_display_daemon_stop_event()
    self.issue_temporary_display_daemon_stop_event()
    self._issue_stop_event()
    self.print()
