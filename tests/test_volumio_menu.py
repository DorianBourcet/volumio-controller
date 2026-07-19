from unittest.mock import MagicMock

import volumio_menu


def make_menu(client):
  return volumio_menu.VolumioMenu('volumio', client=client)


def test_browse_returns_empty_when_volumio_is_unreachable():
  client = MagicMock()
  client.browse.return_value = None
  menu = make_menu(client)
  out = menu.browse()
  assert out == []


def test_browse_decorates_items_with_provider():
  client = MagicMock()
  client.browse.return_value = {
    'navigation': {
      'lists': [{
        'items': [
          {'title': 'Folk', 'uri': '/folk', 'type': 'folder'},
          {'title': 'Song', 'uri': '/song.mp3', 'type': 'song'},
        ],
      }],
    },
  }
  menu = make_menu(client)
  out = menu.browse()
  assert all(item['provider'] == 'volumio' for item in out)
  by_name = {item['name']: item for item in out}
  assert by_name['Folk']['is_node'] is True
  assert by_name['Song']['is_node'] is False


def test_browse_caches_results_between_calls():
  client = MagicMock()
  client.browse.return_value = {'navigation': {'lists': [{'items': []}]}}
  menu = make_menu(client)
  menu.browse('/some-uri')
  menu.browse('/some-uri')
  # Second call should be served from cache, not re-hit the client.
  assert client.browse.call_count == 1


def test_browse_handles_missing_navigation_key():
  client = MagicMock()
  client.browse.return_value = {'unrelated': 'payload'}
  menu = make_menu(client)
  assert menu.browse() == []


def test_playable_item_triggers_play():
  client = MagicMock()
  # First browse returns a list with one playable child
  client.browse.return_value = {
    'navigation': {
      'lists': [{
        'items': [{'title': 'Song', 'uri': '/song', 'type': 'song'}],
      }],
    },
  }
  client.replace_and_play.return_value = True
  menu = make_menu(client)
  menu.browse('/folder')
  result = menu.browse('/song')
  assert result == {'terminated': True, 'message': 'LECTURE'}
  client.replace_and_play.assert_called_once()


def test_playable_item_play_failure_returns_error():
  client = MagicMock()
  client.browse.return_value = {
    'navigation': {
      'lists': [{
        'items': [{'title': 'Song', 'uri': '/song', 'type': 'song'}],
      }],
    },
  }
  client.replace_and_play.return_value = False
  menu = make_menu(client)
  menu.browse('/folder')
  result = menu.browse('/song')
  assert result == {'terminated': False, 'message': 'une erreur est survenue'}
