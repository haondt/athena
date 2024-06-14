from dataclasses import dataclass

import os

from .resource import DEFAULT_ENVIRONMENT_KEY
from .exceptions import AthenaException
from . import file

@dataclass
class State:
    environment: str = DEFAULT_ENVIRONMENT_KEY

def init() -> State:
    return State()

def load(root: str) -> State:
    state_yaml = {}
    with open(os.path.join(root, '.athena'), 'r') as f:
        state_yaml = file.import_yaml(f.read())
    state = State()
    if not isinstance(state_yaml, dict):
        raise AthenaException("State was not in the expected format. See contents of .athena")
    for k, v in state_yaml.items():
        state.__dict__[k] = v
    return state

def save(root: str, state: State):
    state_yaml = file.export_yaml(state.__dict__)
    with open(os.path.join(root, '.athena'), 'w') as f:
        f.write(state_yaml)
    return 
