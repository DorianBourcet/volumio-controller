import board
import busio as io
import adafruit_ht16k33.segments
from threading import Event
from continuous_marquee_display_thread import ContinuousMarqueeDisplayThread
from persistent_display_thread import PersistentDisplayThread
from temporary_display_thread import TemporaryDisplayThread
from threading import Event
from itertools import cycle

class DisplayState:
  EMPTY_TEXT = '            '

  def __init__(self):
    i2c = io.I2C(board.SCL, board.SDA)
    self._display = adafruit_ht16k33.segments.Seg14x4(i2c, address = [0x70,0x71,0x72])
    self._stop_event = Event()
    self._persistent_display_daemon_stop_event = Event()
    self._temporary_display_daemon_stop_event = Event()
    self.displaying_persistent = False
    self._persistent_texts = ['.  ','.. ','...',' ..','  .','']
    self._persistent_texts_iterable = cycle(self._persistent_texts)
    self._persistent_texts_continuous_marquee = False
    self._persistent_text_duration = 5.0
    self._sleep_mode = False
    self._latest_text = self.EMPTY_TEXT
    self.temporary_text_duration = 2.0
    self.temporary_text = None
    self.currently_selected_text = None
    self.set_quiet_mode()

  def _issue_stop_event(self) -> Event:
    self._stop_event.set()
    self._stop_event = Event()
    return self._stop_event

  def print(self, text: str = None, bypass_sleep_mode: bool = False):
    if text is not None:
      self._latest_text = text
    else:
      text = self.EMPTY_TEXT
    if not self._sleep_mode or bypass_sleep_mode:
      self._display.print(text)
    else:
      self._display.print(self.EMPTY_TEXT)
  
  def issue_persistent_display_daemon_stop_event(self) -> Event:
    self._persistent_display_daemon_stop_event.set()
    self._persistent_display_daemon_stop_event = Event()
    return self._persistent_display_daemon_stop_event
  
  def issue_temporary_display_daemon_stop_event(self) -> Event:
    self._temporary_display_daemon_stop_event.set()
    self._temporary_display_daemon_stop_event = Event()
    return self._temporary_display_daemon_stop_event

  def set_quiet_mode(self):
    self._display.brightness = 0.15
    self.marquee_sleep_delay = 0.20

  def set_active_mode(self):
    self._display.brightness = 0.5
    self.marquee_sleep_delay = 0.15
  
  def enable_sleep_mode(self):
    if not self._sleep_mode:
      self._sleep_mode = True
      self.print()

  def disable_sleep_mode(self):
    if self._sleep_mode:
      self._sleep_mode = False
      self.print(self._latest_text)

  def display_persistent_texts(self, texts: list=None, duration: float = None, continuous_marquee: bool = None, marquee_trim_start: bool = False, stop_daemons: bool = True):
    if continuous_marquee is not None:
      self._persistent_texts_continuous_marquee = continuous_marquee
    if duration is not None:
      self._persistent_text_duration = duration
    if stop_daemons:
      self.issue_persistent_display_daemon_stop_event()
      self.issue_temporary_display_daemon_stop_event()
    self.displaying_persistent = True
    if texts is not None:
      self.set_persistent_texts(texts)
    elif self._persistent_texts_continuous_marquee:
      printer = ContinuousMarqueeDisplayThread(self,' '.join(self._persistent_texts),self._issue_stop_event())
      printer.start()
    else:
      printer = PersistentDisplayThread(self,next(self._persistent_texts_iterable),self._issue_stop_event(),self._persistent_text_duration, marquee_trim_start)
      printer.start()

  def set_persistent_texts(self, texts: list, duration: float = None, continuous_marquee: bool = None):
    if continuous_marquee is not None:
      self._persistent_texts_continuous_marquee = continuous_marquee
    if duration is not None:
      self._persistent_text_duration = duration
    if texts != self._persistent_texts:
      self._persistent_texts = texts
      self._persistent_texts_iterable = cycle(texts)
      if self.displaying_persistent:
        if texts[0] == self.currently_selected_text:
          next(self._persistent_texts_iterable)
        else:
          self._issue_stop_event()
          self.display_persistent_texts(stop_daemons=False)

  def display_temporary_text(
    self,
    text: str,
    duration: float = 2.0,
    marquee_trim_start: bool = False,
    wave: bool = False,
    align_left: bool = False,
    trim_next_persistent_marquee: bool = False,
    stop_daemons: bool = True
  ):
    if stop_daemons:
      self.issue_temporary_display_daemon_stop_event()
    self.displaying_persistent = False
    self.temporary_text = text
    self.temporary_text_duration = duration
    printer = TemporaryDisplayThread(self, self.temporary_text, self._issue_stop_event(), marquee_trim_start, align_left, wave, trim_next_persistent_marquee)
    printer.start()
  
  def clear_temporary_display(self):
    self.issue_temporary_display_daemon_stop_event()
    self._issue_stop_event()
  
  def clear_persistent_display(self):
    self.issue_persistent_display_daemon_stop_event()
    self.set_persistent_texts(texts=[''])

