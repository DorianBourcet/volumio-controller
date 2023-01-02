from threading import Thread, Event
from display_state import DisplayState
from volumio_thread import VolumioThread
import time
from utils import format_elapsed_time_text

class TrackElapsedTimeDisplayThread(Thread):

  def __init__(self, volumio:VolumioThread, display:DisplayState, stop_event:Event):
    super().__init__()
    self._volumio = volumio
    self._display = display
    self._stop_event = stop_event

  def _produce_elapsed_time_text(self) -> str:
    elapsed = self._volumio.get_seek()
    duration = self._volumio.get_duration()
    return format_elapsed_time_text(elapsed,duration)
  
  def run(self):
    pass