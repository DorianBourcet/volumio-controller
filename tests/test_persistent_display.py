"""Tests for the single persistent render loop: one long-lived loop reused
across content changes (no thread-per-frame), resuming after a temporary display."""
import threading
import time
from threading import Event

from display_state import DisplayState
from persistent_display_thread import PersistentDisplayThread


class _FakeDisplay:
  """Minimal DisplayState stand-in that feeds the render loop a fixed spec and
  records every frame written, so marquee behaviour can be asserted directly."""

  def __init__(self, texts: list[str], continuous: bool = False, duration: float = 0.0):
    self._spec = (texts, continuous, duration)
    self.marquee_sleep_delay = 0.0
    self.currently_selected_text = None
    self.frames: list[str] = []

  def persistent_gen(self) -> int:
    return 0

  def persistent_render_spec(self):
    texts, continuous, duration = self._spec
    return (list(texts), continuous, duration, 0)

  def print(self, text: str, bypass_sleep_mode: bool = False) -> None:
    self.frames.append(text)


def _live_persistent_loops() -> list[threading.Thread]:
  return [
    t for t in threading.enumerate()
    if t.name == 'PersistentDisplayThread' and t.is_alive()
  ]


def test_loop_renders_and_is_reused_across_content_changes():
  display = DisplayState()
  try:
    display.display_persistent_texts(
      texts=['AAA'], continuous_marquee=False, stop_daemons=False,
    )
    time.sleep(0.1)
    loop = display._persistent_loop
    assert loop is not None and loop.is_running()

    # Feed many content updates the way a feeder daemon (clock, playing track)
    # does. The loop must pick them up WITHOUT ever being respawned.
    for i in range(20):
      display.set_persistent_texts(texts=[f'T{i:02d}'], continuous_marquee=False)
      time.sleep(0.02)

    assert display._persistent_loop is loop, 'loop was respawned (churn)'
    assert len(_live_persistent_loops()) == 1
    assert display._display.print.call_count > 0, 'nothing was rendered'
  finally:
    display.shutdown()
    loop = display._persistent_loop
    if loop is not None:
      loop.join(timeout=2)
  assert _live_persistent_loops() == []


def test_continuous_marquee_renders_without_respawn():
  display = DisplayState()
  try:
    display.display_persistent_texts(
      texts=['UNE OPTION DE MENU TRES LONGUE'],
      continuous_marquee=True,
      stop_daemons=False,
    )
    time.sleep(0.2)
    loop = display._persistent_loop
    assert loop is not None and loop.is_running()
    calls = display._display.print.call_count
    time.sleep(0.3)
    assert display._display.print.call_count > calls, 'marquee did not advance'
    assert display._persistent_loop is loop
  finally:
    display.shutdown()
    loop = display._persistent_loop
    if loop is not None:
      loop.join(timeout=2)


def test_marquee_trim_start_is_a_one_shot():
  # A loop born with trim_start=True must honour it on the first frame only;
  # every subsequent marquee pass must scroll in from the right again.
  fake = _FakeDisplay(texts=['A' * 14])
  loop = PersistentDisplayThread(fake, Event(), marquee_trim_start=True)
  loop.start()
  try:
    time.sleep(0.1)
  finally:
    loop._stop_event.set()
    loop.join(timeout=2)

  assert fake.frames, 'nothing rendered'
  # First frame skips the scroll-in (text starts flush left).
  assert fake.frames[0] == 'A' * 12
  # A later pass scrolls the text in from the right (11 spaces then one 'A'),
  # which only happens once trim_start has been reset to False.
  assert (' ' * 11 + 'A') in fake.frames, 'trim_start was not reset (still applied every pass)'
  assert loop._marquee_trim_start is False


def test_temporary_display_stops_then_resumes_persistent_loop():
  display = DisplayState()
  try:
    display.display_persistent_texts(
      texts=['HOME'], continuous_marquee=False, stop_daemons=False,
    )
    time.sleep(0.1)
    first = display._persistent_loop
    assert first.is_running()

    # A temporary display takes over: it must stop the persistent loop...
    display.display_temporary_text('TMP', duration=0.1)
    time.sleep(0.05)
    assert not first.is_running(), 'persistent loop should yield to temporary'

    # ...and once it ends, a fresh persistent loop must resume automatically.
    time.sleep(0.5)
    resumed = display._persistent_loop
    assert resumed is not None and resumed.is_running()
    assert resumed is not first
    assert len(_live_persistent_loops()) == 1
  finally:
    display.shutdown()
    loop = display._persistent_loop
    if loop is not None:
      loop.join(timeout=2)
