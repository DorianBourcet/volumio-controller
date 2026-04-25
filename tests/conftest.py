"""Pytest config: mock hardware-dependent modules so tests can run on dev machines.

Volumio's controller imports `board`, `busio`, `adafruit_ht16k33` and
`adafruit_seesaw` at module load time. These probe Pi hardware on import and
fail outside the target. We inject lightweight fakes before any project module
loads so unit tests can run on macOS/Linux dev boxes."""
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
sys.modules['adafruit_seesaw.seesaw'].Seesaw = MagicMock()
sys.modules['adafruit_seesaw.rotaryio'].IncrementalEncoder = MagicMock()
sys.modules['adafruit_seesaw.digitalio'].DigitalIO = MagicMock()
