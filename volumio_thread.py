import math
import os
import time
from threading import RLock, Thread

import socketio

import logging_setup
import utils

logger = logging_setup.get_logger(__name__)

DEFAULT_VOLUMIO_URL = os.environ.get('VC_VOLUMIO_URL', 'http://localhost:3000')


class VolumioThread(Thread):

  LINEAR_BROADCAST_SERVICES: tuple[str, ...] = ('metaradio', 'webradio')

  CONNECT_BACKOFF_INITIAL_SEC = 1.0
  CONNECT_BACKOFF_FACTOR = 2.0
  CONNECT_BACKOFF_MAX_SEC = 30.0

  def __init__(self, base_url: str = DEFAULT_VOLUMIO_URL):
    super().__init__(name='volumio')
    self._base_url = base_url
    self._socketIO: socketio.Client | None = None
    self._lock = RLock()
    self._connected = False
    self._stopping = False
    self._volumio_volatile = False
    self._volumio_status = 'stop'
    self._volumio_volume = 0
    self._volumio_artist = ''
    self._volumio_title = ''
    self._volumio_queue_position = 0
    self._volumio_seek = 0
    self._volumio_queue: list[dict] = []
    self._volumio_service = ''
    self._volumio_track_type = ''
    self._volumio_duration = 0
    self._status_since = time.time()
    self._state_updated_on = time.time()
    self._selected_index = 0

  def _init_socketIO(self) -> None:
    self._socketIO = socketio.Client()
    self._socketIO.on('connect', self._on_connect)
    self._socketIO.on('disconnect', self._on_disconnect)
    self._socketIO.on('reconnect', self._on_reconnect)
    self._socketIO.on('pushState', self._on_state_response)
    self._socketIO.on('getState_response', self._on_state_response)
    self._socketIO.on('pushQueue', self._on_queue_response)
    self._socketIO.on('getQueue_response', self._on_queue_response)
    backoff = self.CONNECT_BACKOFF_INITIAL_SEC
    attempts = 0
    while not self._stopping:
      try:
        self._socketIO.connect(self._base_url)
        logger.info('connected to volumio at %s after %d attempt(s)', self._base_url, attempts + 1)
        return
      except Exception as ex:
        attempts += 1
        logger.warning(
          'volumio connect attempt %d failed (%s); retrying in %.1fs',
          attempts, ex, backoff,
        )
        time.sleep(backoff)
        backoff = min(backoff * self.CONNECT_BACKOFF_FACTOR, self.CONNECT_BACKOFF_MAX_SEC)

  def _on_connect(self) -> None:
    with self._lock:
      self._connected = True
    logger.info('socket.io connected')
    self._request_initial_state()

  def _on_disconnect(self) -> None:
    with self._lock:
      self._connected = False
    logger.warning('socket.io disconnected')

  def _on_reconnect(self) -> None:
    with self._lock:
      self._connected = True
    logger.info('socket.io reconnected')
    self._request_initial_state()

  def _request_initial_state(self) -> None:
    if self._socketIO is None:
      return
    try:
      self._socketIO.emit('getState')
      self._socketIO.emit('getQueue')
    except Exception:
      logger.exception('failed to request initial state')

  def _on_state_response(self, *args) -> None:
    if not args:
      return
    state = args[0]
    if not isinstance(state, dict):
      logger.warning('unexpected state payload: %r', type(state))
      return
    with self._lock:
      self._state_updated_on = time.time()
      volume = state.get('volume', 0) or 0
      self._volumio_volume = int(volume)
      status = state.get('status', 'stop')
      if self._volumio_status != status:
        self._volumio_status = status
        self._status_since = time.time()
      self._volumio_status = status
      raw_artist = (state.get('artist', '') or '').strip()
      self._volumio_artist = utils.truncate(raw_artist, 84)
      raw_title = (state.get('title', '') or '').strip()
      self._volumio_title = utils.truncate(raw_title, 84)
      self._volumio_service = (state.get('service', '') or '').strip()
      new_position = state.get('position', 0) or 0
      if self._volumio_queue_position != new_position:
        self._volumio_queue_position = new_position
        self._selected_index = new_position
      self._volumio_track_type = (state.get('trackType', '') or '').strip()
      self._volumio_seek = math.floor((state.get('seek', 0) or 0) / 1000)
      self._volumio_duration = state.get('duration', 0) or 0
      self._volumio_volatile = state.get('volatile', False)

  def _on_queue_response(self, *args) -> None:
    if not args:
      return
    queue = args[0]
    if not isinstance(queue, list):
      logger.warning('unexpected queue payload: %r', type(queue))
      return
    with self._lock:
      self._volumio_queue = queue

  def _safe_emit(self, event: str, *payload) -> bool:
    if self._socketIO is None or not self._connected:
      logger.debug('emit(%s) skipped — not connected', event)
      return False
    try:
      if payload:
        self._socketIO.emit(event, *payload)
      else:
        self._socketIO.emit(event)
      return True
    except Exception:
      logger.exception('emit(%s) failed', event)
      return False

  def is_connected(self) -> bool:
    with self._lock:
      return self._connected

  def queue_is_not_empty(self) -> bool:
    with self._lock:
      return len(self._volumio_queue) > 0

  def get_status(self) -> str:
    with self._lock:
      return self._volumio_status

  def has_status_stop(self) -> bool:
    return self.get_status() == 'stop'

  def is_playing(self) -> bool:
    return self.get_status() == 'play'

  def is_on_pause(self) -> bool:
    return self.get_status() == 'pause'

  def is_stopping(self) -> bool:
    with self._lock:
      if self._volumio_status != 'stop':
        return False
      return (time.time() - self._status_since) <= 5

  def is_interactive_broadcast(self) -> bool:
    with self._lock:
      return self._volumio_service not in self.LINEAR_BROADCAST_SERVICES

  def get_playing_track(self) -> list[str]:
    with self._lock:
      parts: list[str] = []
      if self._volumio_service == 'metaradio':
        parts.append(self._volumio_track_type)
      if self._volumio_track_type != self._volumio_title:
        parts.append(self._volumio_title)
      if self._volumio_track_type != self._volumio_artist:
        parts.append(self._volumio_artist)
      if self._volumio_track_type != self._volumio_title:
        parts.append(self._volumio_title)
      if self._volumio_track_type != self._volumio_artist:
        parts.append(self._volumio_artist)
      return [i for i in parts if i]

  def get_volume(self) -> int:
    with self._lock:
      return self._volumio_volume

  def volume_up(self, step: int = 1) -> None:
    with self._lock:
      target = max(0, min(100, self._volumio_volume + step))
      if target == self._volumio_volume:
        return
      self._volumio_volume = target
    self._safe_emit('volume', target)

  def volume_down(self, step: int = 1) -> None:
    with self._lock:
      target = max(0, min(100, self._volumio_volume - step))
      if target == self._volumio_volume:
        return
      self._volumio_volume = target
    self._safe_emit('volume', target)

  def get_current_queue_position(self) -> int:
    with self._lock:
      return self._volumio_queue_position

  def get_next_track(self) -> str | None:
    with self._lock:
      next_position = self._volumio_queue_position + 1
    return self.get_track(next_position)

  def get_previous_track(self) -> str | None:
    with self._lock:
      previous_position = self._volumio_queue_position - 1
    return self.get_track(previous_position)

  def next_track(self) -> None:
    with self._lock:
      if self._volumio_queue_position + 1 >= len(self._volumio_queue):
        return
      self._volumio_queue_position += 1
    self._safe_emit('next')

  def previous_track(self) -> None:
    """If we've played < 2s of the track, jump to the previous queue entry;
    otherwise restart the current track (single `prev` emit)."""
    if self.get_seek() >= 2:
      self._safe_emit('prev')
      return
    with self._lock:
      if self._volumio_queue_position <= 0:
        return
      self._volumio_queue_position -= 1
    self._safe_emit('prev')

  def get_track(self, index: int) -> str | None:
    with self._lock:
      if not self._volumio_queue:
        return None
      if index < 0 or index >= len(self._volumio_queue):
        return None
      track = self._volumio_queue[index]
    return track.get('title', track.get('name'))

  def can_browse_queue(self) -> bool:
    with self._lock:
      return self._volumio_service != 'spop' and len(self._volumio_queue) > 0

  def play_track(self, index: int) -> None:
    self._safe_emit('play', {'value': index})

  def get_seek(self) -> int:
    with self._lock:
      elapsed_since_last_update = math.floor(time.time() - self._state_updated_on)
      return self._volumio_seek + elapsed_since_last_update

  def get_duration(self) -> int:
    with self._lock:
      return self._volumio_duration

  def seek_up(self, seconds: int = 15) -> None:
    if not self.is_interactive_broadcast():
      return
    seek = self.get_seek()
    duration = self.get_duration()
    if duration - seek > seconds:
      self._safe_emit('seek', seek + seconds)

  def seek_down(self, seconds: int = 15) -> None:
    if not self.is_interactive_broadcast():
      return
    seek = self.get_seek()
    if seek > seconds:
      self._safe_emit('seek', seek - seconds)

  def selected_index_next(self) -> int:
    with self._lock:
      if not self._volumio_queue:
        return self._selected_index
      next_selected_index = self._selected_index + 1
      if next_selected_index >= len(self._volumio_queue):
        next_selected_index = 0
      self._selected_index = next_selected_index
      return self._selected_index

  def selected_index_previous(self) -> int:
    with self._lock:
      if not self._volumio_queue:
        return self._selected_index
      previous_selected_index = self._selected_index - 1
      if previous_selected_index < 0:
        previous_selected_index = len(self._volumio_queue) - 1
      self._selected_index = previous_selected_index
      return self._selected_index

  def resume(self) -> None:
    if self.is_playing():
      return
    with self._lock:
      volatile = self._volumio_volatile
    self._safe_emit('volatilePlay' if volatile else 'play')

  def hold_on(self) -> None:
    if self.is_interactive_broadcast():
      self.pause()
    else:
      self.stop()

  def stop(self) -> None:
    if self.get_status() != 'stop':
      self._safe_emit('stop')

  def pause(self) -> None:
    if self.get_status() == 'play':
      self._safe_emit('pause')

  def get_current_service(self) -> str:
    with self._lock:
      return self._volumio_service

  def shutdown(self) -> None:
    self._stopping = True
    if self._socketIO is None:
      return
    try:
      self._socketIO.disconnect()
    except Exception:
      logger.exception('error during socket.io disconnect')

  def run(self) -> None:
    try:
      self._init_socketIO()
      if self._stopping:
        return
      self._request_initial_state()
      self._socketIO.wait()
    except Exception:
      logger.exception('volumio thread crashed')
