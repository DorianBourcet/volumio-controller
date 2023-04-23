from main_thread import MainThread
from volumio_menu import VolumioMenu
from display_state import DisplayState
import graceful_killer
import time
import os

def main(display: DisplayState):
  thread = MainThread(display)
  thread.daemon = True
  thread.start()

if __name__ == '__main__':
  display = DisplayState()
  main(display)
  while not graceful_killer.kill_now:
    time.sleep(1)
  time.sleep(2.0)
  display.display.print('            ')
  if graceful_killer.shutdown_machine:
    os.system('sudo shutdown -h now')