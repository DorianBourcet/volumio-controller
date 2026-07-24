"""Stub Pi-only modules (`board`, `busio`, `adafruit_ht16k33`, `adafruit_seesaw`)
before any project module imports them, so tests run on dev machines."""
import os
import sys
import types
from unittest.mock import MagicMock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
  sys.path.insert(0, ROOT)


def _stub_module(name: str) -> types.ModuleType:
  module = types.ModuleType(name)
  sys.modules[name] = module
  return module


for name in (
  'board',
  'busio',
  'adafruit_ht16k33',
  'adafruit_ht16k33.segments',
  'adafruit_seesaw',
  'adafruit_seesaw.seesaw',
  'adafruit_seesaw.rotaryio',
  'adafruit_seesaw.digitalio',
):
  if name not in sys.modules:
    _stub_module(name)

sys.modules['board'].SCL = object()
sys.modules['board'].SDA = object()
sys.modules['board'].I2C = MagicMock(return_value=MagicMock())
sys.modules['busio'].I2C = MagicMock(return_value=MagicMock())
sys.modules['adafruit_ht16k33.segments'].Seg14x4 = MagicMock(return_value=MagicMock())
# Link the submodule as an attribute so `adafruit_ht16k33.segments.Seg14x4`
# attribute access resolves (DisplayState reaches it that way).
sys.modules['adafruit_ht16k33'].segments = sys.modules['adafruit_ht16k33.segments']
sys.modules['adafruit_seesaw.seesaw'].Seesaw = MagicMock()
sys.modules['adafruit_seesaw.rotaryio'].IncrementalEncoder = MagicMock()
sys.modules['adafruit_seesaw.digitalio'].DigitalIO = MagicMock()
