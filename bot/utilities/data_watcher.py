import time
from pathlib import Path
from typing import Callable
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

Callback = Callable[[str], None]

callbaques: list[tuple[Path, Callback]] = []
class FileWatcher(FileSystemEventHandler):
	def on_modified(self, event: FileModifiedEvent):
		if not isinstance(event, FileModifiedEvent): 
			return;

		event.src_path = event.src_path.replace("\\", "/")
		for callback in callbaques:
			p = event.src_path.split("bot/data/")[1]
			if p.startswith(callback[0]):
				callback[1](p[len(callback[0]):])
				
def subscribe(path: str, cb: Callback):
	callbaques.append((path, cb))

def watch():
	observer = Observer()
	observer.schedule(FileWatcher(), path="bot/data/", recursive=True, event_filter=[FileModifiedEvent])
	observer.start()

	try:
		a = False
		def fnum(a):
			return a
		while True:
			time.sleep(60*60*24)
			if a == False:
				print("[ Hello. ]")
				a = 1
			else:
				print(f"[ Hello for the {fnum(a)} time ]")
				a += 1
	except KeyboardInterrupt:
		observer.stop()
	observer.join()

watcher_thread = Thread(target=watch)
watcher_thread.daemon = True
watcher_thread.start()