from threading import Thread, Event
from display_state import DisplayState
from volumio_thread import VolumioThread
from datetime import datetime
import pytz
import time

class BasicStateThread(Thread):

  def __init__(self, volumio:VolumioThread, display:DisplayState):
    super().__init__()
    self._volumio = volumio
    self._display = display
    self._clock_tick = True
    self._latest_volumio_status = self._volumio.get_status()

  def _display_datetime(self):
    self._clock_tick = not self._clock_tick
    separator = "." if self._clock_tick else ""
    now = datetime.now(pytz.timezone("America/Toronto"))
    day = now.strftime('%-d').rjust(2,' ')
    month = now.strftime('%-m').ljust(2,' ')
    hours = now.strftime('%-H').rjust(2,' ')
    minutes = now.strftime('%M')
    self._display.set_persistent_texts([' '+day+'.'+month+'  '+hours+separator+minutes+' '])

  def run(self):
    while True:
      time.sleep(1)
      if self._volumio.is_stopping():
        self._display.set_persistent_texts(['...'])
        continue
      if self._volumio.is_playing():
        self._display.set_persistent_texts(self._volumio.get_playing_track())
      else:
        self._display_datetime()

