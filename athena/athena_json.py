from json import JSONEncoder, dumps, loads, JSONDecoder
from typing import Any, Type

from .exceptions import AthenaException


_serializeable_classes = set()
_deserializeable_classes = {}

def serializeable(cls):
    _serializeable_classes.add(cls)
    return cls

def deserializeable(cls):
    _deserializeable_classes[cls.__name__] = cls
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

class AthenaReversibleJSONEncoder(JSONEncoder):
    def default(self, o):
        if not o.__class__ in _serializeable_classes:
            return JSONEncoder.default(self, o)
        out = {}
        for k, v in o.__dict__.items():
            if not k.startswith("_"):
                out[k] = v
        out["__class__"] = o.__class__.__name__
        return out


class AthenaJSONDecoder(JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.athena_object_hook, *args, **kwargs)
    def athena_object_hook(self, dct):
        if "__class__" in dct:
            class_name = dct["__class__"]
            if class_name in _deserializeable_classes:
                del dct["__class__"]
                cls = _deserializeable_classes[class_name]
                instance = cls()
                for k, v in dct.items():
                    instance.__dict__[k] = v
                return instance
        return dct
            
def jsonify(item: Any, reversible=False, indent: int | None = None):
    try:
        if reversible:
            return dumps(item, cls=AthenaReversibleJSONEncoder, indent=indent)
        return dumps(item, cls=AthenaJSONEncoder, indent=indent)
    except Exception as e:
        raise AthenaException(f"Error while dumping json: {e}")

def dejsonify(json_str: str, expected_type: Type | None=None):
    try:
        loaded = loads(json_str, cls=AthenaJSONDecoder)
        if expected_type is not None:
            if not isinstance(loaded, expected_type):
                raise AthenaException(f"Error while loading json: expected deserialized object to be of type `{expected_type.__name__}` but found `{type(loaded).__name__}`")
        return loaded
    except Exception as e:
        raise AthenaException(f"Error while loading json: {e}")
