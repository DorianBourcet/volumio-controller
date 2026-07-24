from threading import Event, Thread

import logging_setup
from display_state import DisplayState
from radio_state_machine import RadioStateMachine
from user_input import UserInput
from user_input_listener import UserInputListener
from vigie_thread import VigieThread
from volumio_thread import VolumioThread

logger = logging_setup.get_logger(__name__)

ENCODER_ADDRESSES = (0x36, 0x37, 0x38, 0x3a)


class MainThread(Thread):

  def __init__(self, display: DisplayState):
    super().__init__(name='main')
    self._display = display
    self._stop_event = Event()
    self._listeners: list[UserInputListener] = []
    self._volumio: VolumioThread = None
    self._vigie: VigieThread = None
    self._vigie_stop_event: Event = None
    self._radio: RadioStateMachine = None
    self.daemon = True

  def _start_subsystems(self) -> None:
    self._display.display_persistent_texts(stop_daemons=False, duration=0.25)
    self._volumio = VolumioThread()
    self._volumio.daemon = True
    self._volumio.start()
    self._vigie_stop_event = Event()
    self._radio = RadioStateMachine(self._volumio, self._display, self._vigie_stop_event)
    self._vigie = VigieThread(self._volumio, self._radio, self._vigie_stop_event)
    self._vigie.start()
    for idx, addr in enumerate(ENCODER_ADDRESSES, start=1):
      try:
        listener = UserInputListener(UserInput(addr), self._radio, idx, self._stop_event)
      except Exception:
        logger.exception('failed to initialize encoder %d at 0x%02x', idx, addr)
        continue
      listener.daemon = True
      listener.start()
      self._listeners.append(listener)
    logger.info('subsystems started (%d encoders active)', len(self._listeners))

  def run(self) -> None:
    try:
      self._start_subsystems()
      was_ready = False
      while not self._stop_event.is_set():
        ready = self._volumio.is_ready()
        if ready and not was_ready:
          self._radio.back_home()
        elif not ready and was_ready:
          logger.warning('lost connection to volumio, awaiting reconnect')
          self._radio.wait_for_connection()
        was_ready = ready
        self._stop_event.wait(0.5)
    except Exception:
      logger.exception('main thread crashed')

  def stop(self, timeout: float = 3.0) -> None:
    logger.info('stopping main thread')
    self._stop_event.set()
    if self._vigie_stop_event is not None:
      self._vigie_stop_event.set()
    if self._volumio is not None:
      try:
        self._volumio.shutdown()
      except Exception:
        logger.exception('error while shutting down volumio thread')
    threads: list[Thread] = []
    threads.extend(self._listeners)
    if self._vigie is not None:
      threads.append(self._vigie)
    if self._volumio is not None:
      threads.append(self._volumio)
    for t in threads:
      try:
        t.join(timeout=timeout)
      except RuntimeError:
        pass
