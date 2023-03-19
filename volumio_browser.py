import requests

class VolumioBrowser:

  def __init__(self):
    self._uri_history = []
    self._list_position = 0
    self._list = []

  def _fetch_list(self, uri: str):
    response = requests.get('http://localhost:3000/api/v1/browse', params={'uri': uri})
    return response.json()
  
  def reset(self):
    self._uri_history = []
    self._list_position = -1

  def get_menu(self, index: int=None):
    if index is None:
      index = 0
    if len(self._list) == 0:
      raw = self._fetch()
      self._list = raw.navigation.lists

  def enter_menu(self, index: int):
    pass
  def exit_menu(self):
    pass
  def get_menu(self, index: int):
    pass
  def next_menu(self):
    pass
  def previous_menu(self):
    pass

  def browse_from_root(self):
    self._browser_uri_history = []
    self._browser_queue_position = -1
    response = requests.get('http://localhost:3000/api/v1/browse')
    self._browser_response = response.json().navigation.lists
    #return map(lambda x: x.uri, response.navigation.lists)
  
  def browse_get_next_item(self) -> str:
    current_position = self._browser_queue_position
    next_position = current_position + 1
    return self.browse_get_item(next_position)

  def browse_get_item(self, index: int):
    item = self._browser_response[index]
    return item.get('name')

  def selected_index_next2(self):
    next_selected_index = self._selected_index + 1
    if next_selected_index >= len(self._volumio_queue):
      next_selected_index = 0
    self._selected_index = next_selected_index
    return self._selected_index
  
  def selected_index_previous2(self):
    previous_selected_index = self._selected_index - 1
    if previous_selected_index < 0:
      previous_selected_index = len(self._volumio_queue) - 1
    self._selected_index = previous_selected_index
    return self._selected_index