from threading import Thread, Event
from display_state import DisplayState
from volumio_thread import VolumioThread
import time
from utils import format_min_sec

class PlayingTrackElapsedTimeDisplayThread(Thread):

  def __init__(self, volumio:VolumioThread, display:DisplayState, stop_event:Event, duration:float=6.0):
    super().__init__()
    self._volumio = volumio
    self._display = display
    self._duration = duration
    self._stop_event = stop_event

  def run(self):
    start = time.time()
    while not self._stop_event.is_set() and time.time() - start <= self._duration:
      elapsed = self._volumio.get_seek()
      duration = self._volumio.get_duration()
      percentage = round(elapsed / duration * 100)
      elapsed_text = format_min_sec(elapsed).rjust(6,' ')
      percentage_text = str(percentage).rjust(3,' ')
      self._display.display_temporary_texts([' '+elapsed_text+'  '+percentage_text+' '],0.25)
      time.sleep(0.25)