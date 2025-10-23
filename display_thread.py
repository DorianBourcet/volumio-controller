import re
import time
from threading import Thread, Event
from unidecode import unidecode
import utils

class DisplayThread(Thread):

  def __init__(
    self, 
    display_state,
    text_to_display: str,
    stop_event: Event,
    duration: float = 5.0,
    align_left: bool = False,
    wave: bool = False,
    bypass_sleep_mode: bool = False,
  ):
    super().__init__()
    self._display_state = display_state
    self._text_to_display = text_to_display
    self._stop_event = stop_event
    self._duration = duration
    self._align_left = align_left
    self._wave = wave
    self._bypass_sleep_mode = bypass_sleep_mode
    self._waved = False
    self.daemon = True

  def _get_duration(self) -> float:
    return self._duration

  def _print(self, text: str):
    upper = text.upper().replace('N°','No').replace(':','..')
    self._display_state.print(unidecode(upper), self._bypass_sleep_mode)

  def _animate(self, text: str, align_left: bool, length: int):
    if align_left:
      full_text = self._text_left(text, length)
    else:
      full_text = self._text_center(text, length)
    self._print(full_text)
    if self._stop_event.is_set():
      return
    splitted_text = utils.split_text(text)
    sleep_time = 0.25 / length
    time.sleep(0.1)
    for i in range(len(splitted_text)):
      if self._stop_event.is_set():
        return
      if align_left:
        str = self._text_left(''.join(splitted_text[:i]) + ' ' + ''.join(splitted_text[i+1:]), length)
      else:
        str = self._text_center(''.join(splitted_text[:i]) + ' ' + ''.join(splitted_text[i+1:]), length)
      self._print(str)
      time.sleep(sleep_time)

  def _on_marquee_must_trim_start(self):
    return False
  
  def _text_center(self, text: str, length: int):
    total_spaces = 12-length
    after_spaces = total_spaces//2
    before_spaces = total_spaces-after_spaces
    return ' '*before_spaces+text+' '*after_spaces
  
  def _text_left(self, text: str, length: int):
    total_spaces = 12-length
    return text+' '*total_spaces

  def _pretty_print(self, text: str, align_left: bool, length: int, animate: bool):
    duration = self._get_duration()
    if align_left:
      full_text = self._text_left(text, length)
    else:
      full_text = self._text_center(text, length)
    start = time.time()
    if self._stop_event.is_set():
      return
    if animate:
      self._animate(text, align_left, length)
    if self._stop_event.is_set():
      return
    self._print(full_text)
    now = start
    while not self._stop_event.is_set() and now <= start+duration:
      time.sleep(self._display_state.marquee_sleep_delay)
      now = time.time()

  def _pretty_marquee(self, text: str, trim_start: bool = False):
    text = text+' '*13
    if not trim_start:
      text = ' '*12+text
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
    self._display_state.currently_selected_text = self._text_to_display
    length = utils.get_length(self._text_to_display)
    if length <= 12:
      if self._wave and not self._waved:
        animate = True
      else:
        animate = False
      self._pretty_print(self._text_to_display,self._align_left,length,animate)
      self._waved = True
    else:
      self._pretty_marquee(self._text_to_display, self._on_marquee_must_trim_start())
    if not self._stop_event.is_set():
      self._after_run()
