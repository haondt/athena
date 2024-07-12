import aiohttp
import requests

from .resource import ResourceLoader, try_extract_value_from_resource, _resource_type, _resource_value_type
from .exceptions import AthenaException
from typing import Any, Callable, Protocol
from .trace import AthenaTrace, ResponseTrace, RequestTrace, LinkedRequest, LinkedResponse
from .request import RequestBuilder, Client
from .athena_json import AthenaJSONEncoder, serializeable
from .fake import Fake
from json import dumps as json_dumps
from contextlib import AsyncExitStack
import inspect

class ResourceFacade:
    def __init__(self, loader: Callable[[], _resource_type], resource_type: str, environment: str):
        self._loader = loader
        self._resource_type = resource_type
        self._environment = environment

    def _load_resource(self, name) -> _resource_value_type:
        success, value = self._try_load_resource(name)
        if success:
            return str(value)

        raise AthenaException(f"unable to find {self._resource_type} \"{name}\" with environment \"{self._environment}\". ensure {self._resource_type}s have at least a default environment.")

    def _try_load_resource(self, name) -> tuple[bool, _resource_value_type]:
        resource = self._loader()
        return try_extract_value_from_resource(resource, name, self._environment)

    def __getitem__(self, key) -> _resource_value_type:
        """Get value by name. Throws an error if the key cannot be found.

        Args:
            key (str): Name of resource to retrieve.

        Returns:
            _resource_value_type: value
        """
        return self._load_resource(key)

    def get(self, key, default: _resource_value_type | None=None) -> _resource_value_type | None:
        """Get value by name. Returns default value if key cannot be found.

        Args:
            key (str): Name of resource to retrieve.
            default (_resource_value_type | None): Default value

        Returns:
            _resource_value_type | None: value
        """
        success, value = self._try_load_resource(key)
        if success:
            return value
        return default

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
    def __init__(self, existing_data: dict[Any, Any] | None=None):
        self._data: dict[str, _cache_value_types] = {}
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
    """Information about the runtime environment of the module

    Attributes:
        environment (str): name of environment
        module_name (str): name of the module
        module_path (str): path to the module
        root_path (str): path to root of athena directory
    """
    def __init__(self,
        environment: str | None,
        module_name: str,
        module_path: str,
        root_path: str
    ):
        self._environment = environment
        self.environment = str(environment)
        self.module_name = module_name
        self.module_path = module_path
        self.root_path = root_path

class AthenaSession:
    def __init__(self):
        self.async_session = aiohttp.ClientSession(request_class=LinkedRequest, response_class=LinkedResponse)
        self.session = requests.Session()
        self.resource_loader = ResourceLoader()

    def __enter__(self):
        raise TypeError("Use async with instead")

    def __exit__(self, *args):
        # should never be called
        pass

    async def __aenter__(self):
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(self.async_session)
            stack.enter_context(self.session)
            self._stack = stack.pop_all()
        return self

    async def __aexit__(self, *args):
        await self._stack.__aexit__(*args)


class Athena:
    """Main api for executed modules

    Attributes:
        fixture (Fixture): provider for test fixtures
        infix (Fixture): wrapper for `fixture` that will inject `Athena` instance as the first argument
        cache (Cache): persistent key (`str`) - value (`str`, `int`, `float`, `bool`) cache
        context (Context): information about the runtime environment of the module
        fake (Fake): generate randomized data
        variable (ResourceFacade): get a variable by name
        secret (ResourceFacade): get a secret by name
    """
    def __init__(self,
        context: Context,
        session: AthenaSession,
        cache_values: dict
    ):
        self.__history: list[AthenaTrace | str] = []
        self.__pending_requests = {}
        self.__history_lookup_cache = {}
        self.__session = session
        self.fixture: Fixture = _Fixture()
        self.infix: Fixture = _InjectFixture(self.fixture, self)
        self.cache = Cache(cache_values)
        self.context = context
        self.fake = Fake()
        self.variable = ResourceFacade(
            lambda: self.__session.resource_loader.load_variables(self.context.root_path, self.context.module_path),
            'variable', self.context.environment)
        self.secret = ResourceFacade(
            lambda: self.__session.resource_loader.load_secrets(self.context.root_path, self.context.module_path),
            'secret', self.context.environment)

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
        """Create a new client.

        Args:
            base_build_request (Callable[[RequestBuilder], [RequestBuilder]] | None): Function to configure all requests sent by the client.
            name (str | None): Optional name for client.

        Returns:
            Client: The configured client.
        """
        return Client(self.__session.session, self.__session.async_session, base_build_request, name, self.__client_pre_hook, self.__client_post_hook)

    def traces(self) -> list[AthenaTrace]:
        """Get all `AthenaTrace`s from the lifetime of this instance. 

        Returns:
            list[AthenaTrace]: List of traces.
        """
        return [i for i in self.__history if isinstance(i, AthenaTrace)]

    def trace(self, subject: AthenaTrace | RequestTrace | ResponseTrace | None=None) -> AthenaTrace:
        """Get the full `AthenaTrace` for a given request or response trace.

        Args:
            subject (AthenaTrace | RequestTrace | ResponseTrace | None): The trace to lookup. If no trace is provided, will return the most recent trace.

        Returns:
            AthenaTrace: The full `AthenaTrace` for the subject.

        Example:

            def run(athena: Athena):
                response = athena.client().get('https://example.com')
                trace = athena.trace(response)
                print(f'request completed in {trace.elapsed} seconds')
        """
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
    """Runs objects through json.dumps, with an encoder for athena objects.

    Args:
        item (Any): The item to json encode.

    Returns:
        str: The json string

    Example:

        from athena.client import Athena, jsonify

        def run(athena: Athena):
            athena.client().get("http://haondt.com")
            traces = athena.traces()
            print(jsonify(traces, indent=4))
    """
    return json_dumps(item, cls=AthenaJSONEncoder, *args, **kwargs)
