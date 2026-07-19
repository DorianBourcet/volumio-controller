import re
import time
from threading import Event, Thread

from unidecode import unidecode

import logging_setup
import utils

logger = logging_setup.get_logger(__name__)

DISPLAY_WIDTH = 12
MARQUEE_TAIL_PADDING = ' ' * 13


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
    super().__init__(name=self.__class__.__name__)
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

  def _print(self, text: str) -> None:
    upper = text.upper().replace('N°', 'No').replace(':', ' ')
    self._display_state.print(unidecode(upper), self._bypass_sleep_mode)

  def _animate(self, text: str, align_left: bool, length: int) -> None:
    if align_left:
      full_text = self._text_left(text, length)
    else:
      full_text = self._text_center(text, length)
    self._print(full_text)
    if self._stop_event.is_set():
      return
    splitted_text = utils.split_text(text)
    sleep_time = 0.25 / max(length, 1)
    time.sleep(0.1)
    for i in range(len(splitted_text)):
      if self._stop_event.is_set():
        return
      partial = ''.join(splitted_text[:i]) + ' ' + ''.join(splitted_text[i + 1:])
      if align_left:
        rendered = self._text_left(partial, length)
      else:
        rendered = self._text_center(partial, length)
      self._print(rendered)
      time.sleep(sleep_time)

  def _on_marquee_must_trim_start(self) -> bool:
    return False

  def _text_center(self, text: str, length: int) -> str:
    total_spaces = DISPLAY_WIDTH - length
    after_spaces = total_spaces // 2
    before_spaces = total_spaces - after_spaces
    return ' ' * before_spaces + text + ' ' * after_spaces

  def _text_left(self, text: str, length: int) -> str:
    total_spaces = DISPLAY_WIDTH - length
    return text + ' ' * total_spaces

  def _pretty_print(self, text: str, align_left: bool, length: int, animate: bool) -> None:
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
    while not self._stop_event.is_set() and now <= start + duration:
      time.sleep(self._display_state.marquee_sleep_delay)
      now = time.time()

  def _pretty_marquee(self, text: str, trim_start: bool = False) -> None:
    text = text + MARQUEE_TAIL_PADDING
    if not trim_start:
      text = ' ' * DISPLAY_WIDTH + text
    parts = re.findall(r'([^\.]\.|[^\.]|\.)', text)
    if len(parts) <= DISPLAY_WIDTH:
      length = utils.get_length(text)
      self._pretty_print(text, True, min(length, DISPLAY_WIDTH), False)
      return
    start = 0
    delay_start = trim_start
    while not self._stop_event.is_set() and start < len(parts) - DISPLAY_WIDTH:
      self._print(''.join(parts[start:start + DISPLAY_WIDTH]))
      if delay_start:
        delay_start = False
      else:
        start += 1
      time.sleep(self._display_state.marquee_sleep_delay)

  def _after_run(self) -> None:
    pass

  def run(self) -> None:
    try:
      if self._stop_event.is_set():
        return
      self._display_state.currently_selected_text = self._text_to_display
      length = utils.get_length(self._text_to_display)
      if length <= DISPLAY_WIDTH:
        animate = self._wave and not self._waved
        self._pretty_print(self._text_to_display, self._align_left, length, animate)
        self._waved = True
      else:
        self._pretty_marquee(self._text_to_display, self._on_marquee_must_trim_start())
      if not self._stop_event.is_set():
        self._after_run()
    except Exception:
      logger.exception('display thread crashed')
