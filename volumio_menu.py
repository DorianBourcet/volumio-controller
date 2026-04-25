from typing import Any, Dict, List, Optional, Union

import logging_setup
import volumio_client

logger = logging_setup.get_logger(__name__)

PLAYABLE_TYPES = ('song', 'mywebradio', 'webradio')
NODE_LEAF_TYPES = ('song', 'mywebradio')


class VolumioMenu:

  def __init__(
    self,
    provider_name: str,
    client: Optional[volumio_client.VolumioRestClient] = None,
  ):
    self._provider_name = provider_name
    self._latest_uri: Optional[str] = None
    self._uri_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}
    self._client = client or volumio_client.default_client()

  def invalidate_cache(self, uri: Optional[str] = None) -> None:
    if uri is None:
      self._uri_cache.clear()
      self._latest_uri = None
      return
    self._uri_cache.pop(uri, None)

  def _set_uri_items(self, uri: str, items: List[Dict[str, Any]]) -> None:
    items_by_uri = {item['uri']: item for item in items if 'uri' in item}
    self._uri_cache[uri] = items_by_uri

  def _add_uri_item(self, uri: str, item: Dict[str, Any]) -> None:
    if 'uri' not in item:
      return
    if uri not in self._uri_cache:
      self._uri_cache[uri] = {}
    self._uri_cache[uri][item['uri']] = item

  def _add_uri_items(self, uri: str, items: List[Dict[str, Any]]) -> None:
    items_by_uri = {item['uri']: item for item in items if 'uri' in item}
    if uri not in self._uri_cache:
      self._uri_cache[uri] = {}
    self._uri_cache[uri].update(items_by_uri)

  def _get_items(self, uri: str) -> Dict[str, Dict[str, Any]]:
    if uri not in self._uri_cache:
      raw_list = self._client.browse(uri)
      if not raw_list:
        return {}
      self._build_cache(uri, raw_list)
    return self._uri_cache.get(uri, {})

  def _get_uris(self, uri: str) -> List[str]:
    if uri not in self._uri_cache:
      raw_list = self._client.browse(uri)
      if not raw_list:
        return []
      self._build_cache(uri, raw_list)
    return list(self._uri_cache.get(uri, {}))

  def _play_items(self, items: List[Dict[str, Any]], index: int = 0) -> bool:
    return self._client.replace_and_play(items, index)

  def _build_cache(self, uri: str, raw: Dict[str, Any]) -> None:
    if 'navigation' not in raw or 'lists' not in raw['navigation']:
      logger.debug('browse(%r) returned no navigation/lists', uri)
      return
    raw_lists = raw['navigation']['lists']
    raw_length = len(raw_lists)
    for x in raw_lists:
      if 'items' not in x:
        self._add_uri_item(uri, x)
      elif raw_length > 1 and 'title' in x:
        sub_uri = f"{uri}/{x['title']}"
        self._add_uri_item(uri, {
          'title': x['title'],
          'uri': sub_uri,
          'type': 'standalone_menu',
        })
        self._set_uri_items(sub_uri, x['items'])
      else:
        self._add_uri_items(uri, x['items'])

  def _is_playable(self, item: Dict[str, Any]) -> bool:
    return item.get('type') in PLAYABLE_TYPES

  def browse(self, uri: str = '/') -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    logger.debug('browse %r', uri)
    if uri not in self._uri_cache and self._latest_uri:
      uris = self._get_uris(self._latest_uri)
      if uri in uris:
        items = self._get_items(self._latest_uri)
        item = items[uri]
        if self._is_playable(item):
          logger.info('playing item %r', item.get('title') or item.get('name'))
          success = self._play_items(list(items.values()), uris.index(uri))
          if not success:
            return {'terminated': False, 'message': 'une erreur est survenue'}
          return {'terminated': True, 'message': 'LECTURE'}
    self._latest_uri = uri
    items = list(self._get_items(uri).values())
    return [
      {
        'name': x['title'] if 'title' in x else x.get('name'),
        'uri': x.get('uri'),
        'is_node': 'type' in x and x['type'] not in NODE_LEAF_TYPES,
        'provider': self._provider_name,
      }
      for x in items
    ]
