import signal
import time

kill_now = False
shutdown_machine = False

def exit_gracefully(*args):
  global kill_now
  print('ordered exiting...')
  kill_now = True

signal.signal(signal.SIGINT, exit_gracefully)
signal.signal(signal.SIGTERM, exit_gracefully)
