import volumio_api

class VolumioMenu:

  def __init__(self, provider_name: str):
    self._provider_name = provider_name
    self._latest_uri = None
    self._uri_cache = {}
  
  def _set_uri_items(self, uri: str, items: list):
    items_by_uri = {}
    for item in items:
      items_by_uri[item['uri']] = item
    self._uri_cache[uri] = items_by_uri
  
  def _add_uri_item(self, uri: str, item: dict):
    if not 'uri' in item:
      return
    if not uri in self._uri_cache:
      self._uri_cache[uri] = {}
    self._uri_cache[uri][item['uri']] = item
  
  def _add_uri_items(self, uri: str, items: list):
    items_by_uri = {}
    for item in items:
      items_by_uri[item['uri']] = item
    if not uri in self._uri_cache:
      self._uri_cache[uri] = {}
    self._uri_cache[uri].update(items_by_uri)
  
  def _get_items(self, uri: str) -> list:
    if uri not in self._uri_cache:
      # must build the cache
      raw_list = volumio_api.browse(uri)
      if not raw_list:
        return {}
      self._build_cache(uri,raw_list)
    return self._uri_cache[uri]
  
  def _get_uris(self, uri: str) -> list:
    if uri not in self._uri_cache:
      # must build the cache
      raw_list = volumio_api.browse(uri)
      if not raw_list:
        return []
      self._build_cache(uri,raw_list)
    return list(self._uri_cache[uri])
  
  def _play_items(self, items: list, index: int = 0) -> bool:
    return volumio_api.play_items(items,index)
  
  def _build_cache(self, uri: str, raw: dict):
    if not 'navigation' in raw or not 'lists' in raw['navigation']:
      return
    raw_length = len(raw['navigation']['lists'])
    for x in raw['navigation']['lists']:
      if not 'items' in x:
        self._add_uri_item(uri,x)
      elif raw_length > 1 and 'title' in x:
        self._add_uri_item(uri,{
          'title': x['title'],
          'uri': uri+'/'+x['title'],
          'type': 'standalone_menu'
        })
        self._set_uri_items(uri+'/'+x['title'],x['items'])
      else:
        self._add_uri_items(uri,x['items'])
  
  def _is_playable(self, item: dict):
    if 'type' in item and item['type'] in ['song','mywebradio','webradio']:
      return True
    return False

  def browse(self, uri: str = '/'):
    print('======================')
    print(uri)
    if not uri in self._uri_cache:
      print('.. was not found')
      # could be a playable
      if self._latest_uri:
        uris = self._get_uris(self._latest_uri)
        #print(uris)
        if uri in uris:
          items = self._get_items(self._latest_uri)
          item = items[uri]
          if self._is_playable(item):
            print('playable found, will play')
            print(item)
            #print(self._get_items(self._latest_uri))
            #print(uris.index(uri))
            success = self._play_items(list(items.values()),uris.index(uri))
            if not success:
              return {
                'terminated': False,
                'message': 'une erreur est survenue'
              }
            return {
              'terminated': True,
              'message': 'LECTURE'
            }
    print('no latest_uri, or uri not found in uris')
    print('registering latest uri... ')
    print(self._latest_uri)
    self._latest_uri = uri
    items = list(self._get_items(uri).values())
    return list(map(
      lambda x: {
        'name': x['title'] if 'title' in x else x['name'],
        'uri': x['uri'],
        'is_node': False if 'type' not in x or x['type'] in ['song','mywebradio'] else True,
        'provider': self._provider_name
      },
      items
    ))