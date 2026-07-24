from threading import Thread

from display_state import DisplayState
from utils import format_min_sec
from volumio_thread import VolumioThread


class TrackElapsedTimeDisplayThread(Thread):

  def __init__(self, volumio: VolumioThread, display: DisplayState):
    super().__init__(name='track-elapsed')
    self._volumio = volumio
    self._display = display

  def _produce_elapsed_time_text(self) -> str:
    elapsed = self._volumio.get_seek()
    duration = self._volumio.get_duration()
    elapsed_text = ' --.--'
    duration_text = ' --.--'
    if duration != 0 and elapsed <= duration:
      elapsed_text = format_min_sec(elapsed).rjust(6, ' ')
      duration_text = format_min_sec(duration).rjust(6, ' ')
    return f'{elapsed_text}  {duration_text}'

  def run(self) -> None:
    pass
