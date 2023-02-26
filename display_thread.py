import re
import time
from threading import Thread, Event
from unidecode import unidecode
import utils

class DisplayThread(Thread):

  def __init__(self, display_state, text_to_display: str, stop_event: Event, wave:bool=False):
    super().__init__()
    self._display_state = display_state
    self._text_to_display = text_to_display
    self._stop_event = stop_event
    self._wave = wave
    self._waved = False

  def _get_duration(self) -> float:
    return 4.0

  def _print(self, text: str):
    upper = text.upper().replace('N°','No')
    self._display_state.display.print(unidecode(upper))

  def _animate(self, text: str):
    self._print(text)
    if self._stop_event.is_set():
      return
    text = utils.split_text(text)
    time.sleep(0.01)
    for i in range(len(text)):
      if self._stop_event.is_set():
        return
      str = ''.join(text[:i]) + ' ' + ''.join(text[i+1:])
      self._print(str)
      time.sleep(0.01)

  def _on_marquee_must_trim_start(self):
    return False

  def _pretty_print(self, text: str, length: int, animate: bool):
    duration = self._get_duration()
    total_spaces = 12-length
    after_spaces = total_spaces//2
    before_spaces = total_spaces-after_spaces
    full_text = ' '*before_spaces+text+' '*after_spaces
    start = time.time()
    if self._stop_event.is_set():
      return
    if animate:
      self._animate(full_text)
    if self._stop_event.is_set():
      return
    self._print(full_text)
    now = start
    while not self._stop_event.is_set() and now <= start+duration:
      time.sleep(self._display_state.marquee_sleep_delay)
      now = time.time()

  def _pretty_marquee(self, text: str, trim_start: bool = False):
    text = text+' '*14
    if not trim_start:
      text = ' '*13+text
    start = 0
    parts = re.findall('([^\.]\.|[^\.]|\.)', text)
    delay_start = trim_start
    while not self._stop_event.is_set() and start < len(parts)-12:
      self._print(''.join(parts[start:start+12]))
      if delay_start:
        delay_start = False
      else:
        start += 1
      time.sleep(self._display_state.marquee_sleep_delay)

  def _after_run(self):
    pass

  def run(self):
    if self._stop_event.is_set():
      return
    length = utils.get_length(self._text_to_display)
    if length <= 12:
      if self._wave and not self._waved:
        animate = True
      else:
        animate = False
      self._pretty_print(self._text_to_display,length,animate)
      self._waved = True
    else:
      self._pretty_marquee(self._text_to_display, self._on_marquee_must_trim_start())
    if not self._stop_event.is_set():
      self._after_run()
