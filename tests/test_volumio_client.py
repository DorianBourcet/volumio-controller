import responses

import volumio_client


@responses.activate
def test_browse_returns_payload():
  responses.add(
    responses.GET,
    'http://localhost:3000/api/v1/browse',
    json={'navigation': {'lists': []}},
    status=200,
  )
  client = volumio_client.VolumioRestClient()
  out = client.browse('/')
  assert out == {'navigation': {'lists': []}}


@responses.activate
def test_browse_returns_none_on_5xx():
  responses.add(
    responses.GET,
    'http://localhost:3000/api/v1/browse',
    status=503,
  )
  client = volumio_client.VolumioRestClient()
  assert client.browse('/') is None


@responses.activate
def test_browse_returns_none_on_invalid_json():
  responses.add(
    responses.GET,
    'http://localhost:3000/api/v1/browse',
    body='not json',
    status=200,
  )
  client = volumio_client.VolumioRestClient()
  assert client.browse('/') is None


@responses.activate
def test_browse_rejects_non_dict_payload():
  responses.add(
    responses.GET,
    'http://localhost:3000/api/v1/browse',
    json=['not', 'a', 'dict'],
    status=200,
  )
  client = volumio_client.VolumioRestClient()
  assert client.browse('/') is None


@responses.activate
def test_replace_and_play_success():
  responses.add(
    responses.POST,
    'http://localhost:3000/api/v1/replaceAndPlay',
    status=200,
  )
  client = volumio_client.VolumioRestClient()
  assert client.replace_and_play([{'uri': 'a'}], 0) is True


@responses.activate
def test_replace_and_play_failure_returns_false():
  responses.add(
    responses.POST,
    'http://localhost:3000/api/v1/replaceAndPlay',
    status=500,
  )
  client = volumio_client.VolumioRestClient()
  assert client.replace_and_play([{'uri': 'a'}], 0) is False


@responses.activate
def test_custom_base_url():
  responses.add(
    responses.GET,
    'http://volumio.local:3000/api/v1/browse',
    json={},
    status=200,
  )
  client = volumio_client.VolumioRestClient(base_url='http://volumio.local:3000')
  assert client.browse('/') == {}
