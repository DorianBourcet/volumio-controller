from threading import Thread, Event
from display_state import DisplayState
from volumio_thread import VolumioThread
import time

class PlayingTrackDisplayThread(Thread):

  def __init__(self, volumio:VolumioThread, display:DisplayState):
    super().__init__()
    self._volumio = volumio
    self._display = display
    self.daemon = True

  def run(self):
    stop_event = self._display.issue_persistent_display_daemon_stop_event()
    while not stop_event.is_set():
      if self._volumio.is_playing():
        self._display.set_persistent_texts(texts=self._volumio.get_playing_track(),continuous_marquee=False)
      else:
        self._display.set_persistent_texts(texts=['...'],continuous_marquee=False)
      time.sleep(0.25)