from __future__ import annotations
from .exceptions import AthenaException
import requests, json
from typing import Callable
from .trace import AthenaTrace

class AthenaRequest:
    def __init__(self):
        self.auth = None
        self.headers = {}
        self.base_url = ""
        self.url = ""
        self.method = ""
        self.files = None
        self.data = {}
        self.json = None
        self.params = {}
        self.cookies = None

    def to_request(self) -> requests.Request:
        return requests.Request(
            method=self.method.upper(),
            url=f"{self.base_url}{self.url}",
            headers=self.headers,
            files=self.files,
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
    def bearer(self, token) -> AuthBuilder:
        def set_bearer(rq: AthenaRequest):
            rq.headers["Authorization"] = f"Bearer {token}" 
            return rq
        self.add_auth = set_bearer
        return self
    def compile(self) -> Callable[[AthenaRequest], AthenaRequest]:
        return self.add_auth

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
    def __init__(self, partial_request_builder: Callable[[RequestBuilder], RequestBuilder]=None, name=None, hook: Callable[[AthenaTrace], None]=None):
        if partial_request_builder is not None:
            self.base_request_apply = partial_request_builder(RequestBuilder()).compile()
        else:
            self.base_request_apply = lambda rq: rq
        self.session = requests.Session()
        self.name = name or ""
        self.hook = hook or (lambda t: None)

    def send(self, method, url, build_request: Callable[[RequestBuilder], RequestBuilder]=None):
        athena_request = self.base_request_apply(AthenaRequest())
        athena_request.url = url
        athena_request.method = method
        if build_request is not None:
            athena_request = build_request(RequestBuilder()).apply(athena_request)

        request = athena_request.to_request()
        prepared_request = request.prepare()

        response = self.session.send(prepared_request, allow_redirects=False, timeout=30)
        trace = AthenaTrace(response)
        self.hook(trace)

        return trace.response

    def get(self, url, build_request: Callable[[RequestBuilder], RequestBuilder]=None):
        return self.send("get", url, build_request)
    def post(self, url, build_request: Callable[[RequestBuilder], RequestBuilder]=None):
        return self.send("post", url, build_request)
    def delete(self, url, build_request: Callable[[RequestBuilder], RequestBuilder]=None):
        return self.send("delete", url, build_request)
    def put(self, url, build_request: Callable[[RequestBuilder], RequestBuilder]=None):
        return self.send("put", url, build_request)

