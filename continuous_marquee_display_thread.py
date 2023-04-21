from display_thread import DisplayThread
from threading import Event
import re
import time

class ContinuousMarqueeDisplayThread(DisplayThread):

  def __init__(self, display_state, text_to_display: str, stop_event: Event):
    super().__init__(display_state,text_to_display,stop_event)

  def _continuous_marquee(self, text: str):
    text = text+' '
    start = 0
    parts = re.findall('([^\.]\.|[^\.]|\.)', text)
    length = len(parts)
    while not self._stop_event.is_set():
      acc = []
      idx = start
      i = 0
      while i < 12:
        if idx >= length:
          idx = 0
        acc.append(parts[idx])
        idx += 1
        i += 1
      self._print(''.join(acc))
      start += 1
      if start >= length:
        start = 0
      time.sleep(0.25)
  
  def run(self):
    if self._stop_event.is_set():
      return
    self._continuous_marquee(self._text_to_display)
