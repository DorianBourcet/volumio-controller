from main_thread import MainThread
from volumio_menu import VolumioMenu

# menu = VolumioMenu('volumio')
# result = menu.browse('/')
# result = menu.browse('favourites')
# result = menu.browse('webfip/002')
# result = menu.browse('spotify')
# result = menu.browse('spotify/Genres & Ambiances')
# print(result)
# print(menu._options_cache.keys())
# result = menu.browse('spotify/Genres & Ambiances')
# print(menu._options_cache.keys())
# print(result)

thread = MainThread()
thread.daemon = True
thread.start()
thread.join()
