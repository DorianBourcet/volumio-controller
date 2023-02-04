import board
import busio as io
import adafruit_ht16k33.segments
from threading import Event
from persistent_display_thread import PersistentDisplayThread
from temporary_display_thread import TemporaryDisplayThread
from threading import Event
from itertools import cycle

class DisplayState:

  def __init__(self):
    i2c = io.I2C(board.SCL, board.SDA)
    self.display = adafruit_ht16k33.segments.Seg14x4(i2c, address = [0x70,0x71,0x72])
    self._latest_stop_event = Event()
    self._latest_quiet_stop_event = Event()
    self.displaying_persistent = False
    self._persistent_texts = ['...']
    self._persistent_texts_iterable = cycle(self._persistent_texts)
    self.temporary_text_duration = None
    self.temporary_text = None
    self._overlay = None
    self.set_quiet_mode()
  
  def _print(self, display_thread):
    display_thread.daemon = True
    display_thread.start()

  def _issue_new_stop_event(self):
    self._latest_stop_event.set()
    self._latest_stop_event = Event()

  def _issue_new_quiet_stop_event(self):
    self._latest_quiet_stop_event.set()
    self._latest_quiet_stop_event = Event()

  def set_quiet_mode(self):
    self.display.brightness = 0.05
    self.marquee_sleep_delay = 0.20

  def set_active_mode(self):
    self.display.brightness = 0.5
    self.marquee_sleep_delay = 0.13

  def display_persistent_texts(self, texts: list = None):
    if texts is not None:
      self._issue_new_stop_event()
      self.set_persistent_texts(texts)
      return
    self.displaying_persistent = True
    self._print(PersistentDisplayThread(self,next(self._persistent_texts_iterable),self._latest_stop_event,self._latest_quiet_stop_event))

  def set_persistent_texts(self, texts: list):
    if texts != self._persistent_texts:
      self._persistent_texts = texts
      self._persistent_texts_iterable = cycle(texts)
      if self.displaying_persistent:
        self._issue_new_quiet_stop_event()

  def display_temporary_text(self, text: str, duration: float = None, marquee_trim_start: bool = False, wave: bool = False):
    self.displaying_persistent = False
    self.temporary_text = text
    if duration:
      self.temporary_text_duration = duration
    else:
      self.temporary_text_duration = None
    self._issue_new_stop_event()
    self._print(TemporaryDisplayThread(self,self.temporary_text,self._latest_stop_event, marquee_trim_start, wave))

