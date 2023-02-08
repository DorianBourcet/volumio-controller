from threading import Thread, Event
from display_state import DisplayState
from volumio_thread import VolumioThread
from datetime import datetime
import pytz
import time
import math

class DatetimeDisplayThread(Thread):

  def __init__(self, display:DisplayState, stop_event:Event):
    super().__init__()
    self._display = display
    self._clock_tick = True
    self._latest_timestamp = None
    self._stop_event = stop_event
  
  def _display_datetime(self):
    now = math.ceil(time.time())
    if now != self._latest_timestamp:
      self._latest_timestamp = now
      self._clock_tick = not self._clock_tick
    separator = "." if self._clock_tick else ""
    now = datetime.now(pytz.timezone("America/Toronto"))
    day = now.strftime('%-d').rjust(2,' ')
    month = now.strftime('%-m').ljust(2,' ')
    hours = now.strftime('%-H').rjust(2,' ')
    minutes = now.strftime('%M')
    self._display.set_persistent_texts([' '+day+'.'+month+'  '+hours+separator+minutes+' '])

  def run(self):
    while not self._stop_event.is_set():
      self._display_datetime()
      time.sleep(0.25)