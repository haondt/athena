import aiohttp
from .resource import ResourceLoader, try_extract_value_from_resource
from .exceptions import AthenaException
from typing import Any, Callable, List, Protocol, Dict, Tuple
from .trace import AthenaTrace, ResponseTrace, RequestTrace
from .request import RequestBuilder, Client
from .json import AthenaJSONEncoder, serializeable
from json import dumps as json_dumps
import inspect
import os

class _Fixture:
    def __init__(self):
        self._fixtures = {}
    def __getattr__(self, name) -> Any:
        if name in self._fixtures:
            return self._fixtures.get(name)
        raise KeyError(f"no such fixture registered: {name}")
    def __setattr__(self, name, value) -> None:
        if name.startswith("_"):
            self.__dict__[name] = value
        else:
            self._fixtures[name] = value

class _InjectFixture:
    def __init__(self, fixture: _Fixture, injected_arg: Any):
        self._fixture = fixture
        self._injected_arg = injected_arg
    def __getattr__(self, name) -> Callable:
        attr = self._fixture.__getattr__(name)
        if inspect.isfunction(attr):
            def injected_function(*args, **kwargs):
                return attr(self._injected_arg, *args, **kwargs)
            return injected_function
        raise ValueError(f"fixture {name} is not a function")
    def __setattr__(self, name, value) -> None:
        if name.startswith("_"):
            self.__dict__[name] = value
        else:
            self._fixtures.__setattr__(name, value)

class Fixture(Protocol):
    def __getattr__(self, name: str) -> Any: ...
    def __setattr__(self, name: str, value: Any) -> None: ...

_cache_value_types = str | int | float | bool
class Cache:
    def __init__(self, existing_data: Dict[Any, Any] | None=None):
        self._data: Dict[str, _cache_value_types] = {}
        if existing_data is not None:
            for k, v in existing_data.items():
                if isinstance(k, str) and isinstance(v, _cache_value_types):
                    self._data[k] = v

    def _assert_kvp(self, key: Any, value: Any):
        self._assert_key_type(key)
        self._assert_value_type(value)
    def _assert_key_type(self, key: Any):
        if not isinstance(key, str):
            raise ValueError(f"cannot index with key of type {type(key)}")
    def _assert_value_type(self, value: Any):
        if not isinstance(value, _cache_value_types):
            raise ValueError(f"cannot cache item of type {type(value)}")

    def __setitem__(self, key: str, value: _cache_value_types) -> None:
        self._assert_kvp(key, value)
        self._data[key] = value
    def __getitem__(self, key: str) -> Any:
        self._assert_key_type(key)
        if key in self._data:
            return self._data[key]
        raise KeyError(f"'{key}' not found")
    def __delitem__(self, key: str) -> None:
        self._assert_key_type(key)
        if key in self._data:
            del self._data[key]
    def __contains__(self, key: str) -> bool:
        self._assert_key_type(key)
        return key in self._data
    def pop(self, key: str) -> Any:
        self._assert_key_type(key)
        if key in self._data:
            return self._data.pop(key)
        raise KeyError(f"'{key}' not found")
    def clear(self) -> None:
        self._data.clear()

@serializeable
class Context:
    def __init__(self,
        environment: str,
        key: str,
        root_path: str,
        workspace_path: str,
        collection_path: str
    ):
        self.environment = environment
        self.key = key
        self.root_path = root_path
        self.workspace_path = workspace_path
        self.collection_path = collection_path
        self.workspace, self.collection, self.module = self.key.split(":")

class Athena:
    def __init__(self,
        context: Context,
        resource_loader: ResourceLoader,
        async_session: aiohttp.ClientSession, 
        cache_values: Dict
    ):
        self.__resource_loader = resource_loader
        self.__history: List[AthenaTrace | str] = []
        self.__pending_requests = {}
        self.__history_lookup_cache = {}
        self.__async_session = async_session
        self.fixture: Fixture = _Fixture()
        self.infix: Fixture = _InjectFixture(self.fixture, self)
        self.cache = Cache(cache_values)
        self.context = context

    def variable(self, name: str) -> str:
        root, workspace, collection = self.context.root_path, self.context.workspace, self.context.collection

        collection_variables = self.__resource_loader.load_collection_variables(root, workspace, collection)
        success, value = try_extract_value_from_resource(collection_variables, name, self.context.environment)
        if success:
            return value

        workspace_variables = self.__resource_loader.load_workspace_variables(root, workspace)
        success, value = try_extract_value_from_resource(workspace_variables, name, self.context.environment)
        if success:
            return value

        raise AthenaException(f"unable to find variable \"{name}\" with environment \"{self.context.environment}\". ensure variables have at least a default environment.")

    def secret(self, name: str) -> str:
        root, workspace, collection = self.context.root_path, self.context.workspace, self.context.collection

        collection_secrets = self.__resource_loader.load_collection_secrets(root, workspace, collection)
        success, value = try_extract_value_from_resource(collection_secrets, name, self.context.environment)
        if success:
            return value

        workspace_secrets = self.__resource_loader.load_workspace_secrets(root, workspace)
        success, value = try_extract_value_from_resource(workspace_secrets, name, self.context.environment)
        if success:
            return value

        raise AthenaException(f"unable to find secret \"{name}\" with environment \"{self.context.environment}\". ensure secrets have at least a default environment")

    def __client_pre_hook(self, trace_id: str) -> None:
        self.__history.append(trace_id)
        self.__pending_requests[trace_id] = len(self.__history) - 1

    def __client_post_hook(self, trace: AthenaTrace) -> None:
        if trace.id in self.__pending_requests:
            index = self.__pending_requests.pop(trace.id)
            if index < len(self.__history):
                self.__history[index] = trace
                return
        self.__history.append(trace)

    def client(self, base_build_request: Callable[[RequestBuilder], RequestBuilder] | None=None, name: str | None=None) -> Client:
        return Client(self.__async_session, base_build_request, name, self.__client_pre_hook, self.__client_post_hook)

    def traces(self) -> List[AthenaTrace]:
        return [i for i in self.__history if isinstance(i, AthenaTrace)]

    def trace(self, subject: AthenaTrace | RequestTrace | ResponseTrace | None=None) -> AthenaTrace:
        traces = self.traces()
        if subject is None:
            if len(traces) == 0:
                raise AthenaException(f"no completed traces in history")
            subject = traces[-1]

        is_trace = isinstance(subject, AthenaTrace)
        is_request_trace = isinstance(subject, RequestTrace)
        is_response_trace = isinstance(subject, ResponseTrace)
        if not (is_trace or is_request_trace or is_response_trace):
            raise AthenaException(f"unable to resolve parent for trace of type {type(subject).__name__}")

        if subject in self.__history_lookup_cache:
            return self.__history_lookup_cache[subject]
        trace = None
        for historic_trace in traces:
            if ((is_trace and historic_trace == subject)
                or (is_request_trace and historic_trace.request == subject)
                or (is_response_trace and historic_trace.response == subject)):
                trace = historic_trace
        if trace is None:
            raise AthenaException(f"unable to resolve parent for trace {subject}")

        self.__history_lookup_cache[subject] = trace
        return trace

def jsonify(item: Any, *args, **kwargs):
    return json_dumps(item, cls=AthenaJSONEncoder, *args, **kwargs)
