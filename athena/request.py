from __future__ import annotations
from time import time
import uuid

from .exceptions import AthenaException
import requests
import aiohttp, asyncio
from typing import Any, Callable
from .trace import AthenaTrace, ResponseTrace, AioHttpRequestContainer, LinkedResponse


class AthenaRequest:
    def __init__(self):
        self.auth: None | tuple[str, str] = None
        self.headers: dict[str, str] = {}
        self.base_url: str = ""
        self.url: str = ""
        self.method: str = ""
        self.files: Any = None
        self.data: dict[str, Any] = {}
        self.json: dict | list | str | None = None
        self.params: Any = {}
        self.cookies: Any = None
        self.verify_ssl: bool = True
        self.allow_redirects: bool = True

        self._before_hooks: list[Callable[[AthenaRequest], None]] = []
        self._after_hooks: list[Callable[[ResponseTrace], None]] = []

    def _run_before_hooks(self) -> None:
        for hook in self._before_hooks:
            hook(self)
    def _run_after_hooks(self, trace: ResponseTrace) -> None:
        for hook in self._after_hooks:
            hook(trace)

    def _to_requests_request(self) -> requests.PreparedRequest:
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
        ).prepare()

    def _to_aiohttp_request(self) -> AioHttpRequestContainer:
        kwargs = {
            'headers': self.headers,
            'data': self.data,
            'json': self.json,
            'params': self.params,
            'auth': self.auth,
            'cookies': self.cookies,
            'ssl': self.verify_ssl,
            'allow_redirects': self.allow_redirects
        }
        return AioHttpRequestContainer(
            self.method.upper(),
            f"{self.base_url}{self.url}",
            kwargs)

class AuthStepFactory:
    def __init__(self, 
        add_build_step: Callable[[Callable[[AthenaRequest], AthenaRequest]], None],
        parent: RequestBuilder):
        self._add_build_step = add_build_step
        self._parent = parent
    def bearer(self, token: str) -> RequestBuilder:
        def set_bearer(rq: AthenaRequest):
            rq.headers["Authorization"] = f"Bearer {token}" 
            return rq
        self._add_build_step(set_bearer)
        return self._parent
    def basic(self, username: str, password: str) -> RequestBuilder:
        def set_auth(rq: AthenaRequest):
            rq.auth = (username, password)
            return rq
        self._add_build_step(set_auth)
        return self._parent

class HookStepFactory:
    def __init__(self,
        add_build_step: Callable[[Callable[[AthenaRequest], AthenaRequest]], None],
        parent: RequestBuilder):
        self._add_build_step = add_build_step
        self._parent = parent
    def before(self, hook: Callable[[AthenaRequest], None]) -> RequestBuilder:
        def add_hook(rq: AthenaRequest):
            rq._before_hooks.append(hook)
            return rq
        self._add_build_step(add_hook)
        return self._parent
    def after(self, hook: Callable[[ResponseTrace], None]) -> RequestBuilder:
        def add_hook(rq: AthenaRequest):
            rq._after_hooks.append(hook)
            return rq
        self._add_build_step(add_hook)
        return self._parent

class BodyStepFactory:
    def __init__(self,
        add_build_step: Callable[[Callable[[AthenaRequest], AthenaRequest]], None],
        parent: RequestBuilder):
        self._add_build_step = add_build_step
        self._parent = parent
    def json(self, payload) -> RequestBuilder:
        def add_json(rq: AthenaRequest):
            rq.json = payload
            return rq
        self._add_build_step(add_json)
        return self._parent

    def form(self, payload: dict[str, str | int | float | bool]) -> RequestBuilder:
        def add_data(rq: AthenaRequest):
            rq.data = payload
            return rq
        self._add_build_step(add_data)
        return self._parent


class RequestBuilder:
    def __init__(self):
        self._build_steps: list[Callable[[AthenaRequest], AthenaRequest]] = []
        self.auth: AuthStepFactory = AuthStepFactory(lambda rq: self._build_steps.append(rq), self)
        self.hook: HookStepFactory = HookStepFactory(lambda rq: self._build_steps.append(rq), self)
        self.body: BodyStepFactory = BodyStepFactory(lambda rq: self._build_steps.append(rq), self)

    def base_url(self, base_url) -> RequestBuilder:
        def set_base_url(rq: AthenaRequest):
            rq.base_url = base_url
            return rq
        self._build_steps.append(set_base_url)
        return self

    def verify_ssl(self, verify_ssl: bool) -> RequestBuilder:
        def set_verify_ssl(rq: AthenaRequest):
            rq.verify_ssl = verify_ssl
            return rq
        self._build_steps.append(set_verify_ssl)
        return self

    def allow_redirects(self, allow_redirects: bool) -> RequestBuilder:
        def set_allow_redirects(rq: AthenaRequest):
            rq.allow_redirects = allow_redirects
            return rq
        self._build_steps.append(set_allow_redirects)
        return self

    def header(self, header_key, header_value) -> RequestBuilder:
        def add_header(rq: AthenaRequest):
            if header_key in  rq.headers:
                raise AthenaException(f"key \"{header_key}\" already present in request headers")
            rq.headers[header_key] = header_value
            return rq
        self._build_steps.append(add_header)
        return self

    def compile(self) -> Callable[[AthenaRequest], AthenaRequest]:
        def apply(request: AthenaRequest):
            for step in self._build_steps:
                request = step(request)
            return request
        return apply

    def apply(self, request: AthenaRequest) -> AthenaRequest:
        for step in self._build_steps:
            request = step(request)
        return request

class Client:
    def __init__(
            self,
            session: requests.Session,
            async_session: aiohttp.ClientSession,
            partial_request_builder: Callable[[RequestBuilder], RequestBuilder] | None=None,
            name=None,
            pre_hook: Callable[[str], None] | None=None,
            post_hook: Callable[[AthenaTrace], None] | None=None
        ):
        if partial_request_builder is not None:
            self.__base_request_apply = partial_request_builder(RequestBuilder()).compile()
        else:
            self.__base_request_apply = lambda rq: rq
        self.__session = session
        self.__async_session = async_session
        self.name = name or ""
        self.__pre_hook = pre_hook or (lambda _: None)
        self.__post_hook = post_hook or (lambda _: None)
        self.__async_lock = asyncio.Lock()

    def generate_trace_id(self):
        return str(uuid.uuid4())

    def send(self, method, url, build_request: Callable[[RequestBuilder], RequestBuilder] | None=None) -> ResponseTrace:
        trace_id = self.generate_trace_id()
        athena_request = self.__base_request_apply(AthenaRequest())
        athena_request.url = url
        athena_request.method = method
        if build_request is not None:
            athena_request = build_request(RequestBuilder()).apply(athena_request)

        athena_request._run_before_hooks()
        self.__pre_hook(trace_id)
        request = athena_request._to_requests_request()

        start = time()
        response = self.__session.send(request, allow_redirects=athena_request.allow_redirects, timeout=30, verify=athena_request.verify_ssl)
        end = time()

        trace_name = ""
        if self.name is not None and len(self.name) > 0:
            trace_name += self.name + "+"
        trace_name += athena_request.url
        trace = AthenaTrace(trace_id, trace_name, response.request, response, start, end)
        
        if(athena_request.verify_ssl == False):
            trace.warnings.append("request was executed with ssl verification disabled")

        self.__post_hook(trace)
        athena_request._run_after_hooks(trace.response)

        return trace.response
    
    async def send_async(self, method, url, build_request: Callable[[RequestBuilder], RequestBuilder] | None=None) -> ResponseTrace:
        trace_id = self.generate_trace_id()
        athena_request = self.__base_request_apply(AthenaRequest())
        athena_request.url = url
        athena_request.method = method
        if build_request is not None:
            athena_request = build_request(RequestBuilder()).apply(athena_request)

        athena_request._run_before_hooks()
        async with self.__async_lock:
            self.__pre_hook(trace_id)
        request = athena_request._to_aiohttp_request()

        trace = None
        timeout = aiohttp.ClientTimeout(total=30)

        start = time()
        async with self.__async_session.request(request.method, request.url, timeout=timeout, **request.kwargs) as response:
            end = time()
            trace_name = ""
            if self.name is not None and len(self.name) > 0:
                trace_name += self.name + "+"
            trace_name += athena_request.url
            assert isinstance(response, LinkedResponse)
            request = response.athena_get_request()
            assert request is not None
            trace = AthenaTrace(trace_id, trace_name, request, response, start, end, response_text=await response.text())

        if(athena_request.verify_ssl == False):
            trace.warnings.append("request was executed with ssl verification disabled")

        async with self.__async_lock:
            self.__post_hook(trace)
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
    async def get_async(self, url, build_request: Callable[[RequestBuilder], RequestBuilder] | None=None) -> ResponseTrace:
        return await self.send_async("get", url, build_request)
    async def post_async(self, url, build_request: Callable[[RequestBuilder], RequestBuilder] | None=None) -> ResponseTrace:
        return await self.send_async("post", url, build_request)
    async def delete_async(self, url, build_request: Callable[[RequestBuilder], RequestBuilder] | None=None) -> ResponseTrace:
        return await self.send_async("delete", url, build_request)
    async def put_async(self, url, build_request: Callable[[RequestBuilder], RequestBuilder] | None=None) -> ResponseTrace:
        return await self.send_async("put", url, build_request)
