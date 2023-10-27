import requests, json
from .exceptions import AthenaException
import collections
from typing import Mapping

def serialize_trace(trace, indent=False):
    if indent:
        return json.dumps(trace, default=lambda t: t.__dict__, indent=4)
    return json.dumps(trace, default=lambda t: t.__dict__)

class AthenaTrace:
    def __init__(self, response: requests.Response):
        self.response = ResponseTrace(response)
        self.request = RequestTrace(response.request)

        self.elapsed = str(response.elapsed)

class ResponseTrace:
    def __init__(self, response: requests.Response):
        self.headers = { k:response.headers[k] for k in response.headers.keys() }
        self.raw = response.text
        self.url = response.url
        self.status_code = response.status_code
        self.reason = response.reason

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
            elif isinstance(request.body, string):
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

    def json(self):
        if self.content_type == "application/json":
            return json.loads(self.raw)
        raise AthenaException(f"unable to load json, content type is {self.content_type}")
