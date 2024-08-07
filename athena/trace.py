from datetime import timedelta
import requests, json, aiohttp, re
from .exceptions import AthenaException
from .athena_json import serializeable, jsonify
from typing import Callable

class AioHttpRequestContainer:
    def __init__(self, method, url, kwargs):
        self.method = method
        self.url = url
        self.kwargs = kwargs

class LinkedRequest(aiohttp.ClientRequest):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    async def send(self, conn) -> aiohttp.ClientResponse:
        resp = await super().send(conn)
        assert isinstance(resp, LinkedResponse)
        resp.athena_get_request = lambda: self
        return resp


class LinkedResponse(aiohttp.ClientResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.athena_get_request: Callable[[], LinkedRequest | None] = lambda: None 


@serializeable
class AthenaTrace:
    """Trace of a single request/response saga.

    Attributes:
        id (str): The unique identifier for the trace.
        name (str): The name of the trace.
        request (RequestTrace): Trace of the request.
        response (ResponseTrace): Trace of the response.
        start (float): The start time of the request in seconds.
        end (float): The end time of the request in seconds.
        elapsed (float): The duration of the request in seconds.
    """
    def __init__(self,
        id: str,
        name: str,
        request: requests.PreparedRequest | aiohttp.ClientRequest,
        response: requests.Response | aiohttp.ClientResponse,
        start: float, 
        end: float,
        request_text: str | None=None,
        response_text: str | None=None,
        warnings: list[str] | None=None
    ):

        self.id = id
        self.response = ResponseTrace(response, response_text)
        self.request = RequestTrace(request, request_text)
        self.name = name
        self.warnings = warnings or []


        # timestamps are in seconds
        self.elapsed = str(timedelta(seconds=end-start))
        self.start = start
        self.end = end

    def __str__(self):
        return jsonify(self)

@serializeable
class ResponseTrace:
    """Trace of the response component.

    Attributes:
        headers (dict): The headers of the response.
        url (str): The URL of the response.
        reason (str): The reason phrase of the response.
        content_type (str | None): The content type of the response.
        status_code (int): The status code of the response.
        text (str): The text content of the response.

    """
    def __init__(self,
        response: requests.Response | aiohttp.ClientResponse,
        response_text: str | None
    ):
        self.headers = { k:response.headers[k] for k in response.headers.keys() }
        self.url = str(response.url)
        self.reason = response.reason
        self.content_type: str | None = self.headers.get(aiohttp.hdrs.CONTENT_TYPE, None)
        if self.content_type is not None:
            self.content_type = self.content_type.split(";")[0]

        if isinstance(response, requests.Response):
            self.status_code = response.status_code
        else:
            self.status_code = response.status

        # just gonna assume for now that it's always text
        if response_text is not None:
            self.text = response_text
        else:
            if isinstance(response, requests.Response):
                self.text = response.text
            else:
                raise ValueError("response text must be provided with async response")

    def __str__(self):
        return jsonify(self)

    def json(self):
        """
        Parses the response text as JSON and returns the result.

        Returns:
            dict: The parsed JSON content of the response text.
        """
        return json.loads(self.text)

@serializeable
class RequestTrace:
    """Trace of the request component.

    Attributes:
        method (str): The HTTP method of the request.
        url (str): The URL of the request.
        headers (dict): The headers of the request.
        content_type (str | None): The content type of the request.
        text (str): The text content of the request.

    """
    json_re = re.compile(r"^application/(?:[\w.+-]+?\+)?json")
    def __init__(self, 
        request: requests.PreparedRequest | aiohttp.ClientRequest,
        request_text: str | None=None
    ):
        self.method = request.method
        self.url = str(request.url)
        self.headers = { k:v for k, v in request.headers.items() }
        self.content_type: str | None = self.headers.get(aiohttp.hdrs.CONTENT_TYPE, None)

        if request_text is not None:
            self.text = request_text
        else:
            if self.content_type is not None \
                and (RequestTrace.json_re.match(self.content_type) or self.content_type == "application/x-www-form-urlencoded") \
                and isinstance(request.body, (str, bytes)):
                if isinstance(request.body, bytes):
                    self.text = request.body.decode('utf-8')
                elif isinstance(request.body, str):
                    self.text = request.body
            elif isinstance(request.body, str):
                self.text = request.body
            #elif isinstance(request.body, BytesPayload) and isinstance(request, aiohttp.ClientRequest) and request.body.encoding is not None:
            elif isinstance(request.body, aiohttp.Payload) and isinstance(request, aiohttp.ClientRequest) and request.body.size == 0:
                self.text = ""
            elif request.body is None:
                self.text = ""
            else:
                raise AthenaException(f"unable to handle request body of type {type(request.body)} with content type {self.content_type}")

    def __str__(self):
        return jsonify(self)

