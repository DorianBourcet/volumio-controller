import time
from threading import Event, Thread

import logging_setup
from constants import DISPLAY_POLL_INTERVAL_SEC
from radio_state_machine import RadioStateMachine
from volumio_thread import VolumioThread

logger = logging_setup.get_logger(__name__)


class VigieThread(Thread):

  def __init__(self, volumio: VolumioThread, radio: RadioStateMachine, stop_event: Event):
    super().__init__(name='vigie')
    self._volumio = volumio
    self._radio = radio
    self._latest_volumio_status = self._volumio.get_status()
    self._stop_event = stop_event
    self.daemon = True

  def run(self) -> None:
    try:
      while not self._stop_event.is_set():
        try:
          status = self._volumio.get_status()
          if self._radio.is_home(allow_substates=True) and status != self._latest_volumio_status:
            self._radio.refresh_home()
            self._latest_volumio_status = self._volumio.get_status()
          # Reconcile resting brightness with the real status every tick, so a
          # locked display converges to STANDBY once Volumio stops. Idempotent.
          self._radio.reconcile_activity_level()
        except Exception:
          logger.exception('vigie tick failed')
        time.sleep(DISPLAY_POLL_INTERVAL_SEC)
      logger.debug('vigie exiting')
    except Exception:
      logger.exception('vigie thread crashed')
