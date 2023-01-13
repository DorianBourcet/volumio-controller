import board
import busio as io
import adafruit_ht16k33.segments
from threading import Event
from persistent_display_thread import PersistentDisplayThread
from temporary_display_thread import TemporaryDisplayThread
from threading import Event

class DisplayState:

  def __init__(self):
    i2c = io.I2C(board.SCL, board.SDA)
    self.display = adafruit_ht16k33.segments.Seg14x4(i2c, address = [0x70,0x71,0x72])
    self.display.brightness = 0.5
    self.marquee_sleep_delay = 0.13
    self._latest_stop_event = Event()
    self.displaying_persistent = False
    self.persistent_texts = ['...']
    self.temporary_text_duration = None
    self.temporary_texts = []
    self._overlay = None
  
  def _print(self, display_thread):
    display_thread.daemon = True
    display_thread.start()

  def _issue_new_stop_event(self):
    self._latest_stop_event.set()
    self._latest_stop_event = Event()

  def set_quiet_mode(self):
    self.display.brightness = 0.05
    self.marquee_sleep_delay = 0.20

  def set_active_mode(self):
    self.display.brightness = 0.5
    self.marquee_sleep_delay = 0.13

  def display_persistent_texts(self):
    self.displaying_persistent = True
    self._print(PersistentDisplayThread(self,self._latest_stop_event))

  def set_persistent_texts(self, texts: list):
    if texts != self.persistent_texts:
      self.persistent_texts = texts
      if self.displaying_persistent:
        self._issue_new_stop_event()
        self.display_persistent_texts()

  def display_temporary_texts(self, texts: list, duration: float = None, marquee_trim_start: bool = False):
    self.displaying_persistent = False
    self.temporary_texts = texts
    if duration:
      self.temporary_text_duration = duration
    else:
      self.temporary_text_duration = None
    self._issue_new_stop_event()
    self._print(TemporaryDisplayThread(self,self._latest_stop_event, marquee_trim_start))

