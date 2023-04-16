import requests

def browse(uri: str):
  response = requests.get('http://localhost:3000/api/v1/browse', params={'uri': uri}, timeout=2)
  return response.json()

def play_items(items: list, index: int = 0):
  response = requests.post('http://localhost:3000/api/v1/replaceAndPlay', json={'index':index,'list':items})
  return response.ok
