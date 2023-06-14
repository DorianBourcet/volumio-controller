from socketIO_client import SocketIO
from threading import Thread
import json
import time
import math

class VolumioThread(Thread):

  linear_broadcast_service = [
    'metaradio',
    'webradio',
  ]

  def __init__(self):
    super().__init__()
    self._socketIO = None
    self._connected = False
    self._volumio_volatile = False
    self._volumio_status = 'stop'
    self._volumio_volume = 0
    self._volumio_artist = ''
    self._volumio_title = ''
    self._volumio_queue_position = 0
    self._volumio_seek = 0
    self._volumio_queue = []
    self._volumio_service = ''
    self._volumio_track_type = ''
    self._volumio_duration = 0
    self._status_since = time.time()
    self._state_updated_on = time.time()
    self._selected_index = 0
  
  def _init_socketIO(self):
    self._socketIO = SocketIO('localhost', 3000)
    self._socketIO.on('connect', self._on_connect)
    self._socketIO.on('disconnect', self._on_disconnect)
    self._socketIO.on('reconnect', self._on_reconnect)
    self._socketIO.on('pushState', self._on_state_response)
    self._socketIO.on('getState_response', self._on_state_response)
    self._socketIO.on('pushQueue', self._on_queue_response)
    self._socketIO.on('getQueue_response', self._on_queue_response)

  def _on_connect(self):
    self._connected = True

  def _on_disconnect(self):
    self._connected = False

  def _on_reconnect(self):
    self._connected = True

  def _on_state_response(self, *args):
    state = args[0]
    self._state_updated_on = time.time()
    #self._estimate_volumio_seek(state,self._volumio_title, self._volumio_artist)
    volume = state.get('volume', 0) or 0
    self._volumio_volume = int(volume)
    status = state.get('status','stop')
    if self._volumio_status != status:
      self._volumio_status = status
      self._status_since = time.time()
    self._volumio_status = status
    self._volumio_artist = (state.get('artist', '') or '').strip()
    self._volumio_title = (state.get('title', '') or '').strip()
    self._volumio_service = (state.get('service', '') or '').strip()
    if self._volumio_queue_position != state.get('position', 0):
      self._volumio_queue_position = state.get('position', 0)
      self._selected_index = state.get('position', 0)
    self._volumio_track_type = (state.get('trackType', '') or '').strip()
    self._volumio_seek = math.floor((state.get('seek', 0) or 0)/1000)
    self._volumio_duration = state.get('duration', 0)
    self._volumio_volatile = state.get('volatile', False)
  
  def _estimate_volumio_seek(self, new_state, prev_title, prev_artist):
    if new_state.get('service') == 'spop':
      new_status = new_state.get('status')
      raw_seek = new_state.get('seek', 0)
      if new_status == 'play':
        if prev_artist != new_state.get('artist') or prev_title != new_state.get('title'):
          self._volumio_spotify_seek = math.ceil(raw_seek/1000)
          self._volumio_spotify_seek_time = time.time()
        elif raw_seek > 0:
          self._volumio_spotify_seek = math.ceil(raw_seek/1000)
          self._volumio_spotify_seek_time = time.time()
      elif new_status == 'pause' and raw_seek > 0:
        self._volumio_spotify_seek = math.ceil(raw_seek/1000)
      elif new_status == 'stop':
        self._volumio_spotify_seek = None
        self._volumio_spotify_seek_time = None
    else:
      self._volumio_spotify_seek = None
      self._volumio_spotify_seek_time = None
      self._volumio_seek = math.floor(new_state.get('seek', 0)/1000)
        

  def _on_queue_response(self, *args):
    self._volumio_queue = args[0]

  def is_connected(self):
    return self._connected

  def queue_is_not_empty(self):
    return len(self._volumio_queue) > 0

  def get_status(self):
    return self._volumio_status
  
  def has_status_stop(self):
    return self._volumio_status == 'stop'

  def is_playing(self):
    return self._volumio_status == 'play'

  def is_on_pause(self):
    return self._volumio_status == 'pause'

  def is_stopping(self):
    if self._volumio_status != 'stop':
      return False
    now = time.time()
    return (now - self._status_since) <= 5

  def is_interactive_broadcast(self) -> bool:
    return self._volumio_service not in self.linear_broadcast_service

  def get_playing_track(self):
    parts = []
    if self._volumio_service == 'metaradio':
      parts.append(self._volumio_track_type)
    parts.extend([self._volumio_title,self._volumio_artist])
    return [i for i in parts if i]

  def get_volume(self):
    return self._volumio_volume

  def volume_up(self, step: int = 1):
    if self._volumio_volume <= 99:
      volume = self._volumio_volume + step
      self._volumio_volume = volume
      self._socketIO.emit('volume', volume)

  def volume_down(self, step: int = 1):
    if self._volumio_volume >= 1:
      volume = self._volumio_volume - step
      self._volumio_volume = volume
      self._socketIO.emit('volume', volume)

  def get_current_queue_position(self) -> int:
    return self._volumio_queue_position

  def get_next_track(self) -> str:
    current_position = self._volumio_queue_position
    next_position = current_position + 1
    return self.get_track(next_position)

  def get_previous_track(self) -> str:
    current_position = self._volumio_queue_position
    previous_position = current_position - 1
    return self.get_track(previous_position)
  
  def next_track(self):
    self._volumio_queue_position += 1
    self._socketIO.emit('next')
  
  def previous_track(self):
    if self.get_seek() >= 2:
      self._volumio_queue_position -= 1
      self._socketIO.emit('prev')
    self._volumio_queue_position -= 1
    self._socketIO.emit('prev')
  
  def get_track(self, index: int):
    track = self._volumio_queue[index]
    return track.get('title', track.get('name'))
  
  def can_browse_queue(self) -> bool:
    return self._volumio_service != 'spop' and self.queue_is_not_empty()
  
  def play_track(self, index: int):
    self._socketIO.emit('play',{'value': index})

  def get_seek(self):
    """if self._volumio_status == 'stop':
      return 0
    if self._volumio_service == 'spop':
      if self._volumio_status == 'pause':
        return int(self._volumio_spotify_seek)
      else:
        elapsed = time.time() - self._volumio_spotify_seek_time
        return int(elapsed + self._volumio_spotify_seek)"""
    elapsed_since_last_update = math.floor(time.time() - self._state_updated_on)
    total_elapsed = self._volumio_seek + elapsed_since_last_update
    return total_elapsed
  
  def get_duration(self):
    return self._volumio_duration

  def seek_up(self, seconds: int = 15):
    if not self.is_interactive_broadcast():
      return
    seek = self.get_seek()
    if self._volumio_duration - seek > seconds:
      self._socketIO.emit('seek',seek+seconds)
  
  def seek_down(self, seconds: int = 15):
    if not self.is_interactive_broadcast():
      return
    seek = self.get_seek()
    if seek > seconds:
      self._socketIO.emit('seek',seek-seconds)

  def selected_index_next(self):
    next_selected_index = self._selected_index + 1
    if next_selected_index >= len(self._volumio_queue):
      next_selected_index = 0
    self._selected_index = next_selected_index
    return self._selected_index
  
  def selected_index_previous(self):
    previous_selected_index = self._selected_index - 1
    if previous_selected_index < 0:
      previous_selected_index = len(self._volumio_queue) - 1
    self._selected_index = previous_selected_index
    return self._selected_index

  def resume(self):
    if not self.is_playing():
      if self._volumio_volatile:
        self._socketIO.emit('volatilePlay')
      else:
        self._socketIO.emit('play')
  
  def hold_on(self):
    if self.is_interactive_broadcast():
      self.pause()
    else:
      self.stop()

  def stop(self):
    if self._volumio_status != 'stop':
      self._socketIO.emit('stop')
  
  def pause(self):
    if self._volumio_status == 'play':
      self._socketIO.emit('pause')

  def get_current_service(self):
    return self._volumio_service

  def run(self):
    self._init_socketIO()
    self._socketIO.emit('getState')
    self._socketIO.emit('getQueue')
    self._socketIO.wait()