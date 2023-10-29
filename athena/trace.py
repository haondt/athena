import requests, json
from .exceptions import AthenaException
from .json import mark_serializeable, jsonify


@mark_serializeable
class AthenaTrace:
    def __init__(self, response: requests.Response):
        self.response = ResponseTrace(response)
        self.request = RequestTrace(response.request)

        self.elapsed = str(response.elapsed)

    def __str__(self):
        return jsonify(self)

@mark_serializeable
class ResponseTrace:
    def __init__(self, response: requests.Response):
        self.headers = { k:response.headers[k] for k in response.headers.keys() }
        self.raw = response.text
        self.url = response.url
        self.status_code = response.status_code
        self.reason = response.reason

    def __str__(self):
        return jsonify(self)

@mark_serializeable
class RequestTrace:
    def __init__(self, request: requests.PreparedRequest):
        self.method = request.method
        self.url = request.url
        self.headers = { k:request.headers[k] for k in request.headers.keys() }

        self.content_type = None
        if "Content-Type" in request.headers:
            self.content_type = request.headers["Content-Type"]

        if self.content_type == "application/json":
            if isinstance(request.body, bytes):
                self.raw = request.body.decode('utf-8')
            elif isinstance(request.body, str):
                self.raw = request.body
            else:
                self.raw = str(request.body)
        elif self.content_type == "application/x-www-form-urlencoded":
            self.raw = request.body
        elif isinstance(request.body, str):
            self.raw = request.body
        elif request.body is None:
            self.raw = None
        else:
            raise AthenaException(f"unable to handle request body of type {type(request.body)}")

    def __str__(self):
        return jsonify(self)

    def json(self):
        if self.content_type != "application/json":
            raise AthenaException(f"unable to load json, content type is {self.content_type}")
        if not isinstance(self.raw, str):
            raise AthenaException(f"unable to load json, raw body type is {type(self.raw).__name__}")
        return json.loads(self.raw)
