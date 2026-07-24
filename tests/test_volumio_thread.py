"""Unit tests for VolumioThread state-management, without a live Socket.IO."""
from unittest.mock import MagicMock

import volumio_thread


def make_thread():
  vt = volumio_thread.VolumioThread()
  vt._socketIO = MagicMock()
  vt._connected = True
  return vt


def push_state(vt, **overrides):
  payload = {
    'volume': 50,
    'status': 'play',
    'artist': 'Artist',
    'title': 'Title',
    'service': 'mpd',
    'position': 0,
    'trackType': 'mp3',
    'seek': 0,
    'duration': 200,
    'volatile': False,
  }
  payload.update(overrides)
  vt._on_state_response(payload)


def push_queue(vt, queue):
  vt._on_queue_response(queue)


class TestStateUpdates:
  def test_volume_extracted(self):
    vt = make_thread()
    push_state(vt, volume=42)
    assert vt.get_volume() == 42

  def test_invalid_payload_ignored(self):
    vt = make_thread()
    vt._on_state_response('not a dict')
    # Default state retained
    assert vt.get_status() == 'stop'

  def test_no_args_payload_ignored(self):
    vt = make_thread()
    vt._on_state_response()
    assert vt.get_status() == 'stop'


class TestVolumeBounds:
  """volume_up/down must be bounded to [0, 100]."""

  def test_volume_up_caps_at_100(self):
    vt = make_thread()
    push_state(vt, volume=98)
    vt.volume_up(step=5)
    assert vt.get_volume() == 100

  def test_volume_down_floors_at_0(self):
    vt = make_thread()
    push_state(vt, volume=2)
    vt.volume_down(step=5)
    assert vt.get_volume() == 0

  def test_volume_up_no_emit_when_already_max(self):
    vt = make_thread()
    push_state(vt, volume=100)
    vt._socketIO.emit.reset_mock()
    vt.volume_up()
    vt._socketIO.emit.assert_not_called()


class TestPreviousTrackBugFix:
  """previous_track must emit `prev` once, not twice."""

  def test_emits_once_when_seek_below_threshold(self):
    vt = make_thread()
    push_queue(vt, [{'title': 'a'}, {'title': 'b'}, {'title': 'c'}])
    push_state(vt, position=2, seek=0)
    vt._socketIO.emit.reset_mock()
    vt.previous_track()
    emit_calls = [c for c in vt._socketIO.emit.call_args_list if c.args[0] == 'prev']
    assert len(emit_calls) == 1

  def test_emits_once_when_seek_above_threshold(self):
    vt = make_thread()
    push_queue(vt, [{'title': 'a'}, {'title': 'b'}])
    push_state(vt, position=1, seek=10000)  # 10s
    vt._socketIO.emit.reset_mock()
    vt.previous_track()
    emit_calls = [c for c in vt._socketIO.emit.call_args_list if c.args[0] == 'prev']
    assert len(emit_calls) == 1

  def test_does_not_decrement_below_zero(self):
    vt = make_thread()
    push_queue(vt, [{'title': 'a'}])
    push_state(vt, position=0, seek=0)
    vt.previous_track()
    assert vt.get_current_queue_position() == 0


class TestGetTrackBoundsBugFix:
  """get_track must not silently return the wrong element on bad indices."""

  def test_negative_index_returns_none(self):
    vt = make_thread()
    push_queue(vt, [{'title': 'a'}, {'title': 'b'}])
    assert vt.get_track(-1) is None

  def test_out_of_bounds_returns_none(self):
    vt = make_thread()
    push_queue(vt, [{'title': 'a'}, {'title': 'b'}])
    assert vt.get_track(5) is None

  def test_empty_queue_returns_none(self):
    vt = make_thread()
    assert vt.get_track(0) is None

  def test_valid_index_returns_title(self):
    vt = make_thread()
    push_queue(vt, [{'title': 'a'}, {'title': 'b'}])
    assert vt.get_track(1) == 'b'

  def test_falls_back_to_name_when_no_title(self):
    vt = make_thread()
    push_queue(vt, [{'name': 'fallback'}])
    assert vt.get_track(0) == 'fallback'


class TestNextTrack:
  def test_does_not_advance_past_queue_end(self):
    vt = make_thread()
    push_queue(vt, [{'title': 'a'}, {'title': 'b'}])
    push_state(vt, position=1)
    vt._socketIO.emit.reset_mock()
    vt.next_track()
    assert vt.get_current_queue_position() == 1
    vt._socketIO.emit.assert_not_called()


class TestEmitWhenDisconnected:
  def test_emit_skipped_when_disconnected(self):
    vt = make_thread()
    vt._connected = False
    vt._socketIO.emit.reset_mock()
    vt.stop()
    vt._socketIO.emit.assert_not_called()


class TestReadiness:
  """Volumio is 'ready' only once the first real state payload has arrived, so
  home never flashes the stale default 'stop'."""

  def test_not_ready_before_any_state(self):
    vt = volumio_thread.VolumioThread()
    assert vt.is_ready() is False

  def test_ready_after_first_state(self):
    vt = make_thread()
    push_state(vt)
    assert vt.is_ready() is True

  def test_ready_cleared_on_disconnect(self):
    vt = make_thread()
    push_state(vt)
    assert vt.is_ready() is True
    vt._on_disconnect()
    assert vt.is_ready() is False


class TestSelectedIndexNavigation:
  def test_next_wraps(self):
    vt = make_thread()
    push_queue(vt, [{'title': 'a'}, {'title': 'b'}])
    vt._selected_index = 1
    assert vt.selected_index_next() == 0

  def test_previous_wraps(self):
    vt = make_thread()
    push_queue(vt, [{'title': 'a'}, {'title': 'b'}])
    vt._selected_index = 0
    assert vt.selected_index_previous() == 1

  def test_empty_queue_returns_current(self):
    vt = make_thread()
    vt._selected_index = 0
    assert vt.selected_index_next() == 0
    assert vt.selected_index_previous() == 0
