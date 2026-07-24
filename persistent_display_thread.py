import time
from threading import Event

import logging_setup
import utils
from display_thread import DISPLAY_WIDTH, DisplayThread

logger = logging_setup.get_logger(__name__)


class PersistentDisplayThread(DisplayThread):

  def __init__(
    self,
    display_state,
    stop_event: Event,
    marquee_trim_start: bool = False,
  ):
    super().__init__(display_state, '', stop_event)
    self._marquee_trim_start = marquee_trim_start
    self._gen = -1

  def is_running(self) -> bool:
    # A loop whose stop Event is set is on its way out even if is_alive() is
    # briefly still True, so it must not be reused as the live persistent loop.
    return self.is_alive() and not self._stop_event.is_set()

  def _should_stop(self) -> bool:
    return self._stop_event.is_set() or self._gen != self._display_state.persistent_gen()

  def _on_marquee_must_trim_start(self) -> bool:
    return self._marquee_trim_start

  def _render_once(self, text: str) -> None:
    self._text_to_display = text
    self._display_state.currently_selected_text = text
    length = utils.get_length(text)
    if length <= DISPLAY_WIDTH:
      self._pretty_print(text, self._align_left, length, False)
    else:
      self._pretty_marquee(text, self._on_marquee_must_trim_start())

  def run(self) -> None:
    try:
      while not self._stop_event.is_set():
        texts, continuous, duration, gen = self._display_state.persistent_render_spec()
        self._gen = gen
        self._duration = duration
        if not texts:
          time.sleep(self._display_state.marquee_sleep_delay)
          continue
        if continuous:
          self._text_to_display = ' '.join(texts)
          self._display_state.currently_selected_text = self._text_to_display
          self._continuous_marquee(self._text_to_display)
        else:
          for text in texts:
            if self._should_stop():
              break
            self._render_once(text)
            # trim_start is a one-shot: only the very first frame skips the
            # scroll-in; every subsequent marquee pass scrolls in normally.
            self._marquee_trim_start = False
    except Exception:
      logger.exception('persistent display thread crashed')
