from threading import Thread, Event
from display_state import DisplayState
from volumio_thread import VolumioThread
import time
from utils import format_min_sec

class TrackElapsedTimeDisplayThread(Thread):

  def __init__(self, volumio:VolumioThread, display:DisplayState, stop_event:Event):
    super().__init__()
    self._volumio = volumio
    self._display = display
    self._stop_event = stop_event

  def _produce_elapsed_time_text(self) -> str:
    elapsed = self._volumio.get_seek()
    duration = self._volumio.get_duration()
    if duration != 0 and elapsed <= duration:
      percentage = round(elapsed / duration * 100)
    else:
      percentage = ''
    elapsed_text = format_min_sec(elapsed).rjust(6,' ')
    duration_text = format_min_sec(duration).rjust(6,' ')
    percentage_text = str(percentage).rjust(3,' ')
    return ' '+elapsed_text+'  '+duration_text+' '
  
  def run(self):
    pass