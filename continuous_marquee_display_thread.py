import re
import time
from threading import Event

import logging_setup
from display_thread import DisplayThread

logger = logging_setup.get_logger(__name__)

DISPLAY_WIDTH = 12


class ContinuousMarqueeDisplayThread(DisplayThread):

  POLL_INTERVAL_SEC = 0.25

  def __init__(self, display_state, text_to_display: str, stop_event: Event):
    super().__init__(display_state, text_to_display, stop_event)

  def _continuous_marquee(self, text: str) -> None:
    text = text + '  '
    parts = re.findall(r'([^\.]\.|[^\.]|\.)', text)
    length = len(parts)
    if length == 0:
      return
    start = 0
    while not self._stop_event.is_set():
      acc = []
      idx = start
      for _ in range(DISPLAY_WIDTH):
        if idx >= length:
          idx = 0
        acc.append(parts[idx])
        idx += 1
      self._print(''.join(acc))
      start += 1
      if start >= length:
        start = 0
      time.sleep(self.POLL_INTERVAL_SEC)

  def run(self) -> None:
    try:
      if self._stop_event.is_set():
        return
      self._continuous_marquee(self._text_to_display)
    except Exception:
      logger.exception('continuous marquee thread crashed')
