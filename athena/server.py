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

from .exceptions import AthenaException

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)

class ServerRequestBody:
    """Accessor for the request body"""
    def __init__(self, request: Request):
        self._request = request

    @property
    def form(self) -> MultiDictProxy:
        """form payload"""
        return MultiDictProxy(MultiDict(self._request.form.items()))

    @property
    def files(self):
        """files payload"""
        return self._request.files
        
    @property
    def data(self) -> bytes:
        """raw bytes payload"""
        return self._request.data

    @property
    def json(self):
        """json payload"""
        return self._request.json

class ServerRequest:
    """Accessor for the request sent to the server

    Args:
        body (ServerRequestBody): accessor for the request body
    """
    def __init__(self, request: Request):
        self._request = request
        self.body = ServerRequestBody(request)

    @property
    def query(self) -> MultiDictProxy:
        """request query data"""
        return MultiDictProxy(MultiDict(list(self._request.args.items(multi=True))))

    @property
    def cookies(self):
        """request cookie jar"""
        return self._request.cookies

    @property
    def headers(self) -> CIMultiDictProxy:
        """request headers"""
        return CIMultiDictProxy(CIMultiDict(self._request.headers.items()))

    @property
    def url(self):
        """request url"""
        return self._request.url

    @property
    def method(self):
        """request method (verb)"""
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

    def data(self, mimetype: str, payload: bytes):
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
    """Builder for configuring the response body
    """
    def __init__(self, parent: RouteBuilder):
        self._parent = parent

    def json(self, payload) -> RouteBuilder:
        """set the json payload"""
        self._parent._response.json(payload)
        return self._parent

    def text(self, payload) -> RouteBuilder:
        """set the text payload"""
        self._parent._response.text(payload)
        return self._parent

    def html(self, payload) -> RouteBuilder:
        """set the html payload"""
        self._parent._response.html(payload)
        return self._parent

    def data(self, mimetype: str, payload: bytes) -> RouteBuilder:
        """set the raw payload"""
        self._parent._response.data(mimetype, payload)
        return self._parent

class RouteBuilder:
    """Builder for configuring an http route

        Args:
            request (ServerRequest): accessor for the incoming http request
            body (ResponseBodyBuilder): builder for configuring the response body
    """
    def __init__(self, request: ServerRequest):
        self.request = request
        self._response = ServerResponse()
        self.body = ResponseBodyBuilder(self)

    def status(self, status_code: int):
        """Set the response status code"""
        self._response.status_code(status_code)
        return self

    def header(self, header_key, header_value):
        """Add a header to the response."""
        self._response.header(header_key, header_value)
        return self

    def _complete(self):
        return self._response._to_flask_response()

class ServerConfigurator():
    """Builder for creating a server configuration
    """
    def __init__(self):
        self._routes: list[tuple[tuple[str, ...], str, Callable[[RouteBuilder], RouteBuilder]]] = []
        self._host: str | None = None
        self._port: int | None = None

    def host(self, host: str):
        """Set the host for the server.

        Args:
            host (str): host the server is running on. Set to 0.0.0.0 to make the server publicly available.
        """
        self._host = host
        return self

    def port(self, port: int):
        """Set the port for the server.

        Args:
            port (int): port the server is running on.
        """
        self._port = port
        return self

    def send(self, method: str | list[str], path: str, build_route: Callable[[RouteBuilder], RouteBuilder]):
        """
        Add an http request handler.

        Args:
            method (str): HTTP method ('GET', 'POST', etc).
            path (str): endpoint for the request
            build_route (Callable[[RouteBuilder], RouteBuilder]):
                Function to build or modify the request.
        """
        if path[0] != '/':
            path = f'/{path}'

        if isinstance(method, str):
            method_tuple = (method,)
        else:
            method_tuple = tuple(method)
        self._routes.append((method_tuple, path, build_route))
        return self

    def get(self, path, build_route: Callable[[RouteBuilder], RouteBuilder]):
        """
        Add an http get request handler.

        Args:
            path (str): endpoint for the request
            build_route (Callable[[RouteBuilder], RouteBuilder]):
                Function to build or modify the request.
        """
        self.send('GET', path, build_route)
        return self
    def post(self, path, build_route: Callable[[RouteBuilder], RouteBuilder]):
        """
        Add an http post request handler.

        Args:
            path (str): endpoint for the request
            build_route (Callable[[RouteBuilder], RouteBuilder]):
                Function to build or modify the request.
        """
        self.send('POST', path, build_route)
        return self
    def put(self, path, build_route: Callable[[RouteBuilder], RouteBuilder]):
        """
        Add an http put request handler.

        Args:
            path (str): endpoint for the request
            build_route (Callable[[RouteBuilder], RouteBuilder]):
                Function to build or modify the request.
        """
        self.send('PUT', path, build_route)
        return self
    def delete(self, path, build_route: Callable[[RouteBuilder], RouteBuilder]):
        """
        Add an http delete request handler.

        Args:
            path (str): endpoint for the request
            build_route (Callable[[RouteBuilder], RouteBuilder]):
                Function to build or modify the request.
        """
        self.send('DELETE', path, build_route)
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
    """Builder for configuring the server
    """
    def __init__(self):
        self._configurators = []
        self._claimed_ports = set()

    def add_server(self, configure: Callable[[ServerConfigurator], ServerConfigurator]):
        """Add a new server configuration
        
        Args:
            configure (Callable[[ServerConfigurator], ServerConfigurator]): configure the server
        """
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
