import os

from .json import serializeable, jsonify, deserializeable, dejsonify

@serializeable
@deserializeable
class Cache:
    def __init__(self):
        self.data = {}

def get_cache_file_path(root: str):
    return os.path.join(root, ".cache")


def load(root: str) -> Cache:
    cache_file_path = get_cache_file_path(root)
    if not os.path.isfile(cache_file_path):
        return Cache()
    with open(cache_file_path, "r") as f:
        return dejsonify(f.read())

def save(root: str, state: Cache):
    cache_file_path = get_cache_file_path(root)
    with open(cache_file_path, "w") as f:
        f.write(jsonify(state, reversible=True))

def clear(root: str):
    save(root, Cache())

