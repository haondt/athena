from __future__ import annotations
import sys
import traceback
from flask.wrappers import Request
from flask import Flask, Response
import flask, flask.logging
import json
from flask import request
from flask import jsonify as flask_jsonify
import os

from multidict import CIMultiDict, CIMultiDictProxy, MultiDict, MultiDictProxy

from .athena_json import jsonify
from . import module
from typing import Callable
import uuid
import logging

from athena.exceptions import AthenaException

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)

class ServerRequestBody:
    def __init__(self, request: Request):
        self._request = request

    @property
    def form(self) -> MultiDictProxy:
        return MultiDictProxy(MultiDict(self._request.form.items()))

    @property
    def files(self):
        return self._request.files
        
    @property
    def data(self):
        return self._request.data

    @property
    def json(self):
        return self._request.json

class ServerRequest:
    def __init__(self, request: Request):
        self._request = request
        self.body = ServerRequestBody(request)

    @property
    def query(self) -> MultiDictProxy:
        return MultiDictProxy(MultiDict(list(self._request.args.items(multi=True))))

    @property
    def cookies(self):
        return self._request.cookies

    @property
    def headers(self) -> CIMultiDictProxy:
        return CIMultiDictProxy(CIMultiDict(self._request.headers.items()))

    @property
    def url(self):
        return self._request.url

    @property
    def method(self):
        return self._request.method


class ServerResponse:
    def __init__(self):
        self._actions: list[Callable[[Response]]] = []

    def status_code(self, code: int):
        def set_code(r):
            r.status_code = code

        self._actions.append(set_code)

    def json(self, payload):
        def set_json(r: Response):
            r.data = jsonify(payload)
            r.mimetype = 'application/json'
        self._actions.append(set_json)

    def text(self, payload):
        def set_text(r: Response):
            r.data = payload
            r.mimetype = 'text/plain'
        self._actions.append(set_text)

    def html(self, payload):
        def set_html(r: Response):
            r.data = payload
            r.mimetype = 'text/html'
        self._actions.append(set_html)

    def data(self, mimetype: str, payload: str):
        def set_data(r: Response):
            r.data = payload
            r.mimetype = mimetype
        self._actions.append(set_data)

    def header(self, header_key, header_value):
        def add_header(r: Response):
            r.headers[header_key] = header_value
        self._actions.append(add_header)

    def _to_flask_response(self):
        response = Response()
        for action in self._actions:
            action(response)
        return response

class ResponseBodyBuilder:
    def __init__(self, parent: RouteBuilder):
        self._parent = parent

    def json(self, payload) -> RouteBuilder:
        self._parent._response.json(payload)
        return self._parent

    def text(self, payload) -> RouteBuilder:
        self._parent._response.text(payload)
        return self._parent

    def html(self, payload) -> RouteBuilder:
        self._parent._response.html(payload)
        return self._parent

    def __call__(self, mimetype, payload) -> RouteBuilder:
        self._parent._response.data(mimetype, payload)
        return self._parent

class RouteBuilder:
    def __init__(self, 
                 request: ServerRequest):
        self.request = request
        self._response = ServerResponse()
        self.body = ResponseBodyBuilder(self)

    def status(self, status_code: int):
        self._response.status_code(status_code)
        return self

    def header(self, header_key, header_value):
        self._response.header(header_key, header_value)
        return self

    def _complete(self):
        return self._response._to_flask_response()


class ServerConfigurator():
    def __init__(self):
        self._routes: list[tuple[tuple[str, ...], str, Callable[[RouteBuilder], RouteBuilder]]] = []
        self._host: str | None = None
        self._port: int | None = None

    def host(self, host: str):
        self._host = host
        return self

    def port(self, port: int):
        self._port = port
        return self

    def send(self, method: str | list[str], url: str, build_route: Callable[[RouteBuilder], RouteBuilder]):
        if url[0] != '/':
            url = f'/{url}'

        if isinstance(method, str):
            method_tuple = (method,)
        else:
            method_tuple = tuple(method)
        self._routes.append((method_tuple, url, build_route))
        return self

    def get(self, url, build_route: Callable[[RouteBuilder], RouteBuilder]):
        self.send('GET', url, build_route)
        return self
    def post(self, url, build_route: Callable[[RouteBuilder], RouteBuilder]):
        self.send('POST', url, build_route)
        return self
    def put(self, url, build_route: Callable[[RouteBuilder], RouteBuilder]):
        self.send('PUT', url, build_route)
        return self
    def delete(self, url, build_route: Callable[[RouteBuilder], RouteBuilder]):
        self.send('DELETE', url, build_route)
        return self

    def _build(self) -> Flask:
        def create_route_handler(func):
            def handler():
                builder = RouteBuilder(ServerRequest(request))
                try:
                    return func(builder)._complete()
                except:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    response = flask_jsonify({
                        'error': exc_type.__name__ if exc_type is not None else None,
                        'message': str(exc_value),
                        'stacktrace': ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                    })
                    response.status_code = 500
                    return response
            return handler
        app = Flask(__name__)
        for methods, url, func in self._routes:
            app.route(url, methods=methods, endpoint=str(uuid.uuid4()))(create_route_handler(func))

        return app

class ServerBuilder():
    def __init__(self):
        self._configurators = []
        self._claimed_ports = set()

    def add_server(self, configure: Callable[[ServerConfigurator], ServerConfigurator]):
        configurator = configure(ServerConfigurator())
        if configurator._port is not None:
            if configurator._port in self._claimed_ports:
                raise AthenaException(f'Multiple servers are trying to claim port {configurator._port}')
            self._claimed_ports.add(configurator._port)
        self._configurators.append(configurator)
        return self

    def _build(self):
        available_port = 5000
        for configurator in self._configurators:
            if configurator._port is not None:
                continue

            while available_port in self._claimed_ports:
                available_port += 1
            configurator.port(available_port)
            self._claimed_ports.add(available_port)
            available_port += 1

        start_functions = []
        for configurator in self._configurators:
            def start_function(cfg):
                server = cfg._build()
                def after_request(response):
                    _logger.info(f'[{request.host}] [{request.method}] {request.path} {response.status}')
                    return response
                server.after_request(after_request)

                server.run(port=cfg._port, host=cfg._host, debug=False)
            start_functions.append((start_function, (configurator,)))

        return start_functions



def execute_module(builder: ServerBuilder, module_path) -> ServerBuilder:
    module_dir = os.path.dirname(module_path)
    module.execute_module(module_dir, "server", "serve", (builder,))
    return builder
