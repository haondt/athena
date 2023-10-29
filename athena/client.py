from .resource import ResourceLoader, try_extract_value_from_resource
from .exceptions import AthenaException
from typing import Any, Callable, List, Protocol
from .trace import AthenaTrace, ResponseTrace, RequestTrace
from .request import RequestBuilder, Client

class _Fixture:
    _fixtures = {}
    def __getattr__(self, name) -> Any:
        if name in self._fixtures:
            return self._fixtures.get(name)
        raise KeyError(f"no such fixture registered: {name}")
    def __setattr__(self, name, value) -> None:
        self._fixtures[name] = value
class Fixture(Protocol):
    def __getattr__(self, name: str) -> Any: ...
    def __setattr__(self, name: str, value: Any) -> None: ...

class Athena:
    def __init__(self, context, environment, resource_loader: ResourceLoader):
        self.__context = context
        self.__resource_loader = resource_loader
        self.__environment = environment
        self.__history = []
        self.__history_lookup_cache = {}
        self.fixture: Fixture = _Fixture()

    def _get_context(self):
        return self.__context

    def get_variable(self, name: str) -> str:
        root, workspace, collection = self._get_context()

        collection_variables = self.__resource_loader.load_collection_variables(root, workspace, collection)
        success, value = try_extract_value_from_resource(collection_variables, name, self.__environment)
        if success:
            return value

        workspace_variables = self.__resource_loader.load_workspace_variables(root, workspace)
        success, value = try_extract_value_from_resource(workspace_variables, name, self.__environment)
        if success:
            return value

        raise AthenaException(f"unable to find variable \"{name}\" with environment \"{self.__environment}\". ensure variables have at least a default environment.")

    def get_secret(self, name: str) -> str:
        root, workspace, collection = self._get_context()

        collection_secrets = self.__resource_loader.load_collection_secrets(root, workspace, collection)
        success, value = try_extract_value_from_resource(collection_secrets, name, self.__environment)
        if success:
            return value

        workspace_secrets = self.__resource_loader.load_workspace_secrets(root, workspace)
        success, value = try_extract_value_from_resource(workspace_secrets, name, self.__environment)
        if success:
            return value

        raise AthenaException(f"unable to find secret \"{name}\" with environment \"{self.__environment}\". ensure secrets have at least a default environment")

    def __client_hook(self, trace: AthenaTrace) -> None:
        self.__history.append(trace)

    def client(self, base_build_request: Callable[[RequestBuilder], RequestBuilder] | None=None, name: str | None=None) -> Client:
        return Client(base_build_request, name, self.__client_hook)

    def traces(self) -> List[AthenaTrace]:
        return self.__history

    def trace(self, subject: AthenaTrace | RequestTrace | ResponseTrace | None=None) -> AthenaTrace:
        if subject is None:
            if len(self.__history) == 0:
                raise AthenaException(f"no traces in history")
            subject = self.__history[-1]

        is_trace = isinstance(subject, AthenaTrace)
        is_request_trace = isinstance(subject, RequestTrace)
        is_response_trace = isinstance(subject, ResponseTrace)
        if not (is_trace or is_request_trace or is_response_trace):
            raise AthenaException(f"unable to resolve parent for trace of type {type(subject).__name__}")

        if subject in self.__history_lookup_cache:
            return self.__history_lookup_cache[subject]
        trace = None
        for historic_trace in self.__history:
            if ((is_trace and historic_trace == subject)
                or (is_request_trace and historic_trace.request == subject)
                or (is_response_trace and historic_trace.response == subject)):
                trace = historic_trace
        if trace is None:
            raise AthenaException(f"unable to resolve parent for trace {subject}")

        self.__history_lookup_cache[subject] = trace
        return trace
