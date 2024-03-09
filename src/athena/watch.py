from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileSystemEvent, EVENT_TYPE_MODIFIED
from typing import Callable

class Handler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if not event.src_path.endswith(".py"):
            return
        self.callback(event.src_path)


def watch(path: str, callback: Callable[[str], None]):
    handler = Handler(callback)
    observer = Observer()
    observer.schedule(handler, path=path, recursive=True, event_filter=[FileModifiedEvent, FileCreatedEvent] )
    observer.start()

    try:
        while observer.is_alive():
            observer.join()
    finally:
        observer.stop()
        observer.join()
