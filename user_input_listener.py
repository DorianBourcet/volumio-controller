import time
from threading import Event, Thread

import logging_setup
from radio_state_machine import RadioStateMachine
from user_input import UserInput

logger = logging_setup.get_logger(__name__)


class UserInputListener(Thread):

  POLL_INTERVAL_SEC = 0.05

  def __init__(
    self,
    user_input: UserInput,
    radio: RadioStateMachine,
    input_number: int,
    stop_event: Event | None = None,
  ):
    super().__init__(name=f'input-{input_number}')
    self._user_input = user_input
    self._radio = radio
    self._input_number = input_number
    self._stop_event = stop_event or Event()

  def run(self) -> None:
    try:
      while not self._stop_event.is_set():
        try:
          if self._user_input.turned_right():
            self._radio.user_input_right(self._input_number)
          elif self._user_input.turned_left():
            self._radio.user_input_left(self._input_number)
          elif self._user_input.pressed():
            self._radio.user_input_pressed(self._input_number)
          elif self._user_input.released():
            self._radio.user_input_released(self._input_number)
        except OSError:
          logger.warning('I/O error reading encoder %d, will retry', self._input_number)
          time.sleep(0.2)
        except Exception:
          logger.exception('encoder %d handler raised', self._input_number)
        time.sleep(self.POLL_INTERVAL_SEC)
    except Exception:
      logger.exception('input listener %d crashed', self._input_number)
