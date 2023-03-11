from threading import Thread, Event
from display_state import DisplayState
from volumio_thread import VolumioThread
import time

class TrackSelectorThread(Thread):

  def __init__(self, index: int, name: str, volumio: VolumioThread, display: DisplayState, stop_event: Event, select_after_sec: float=1.0):
    super().__init__()
    self._start = None
    self._select_after_sec = select_after_sec
    self._volumio = volumio
    self._display = display
    self._index = index
    self._name = name
    self._stop_event = stop_event
  
  def should_select(self):
    return time.time() - self._start >= self._select_after_sec

  def run(self):
    self._start = time.time()
    while not self._stop_event.is_set() and not self.should_select():
      time.sleep(0.25)
    if not self._stop_event.is_set():
      self._display.display_temporary_text(text=self._name, wave=True, duration=3.5)
      self._volumio.play_track(self._index)