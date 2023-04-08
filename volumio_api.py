import requests

def browse(uri: str):
  response = requests.get('http://localhost:3000/api/v1/browse', params={'uri': uri})
  return response.json()

def play_items(items: list, index: int = 0):
  response = requests.post('http://10.0.0.46/api/v1/replaceAndPlay', data={'index':index,'list':items})
  return response.json()
