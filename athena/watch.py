from threading import Timer
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent, EVENT_TYPE_MODIFIED
from typing import Callable
import asyncio

class Handler(FileSystemEventHandler):
    def __init__(self, settle: float, callback: Callable[[str, str], None]):
        self.callback = callback
        self.settle = settle
        self.last_modified = None
        self.timers: dict[str, Timer] = {}

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        path = event.src_path
        if self.timers.get(path):
            self.timers[path].cancel()
        self.timers[path] = Timer(self.settle, self._debounced_callback, [event.event_type, event.src_path])
        self.timers[path].start()

    def _debounced_callback(self, event_type: str, path: str) -> None:
        del self.timers[path]
        self.callback(event_type, path)

async def watch_async(path: str, settle: float, callback: Callable[[str, str], None]):
    handler = Handler(settle, callback)
    observer = Observer()
    observer.schedule(handler, path=path, recursive=True)
    observer.start()

    try: 
        await asyncio.Event().wait()
    finally: 
        observer.stop()
        observer.join()

def watch(path: str, settle: float, callback: Callable[[str, str], None]):
    handler = Handler(settle, callback)
    observer = Observer()
    observer.schedule(handler, path=path, recursive=True)
    observer.start()

    try:
        while observer.is_alive():
            observer.join(1)
    finally:
        observer.stop()
    observer.join()
