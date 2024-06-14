from threading import Timer
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileSystemEvent, EVENT_TYPE_MODIFIED
from typing import Callable

class Handler(FileSystemEventHandler):
    def __init__(self, settle: float, callback: Callable[[str], None]):
        self.callback = callback
        self.settle = settle
        self.last_modified = None
        self.timer = None

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        # if not event.src_path.endswith(".py"):
        #     return

        if self.timer:
            self.timer.cancel()
        self.timer = Timer(self.settle, self._debounced_callback, [event.src_path])
        self.timer.start()

    def _debounced_callback(self, path: str) -> None:
        self.callback(path)


def watch(path: str, settle: float, callback: Callable[[str], None]):
    handler = Handler(settle, callback)
    observer = Observer()
    observer.schedule(handler, path=path, recursive=True, event_filter=[FileModifiedEvent, FileCreatedEvent] )
    observer.start()

    try:
        while observer.is_alive():
            observer.join(1)
    finally:
        observer.stop()
    observer.join()
