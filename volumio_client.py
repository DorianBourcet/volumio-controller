import os
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import logging_setup

logger = logging_setup.get_logger(__name__)

DEFAULT_BASE_URL = os.environ.get('VC_VOLUMIO_URL', 'http://localhost:3000')
DEFAULT_TIMEOUT = float(os.environ.get('VC_VOLUMIO_HTTP_TIMEOUT', '10'))


class VolumioRestClient:
  """Thin REST client for Volumio's HTTP API.

  Handles transport concerns (timeout, retries, JSON validation) so callers
  can focus on browse/playback semantics. Errors are logged and translated
  to None / False rather than propagated, so that a Volumio outage doesn't
  kill the controller.
  """

  def __init__(
    self,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT,
    session: Optional[requests.Session] = None,
  ):
    self._base_url = base_url.rstrip('/')
    self._timeout = timeout
    self._session = session or self._build_session()

  @staticmethod
  def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
      total=3,
      backoff_factor=0.5,
      status_forcelist=(500, 502, 503, 504),
      allowed_methods=frozenset(['GET', 'POST']),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

  def browse(self, uri: str = '/') -> Optional[Dict[str, Any]]:
    url = f'{self._base_url}/api/v1/browse'
    try:
      response = self._session.get(url, params={'uri': uri}, timeout=self._timeout)
    except requests.RequestException:
      logger.exception('browse(%r) request failed', uri)
      return None
    if not response.ok:
      logger.warning('browse(%r) returned status %s', uri, response.status_code)
      return None
    try:
      payload = response.json()
    except ValueError:
      logger.exception('browse(%r) returned non-JSON body', uri)
      return None
    if not isinstance(payload, dict):
      logger.warning('browse(%r) returned non-dict payload: %r', uri, type(payload))
      return None
    return payload

  def replace_and_play(self, items: List[Dict[str, Any]], index: int = 0) -> bool:
    url = f'{self._base_url}/api/v1/replaceAndPlay'
    try:
      response = self._session.post(
        url,
        json={'index': index, 'list': items},
        timeout=self._timeout,
      )
    except requests.RequestException:
      logger.exception('replace_and_play failed')
      return False
    if not response.ok:
      logger.warning('replace_and_play returned status %s', response.status_code)
      return False
    return True


_default_client: Optional[VolumioRestClient] = None


def default_client() -> VolumioRestClient:
  global _default_client
  if _default_client is None:
    _default_client = VolumioRestClient()
  return _default_client
