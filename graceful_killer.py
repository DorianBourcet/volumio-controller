import signal
from threading import Event

import logging_setup

_logger = logging_setup.get_logger(__name__)


class GracefulKiller:
  """Coordinator for cooperative shutdown.

  Holds a `kill_event` that the main loop waits on and a `shutdown_machine`
  flag to request a host-level halt after the application has finished
  cleaning up.
  """

  def __init__(self) -> None:
    self.kill_event = Event()
    self.shutdown_machine = False
    signal.signal(signal.SIGINT, self._handle_signal)
    signal.signal(signal.SIGTERM, self._handle_signal)

  def _handle_signal(self, *_args) -> None:
    if not self.kill_event.is_set():
      _logger.info('shutdown signal received, exiting gracefully')
    self.kill_event.set()

  def request_shutdown(self, halt_machine: bool = False) -> None:
    if halt_machine:
      self.shutdown_machine = True
    self.kill_event.set()

  def wait(self) -> None:
    self.kill_event.wait()


killer = GracefulKiller()
