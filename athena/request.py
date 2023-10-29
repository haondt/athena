from __future__ import annotations

from requests.sessions import PreparedRequest
from .exceptions import AthenaException
import requests, json
from typing import Any, Callable, Dict, List, Tuple
from .trace import AthenaTrace, ResponseTrace

class AthenaRequest:
    def __init__(self):
        self.auth: Callable[[PreparedRequest], Any] | None | Tuple[str, str] = None
        self.headers: Dict[str, str] = {}
        self.base_url: str = ""
        self.url: str = ""
        self.method: str = ""
        self.files: Any = None
        self.data: Dict[str, Any] = {}
        self.json: Dict | List | str | None = None
        self.params: Any = {}
        self.cookies: Any = None

        self._before_hooks: List[Callable[[AthenaRequest], None]] = []
        self._after_hooks: List[Callable[[ResponseTrace], None]] = []

    def _run_before_hooks(self) -> None:
        for hook in self._before_hooks:
            hook(self)
    def _run_after_hooks(self, trace: ResponseTrace) -> None:
        for hook in self._after_hooks:
            hook(trace)

    def _to_request(self) -> requests.Request:
        return requests.Request(
            method=self.method.upper(),
            url=f"{self.base_url}{self.url}",
            headers=self.headers, files=self.files,
            data=self.data,
            json=self.json,
            params=self.params,
            auth=self.auth,
            cookies=self.cookies,
            hooks=None
        )

class AuthBuilder:
    def __init__(self):
        self.add_auth = lambda rb: rb
    def bearer(self, token: str) -> AuthBuilder:
        def set_bearer(rq: AthenaRequest):
            rq.headers["Authorization"] = f"Bearer {token}" 
            return rq
        self.add_auth = set_bearer
        return self
    def basic(self, username: str, password: str) -> AuthBuilder:
        def set_auth(rq: AthenaRequest):
            rq.auth = (username, password)
            return rq
        self.add_auth = set_auth
        return self
    def compile(self) -> Callable[[AthenaRequest], AthenaRequest]:
        return self.add_auth

class HookBuilder:
    def __init__(self):
        self.__before_hooks: List[Callable[[AthenaRequest], None]] = []
        self.__after_hooks: List[Callable[[ResponseTrace], None]] = []
    def before(self, hook: Callable[[AthenaRequest], None]) -> HookBuilder:
        self.__before_hooks.append(hook)
        return self
    def after(self, hook: Callable[[ResponseTrace], None]) -> HookBuilder:
        self.__after_hooks.append(hook)
        return self
    def compile(self) -> Callable[[AthenaRequest], AthenaRequest]:
        def add_hooks(rq: AthenaRequest):
            rq._before_hooks += self.__before_hooks
            rq._after_hooks += self.__after_hooks
            return rq
        return add_hooks

class RequestBuilder:
    def __init__(self):
        self.build_steps = []

    def base_url(self, base_url) -> RequestBuilder:
        def set_base_url(rq: AthenaRequest):
            rq.base_url = base_url
            return rq
        self.build_steps.append(set_base_url)
        return self

    def auth(self, build_auth: Callable[[AuthBuilder], AuthBuilder]) -> RequestBuilder:
        self.build_steps.append(build_auth(AuthBuilder()).compile())
        return self

    def hook(self, build_hook: Callable[[HookBuilder], HookBuilder]) -> RequestBuilder:
        self.build_steps.append(build_hook(HookBuilder()).compile())
        return self

    def header(self, header_key, header_value) -> RequestBuilder:
        def add_header(rq: AthenaRequest):
            if header_key in  rq.headers:
                raise AthenaException(f"key \"{header_key}\" already present in request headers")
            rq.headers[header_key] = header_value
            return rq
        self.build_steps.append(add_header)
        return self

    def json(self, payload) -> RequestBuilder:
        def add_json(rq: AthenaRequest):
            rq.json = payload
            return rq
        self.build_steps.append(add_json)
        return self

    def form(self, payload) -> RequestBuilder:
        def add_data(rq: AthenaRequest):
            rq.data = payload
            return rq
        self.build_steps.append(add_data)
        return self

    def compile(self) -> Callable[[AthenaRequest], AthenaRequest]:
        def apply(request: AthenaRequest):
            for step in self.build_steps:
                request = step(request)
            return request
        return apply

    def apply(self, request: AthenaRequest) -> AthenaRequest:
        for step in self.build_steps:
            request = step(request)
        return request

class Client:
    def __init__(self, partial_request_builder: Callable[[RequestBuilder], RequestBuilder] | None=None, name=None, hook: Callable[[AthenaTrace], None] | None=None):
        if partial_request_builder is not None:
            self.__base_request_apply = partial_request_builder(RequestBuilder()).compile()
        else:
            self.__base_request_apply = lambda rq: rq
        self.__session = requests.Session()
        self.name = name or ""
        self.__hook = hook or (lambda t: None)

    def send(self, method, url, build_request: Callable[[RequestBuilder], RequestBuilder] | None=None) -> ResponseTrace:
        athena_request = self.__base_request_apply(AthenaRequest())
        athena_request.url = url
        athena_request.method = method
        if build_request is not None:
            athena_request = build_request(RequestBuilder()).apply(athena_request)

        athena_request._run_before_hooks()
        request = athena_request._to_request()
        prepared_request = request.prepare()

        response = self.__session.send(prepared_request, allow_redirects=False, timeout=30)
        trace = AthenaTrace(response)
        self.__hook(trace)
        athena_request._run_after_hooks(trace.response)

        return trace.response

    def get(self, url, build_request: Callable[[RequestBuilder], RequestBuilder] | None=None) -> ResponseTrace:
        return self.send("get", url, build_request)
    def post(self, url, build_request: Callable[[RequestBuilder], RequestBuilder] | None=None) -> ResponseTrace:
        return self.send("post", url, build_request)
    def delete(self, url, build_request: Callable[[RequestBuilder], RequestBuilder] | None=None) -> ResponseTrace:
        return self.send("delete", url, build_request)
    def put(self, url, build_request: Callable[[RequestBuilder], RequestBuilder] | None=None) -> ResponseTrace:
        return self.send("put", url, build_request)
