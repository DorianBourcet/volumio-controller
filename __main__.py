import os
import time

import logging_setup

logging_setup.configure()
logger = logging_setup.get_logger(__name__)

import graceful_killer
from display_state import DisplayState
from main_thread import MainThread


def main(display: DisplayState) -> MainThread:
  thread = MainThread(display)
  thread.daemon = True
  thread.start()
  return thread


if __name__ == '__main__':
  logger.info('volumio-controller starting')
  display = DisplayState()
  main_thread = main(display)
  graceful_killer.killer.wait()
  logger.info('shutdown requested, stopping subsystems')
  try:
    main_thread.stop(timeout=3.0)
  except Exception:
    logger.exception('error while stopping main thread')
  try:
    display.shutdown()
  except Exception:
    logger.exception('error while shutting down display')
  if graceful_killer.killer.shutdown_machine:
    logger.info('halting machine')
    os.system('sudo shutdown -h now')
  else:
    logger.info('volumio-controller exited cleanly')
