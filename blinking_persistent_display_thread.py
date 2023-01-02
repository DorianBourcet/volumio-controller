from display_thread import DisplayThread
from threading import Event
import time

class BlinkingPersistentDisplayThread(DisplayThread):

  def __init__(self, display_state, stop_event: Event):
    super().__init__(display_state,stop_event)
    text = display_state.persistent_texts[0]
    length = DisplayThread._get_length(text)
    if length > 12:
      raise Exception('Length should not exceed 12 for blinking text')
    self._persistent_text = text
    self._text_length = length
    self._blink_delay = display_state.blink_delay
  
  def run(self):
    last_blink = time.time()
    must_display_text = True
    print(str(self._blink_delay))
    while not self._stop_event.is_set():
      now = time.time()
      print('now: '+str(now))
      if now - last_blink >= self._blink_delay:
        print('due for blink')
        last_blink = now
        must_display_text = not must_display_text
      if must_display_text:
        self._pretty_print(self._persistent_text,self._text_length)
      else:
        self._pretty_print('',0)
      time.sleep(0.1)
