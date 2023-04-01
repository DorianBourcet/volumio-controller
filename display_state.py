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
    self._stop_event = Event()
    self._persistent_display_daemon_stop_event = Event()
    self._temporary_display_daemon_stop_event = Event()
    self.displaying_persistent = False
    self._persistent_texts = ['...']
    self._persistent_texts_iterable = cycle(self._persistent_texts)
    self.temporary_text_duration = 2.0
    self.temporary_text = None
    self._overlay = None
    self.set_quiet_mode()

  def _issue_stop_event(self) -> Event:
    self._stop_event.set()
    self._stop_event = Event()
    return self._stop_event
  
  def issue_persistent_display_daemon_stop_event(self) -> Event:
    self._persistent_display_daemon_stop_event.set()
    self._persistent_display_daemon_stop_event = Event()
    return self._persistent_display_daemon_stop_event
  
  def issue_temporary_display_daemon_stop_event(self) -> Event:
    self._temporary_display_daemon_stop_event.set()
    self._temporary_display_daemon_stop_event = Event()
    return self._temporary_display_daemon_stop_event

  def set_quiet_mode(self):
    self.display.brightness = 0.05
    self.marquee_sleep_delay = 0.20

  def set_active_mode(self):
    self.display.brightness = 0.5
    self.marquee_sleep_delay = 0.13

  def display_persistent_texts(self, texts: list=None, stop_daemons: bool = True):
    if stop_daemons:
      self.issue_persistent_display_daemon_stop_event()
      self.issue_temporary_display_daemon_stop_event()
    self.displaying_persistent = True
    if texts is not None:
      self.set_persistent_texts(texts)
    else:
      printer = PersistentDisplayThread(self,next(self._persistent_texts_iterable),self._issue_stop_event())
      printer.start()

  def set_persistent_texts(self, texts: list):
    if texts != self._persistent_texts:
      self._persistent_texts = texts
      self._persistent_texts_iterable = cycle(texts)
      if self.displaying_persistent:
        self._issue_stop_event()
        self.display_persistent_texts(stop_daemons=False)

  def display_temporary_text(
    self,
    text: str,
    duration: float = 2.0,
    marquee_trim_start: bool = False,
    wave: bool = False,
    stop_daemons: bool = True
  ):
    if stop_daemons:
      self.issue_temporary_display_daemon_stop_event()
    self.displaying_persistent = False
    self.temporary_text = text
    self.temporary_text_duration = duration
    printer = TemporaryDisplayThread(self, self.temporary_text, self._issue_stop_event(), marquee_trim_start, wave)
    printer.start()

