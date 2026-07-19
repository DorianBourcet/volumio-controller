import time
from threading import Thread
from typing import Any

import logging_setup
import utils
from display_state import DisplayState
from radio_state_machine import RadioStateMachine
from volumio_menu import VolumioMenu

logger = logging_setup.get_logger(__name__)


class MenuThread(Thread):

  CLOSE_AFTER_SEC = 30.0
  POLL_INTERVAL_SEC = 0.25

  def __init__(self, display: DisplayState, radio: RadioStateMachine):
    super().__init__(name='menu')
    self._display = display
    self._radio = radio
    self._stop_event = None
    self._selected_index = 0
    self._current_options: list[dict[str, Any]] = []
    self._history: list[dict[str, Any]] = []
    self._volumio_menu = VolumioMenu('volumio')
    self._last_input_time: float | None = None
    self.daemon = True

  def _home(self) -> None:
    options = self._volumio_menu.browse()
    self._render_options(options)
    self._history = []

  def _select(self, selected_option: dict[str, Any]) -> None:
    provider = selected_option['provider']
    uri = selected_option['uri']
    result = self._browse_provider(provider, uri)
    if isinstance(result, list):
      self._render_options(result)
      self._history.append(selected_option)
    elif isinstance(result, dict):
      message = result['message']
      must_close = result['terminated']
      self._display.display_temporary_text(text=message, wave=True, duration=3.5)
      if must_close:
        self.close()

  def _browse_provider(self, provider: str, uri: str):
    if provider == 'volumio':
      return self._volumio_menu.browse(uri)
    if provider == 'internal':
      return self._select_internal(uri)
    logger.warning('unknown menu provider %r', provider)
    return None

  def _render_options(self, options: list[dict[str, Any]]) -> None:
    if options is None:
      options = []
    options.append({
      'name': '< RETOUR',
      'uri': 'back',
      'provider': 'internal',
    })
    self._current_options = options
    self._display_first()

  def _get_option_name(self, index: int) -> str:
    return self._current_options[index]['name']

  def _get_option(self, index: int) -> dict[str, Any]:
    return self._current_options[index]

  def _display_first(self) -> None:
    self._selected_index = 0
    if not self._current_options:
      return
    self._display.set_persistent_texts(
      texts=[self._get_option_name(self._selected_index)],
      continuous_marquee=True,
    )

  def display_next(self) -> None:
    self._last_input_time = time.time()
    if not self._current_options:
      return
    next_selected_index = self._selected_index + 1
    if next_selected_index >= len(self._current_options):
      next_selected_index = 0
    self._selected_index = next_selected_index
    option_name = self._get_option_name(self._selected_index)
    self._display.display_temporary_text(
      text=utils.shorten_text(option_name), duration=1.0, align_left=True,
    )
    self._display.set_persistent_texts(texts=[option_name], continuous_marquee=True)

  def display_previous(self) -> None:
    self._last_input_time = time.time()
    if not self._current_options:
      return
    previous_selected_index = self._selected_index - 1
    if previous_selected_index < 0:
      previous_selected_index = len(self._current_options) - 1
    self._selected_index = previous_selected_index
    option_name = self._get_option_name(self._selected_index)
    self._display.display_temporary_text(
      text=utils.shorten_text(option_name), duration=1.0, align_left=True,
    )
    self._display.set_persistent_texts(texts=[option_name], continuous_marquee=True)

  def select_current(self) -> None:
    self._last_input_time = time.time()
    self._display.set_persistent_texts(texts=['...'], continuous_marquee=False)
    if not self._current_options:
      return
    option = self._get_option(self._selected_index)
    self._select(option)

  def _select_internal(self, uri: str):
    if uri == 'back':
      if not self._history:
        self.close()
        return None
      self._history.pop()
      if self._history:
        option = self._history[-1]
        return self._browse_provider(option['provider'], option['uri'])
      return self._volumio_menu.browse()
    return None

  def _should_close(self) -> bool:
    if self._last_input_time is None:
      return False
    return time.time() - self._last_input_time >= self.CLOSE_AFTER_SEC

  def back(self) -> None:
    self._last_input_time = time.time()
    if not self._history:
      self.close()
      return
    self._history.pop()
    if self._history:
      option = self._history[-1]
      result = self._browse_provider(option['provider'], option['uri'])
    else:
      result = self._volumio_menu.browse()
    if isinstance(result, list):
      self._render_options(result)

  def close(self) -> None:
    if not self.is_alive():
      logger.warning('cannot close menu thread before it has started')
      return
    if self._stop_event:
      self._stop_event.set()
    try:
      self._radio.close_menu()
    except Exception:
      logger.exception('error during radio.close_menu()')

  def run(self) -> None:
    try:
      self._last_input_time = time.time()
      self._stop_event = self._display.issue_persistent_display_daemon_stop_event()
      self._home()
      while not self._stop_event.is_set():
        if self._should_close():
          self.close()
        time.sleep(self.POLL_INTERVAL_SEC)
    except Exception:
      logger.exception('menu thread crashed')
