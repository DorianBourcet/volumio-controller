import board
from adafruit_seesaw import seesaw, rotaryio, digitalio

class UserInput:

  def __init__(self, addr):
    qt_enc = seesaw.Seesaw(board.I2C(), addr=addr)
    qt_enc.pin_mode(24, qt_enc.INPUT_PULLUP)
    self._button = digitalio.DigitalIO(qt_enc, 24)
    self._button_held = False
    self._encoder = rotaryio.IncrementalEncoder(qt_enc)
    self._last_position = -self._encoder.position

  def pressed(self):
    if not self._button.value and not self._button_held:
      self._button_held = True
      return True
    return False

  def released(self):
    if self._button.value and self._button_held:
      self._button_held = False
      return True
    return False

  def turned_right(self):
    position = -self._encoder.position
    if position > 210000000:
      return False
    if position != self._last_position:
      if position > self._last_position:
        self._last_position = position
        return True
    return False

  def turned_left(self):
    position = -self._encoder.position
    if position > 210000000:
      return False
    if position != self._last_position:
      if position < self._last_position:
        self._last_position = position
        return True
    return False
