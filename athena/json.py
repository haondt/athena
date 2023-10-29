from json import JSONEncoder, dumps
from typing import Any

_serializeable_classes = set()

def mark_serializeable(cls):
    _serializeable_classes.add(cls)
    return cls

class AthenaJSONEncoder(JSONEncoder):
    def default(self, o):
        if not o.__class__ in _serializeable_classes:
            return JSONEncoder.default(self, o)
        out = {}
        for k, v in o.__dict__.items():
            if not k.startswith("_"):
                out[k] = v
        return out

def jsonify(item: Any):
    return dumps(item, cls=AthenaJSONEncoder)
