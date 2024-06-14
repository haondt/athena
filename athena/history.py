import concurrent.futures
from typing import Callable
import os


def get_history_file(root: str):
    return os.path.join(root, '.history')

executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

def push(root:str, item: str | Callable[[], str]):
    def write_to_file():
        with open(get_history_file(root), 'a') as f:
            if isinstance(item, str):
                f.write(item + '\n')
            else:
                f.write(item() + '\n')
    executor.submit(write_to_file)

def get(root: str):
    with open(get_history_file(root), 'r') as f:
        return f.read()

def clear(root: str):
    with open(get_history_file(root), 'w') as f:
        pass

import atexit
atexit.register(executor.shutdown)

