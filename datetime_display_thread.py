import math
import time
from datetime import datetime
from threading import Thread

import pytz

import logging_setup
from constants import DISPLAY_POLL_INTERVAL_SEC
from display_state import DisplayState

logger = logging_setup.get_logger(__name__)

TIMEZONE = pytz.timezone('America/Toronto')


class DatetimeDisplayThread(Thread):

  def __init__(self, display: DisplayState):
    super().__init__(name='datetime')
    self._display = display
    self._clock_tick = True
    self._latest_timestamp = None
    self.daemon = True

  def _display_datetime(self) -> None:
    now = math.ceil(time.time())
    if now != self._latest_timestamp:
      self._latest_timestamp = now
      self._clock_tick = not self._clock_tick
    separator = '.' if self._clock_tick else ''
    now_dt = datetime.now(TIMEZONE)
    day = now_dt.strftime('%-d').rjust(2, ' ')
    month = now_dt.strftime('%-m').ljust(2, ' ')
    hours = now_dt.strftime('%-H').rjust(2, ' ')
    minutes = now_dt.strftime('%M')
    self._display.set_persistent_texts(
      texts=[f' {day}.{month}  {hours}{separator}{minutes} '],
      continuous_marquee=False,
    )

  def run(self) -> None:
    try:
      stop_event = self._display.issue_persistent_display_daemon_stop_event()
      while not stop_event.is_set():
        self._display_datetime()
        time.sleep(DISPLAY_POLL_INTERVAL_SEC)
    except Exception:
      logger.exception('datetime display thread crashed')
