import requests

class VolumioBrowser:

  def __init__(self):
    self._uri_history = []

  def browse(self, index:int=None):
    if len(self._uri_history) == 0:
      pass
  
  def browse_from_root(self):
    response = requests.get('http://localhost/api/v1/browse')
    response = response.json()

    return map(lambda x: x.uri, response.navigation.lists)