"""Backwards-compatible thin shim around volumio_client.

Kept so that legacy imports (`import volumio_api`) keep working. Prefer
`volumio_client.VolumioRestClient` for new code — it supports dependency
injection, retries, and explicit error reporting.
"""
from typing import Any, Dict, List, Optional

import volumio_client


def browse(uri: str) -> Optional[Dict[str, Any]]:
  return volumio_client.default_client().browse(uri)


def play_items(items: List[Dict[str, Any]], index: int = 0) -> bool:
  return volumio_client.default_client().replace_and_play(items, index)
