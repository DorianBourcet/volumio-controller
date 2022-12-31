from socketIO_client import SocketIO
from threading import Thread
import json
import time
import math

class VolumioThread(Thread):

  unpausable_services = [
    'metaradio',
    'webradio',
  ]

  def __init__(self):
    super().__init__()
    self._socketIO = SocketIO('localhost', 3000)
    self._socketIO.on('pushState', self._on_state_response)
    self._socketIO.on('getState_response', self._on_state_response)
    self._socketIO.on('pushQueue', self._on_queue_response)
    self._socketIO.on('getQueue_response', self._on_queue_response)

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

  def _on_state_response(self, *args):
    state = args[0]
    self._estimate_volumio_seek(state,self._volumio_title, self._volumio_artist)
    volume = state.get('volume', 0)
    if volume == '':
      volume = 0
    self._volumio_volume = int(volume)
    status = state.get('status','stop')
    if self._volumio_status != status:
      self._volumio_status = status
      self._status_since = time.time()
    self._volumio_status = status
    self._volumio_artist = state.get('artist', '')
    self._volumio_title = state.get('title', '')
    self._volumio_service = state.get('service', '')
    self._volumio_queue_position = state.get('position', 0)
    self._volumio_track_type = state.get('trackType', '')
    self._volumio_duration = state.get('duration', 0)
  
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
      self._volumio_seek = math.ceil(new_state.get('seek', 0)/1000)
        

  def _on_queue_response(self, *args):
    self._volumio_queue = args[0]

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

  def can_pause(self):
    return self._volumio_service not in self.unpausable_services

  def get_playing_track(self):
    parts = []
    if self._volumio_service == 'metaradio':
      parts.append(self._volumio_track_type)
    title = self._volumio_title
    artist = self._volumio_artist
    parts.extend([title, artist])
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

  def get_next_track(self) -> str:
    try:
      current_position = self._volumio_queue_position
      next_position = current_position + 1
      next_track = self._volumio_queue[next_position]
      if self._volumio_service != next_track['service']:
        return None
      return next_track.get('title', next_track.get('name'))
    except:
      return None

  def get_previous_track(self) -> str:
    try:
      current_position = self._volumio_queue_position
      previous_position = current_position - 1
      previous_track = self._volumio_queue[previous_position]
      if self._volumio_service != previous_track['service']:
        return None
      return previous_track.get('title', previous_track.get('name'))
    except:
      return None
  
  def next_track(self):
    self._volumio_queue_position += 1
    self._socketIO.emit('next')
  
  def previous_track(self):
    if self.get_seek() >= 2:
      self._volumio_queue_position -= 1
      self._socketIO.emit('prev')
    self._volumio_queue_position -= 1
    self._socketIO.emit('prev')

  def get_seek(self):
    if self._volumio_status == 'stop':
      return 0
    if self._volumio_service == 'spop':
      if self._volumio_status == 'pause':
        return int(self._volumio_spotify_seek)
      else:
        elapsed = time.time() - self._volumio_spotify_seek_time
        return int(elapsed + self._volumio_spotify_seek)
    return int(self._volumio_seek)
  
  def get_duration(self):
    return self._volumio_duration

  def seek_up(self, seconds: int = 15):
    seek = self.get_seek()
    if self._volumio_duration - seek > seconds:
      self._socketIO.emit('seek',seek+seconds)
  
  def seek_down(self, seconds: int = 15):
    seek = self.get_seek()
    if seek > seconds:
      self._socketIO.emit('seek',seek-seconds)

  def toggle_play_stop(self):
    if not self.is_playing():
      self._socketIO.emit('play')
    else:
      self._socketIO.emit('stop')

  def resume(self):
    if not self.is_playing():
      self._socketIO.emit('play')

  def stop(self):
    if self._volumio_status != 'stop':
      self._socketIO.emit('stop')
  
  def pause(self):
    if self._volumio_status == 'play':
      self._socketIO.emit('pause')

  def get_current_service(self):
    return self._volumio_service

  def run(self):
    self._socketIO.emit('getState')
    self._socketIO.emit('getQueue')
    self._socketIO.wait()