from main_thread import MainThread

thread = MainThread()
thread.daemon = True
thread.start()
thread.join()
