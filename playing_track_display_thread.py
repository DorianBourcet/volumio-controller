from threading import Thread, Event
from display_state import DisplayState
from volumio_thread import VolumioThread
import time

class PlayingTrackDisplayThread(Thread):

  def __init__(self, volumio:VolumioThread, display:DisplayState, stop_event:Event):
    super().__init__()
    self._volumio = volumio
    self._display = display
    self._stop_event = stop_event

  def run(self):
    while not self._stop_event.is_set():
      if self._volumio.is_playing():
        should_break = self._volumio.get_current_service() != 'metaradio'
        self._display.set_persistent_texts(self._volumio.get_playing_track())
      else:
        self._display.display_persistent_texts(['...'])
      time.sleep(0.25)