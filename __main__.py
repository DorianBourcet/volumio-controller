from main_thread import MainThread
from volumio_menu import VolumioMenu

def main():
  thread = MainThread()
  thread.start()
  thread.join()

main()