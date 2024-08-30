from athena.client import Athena
from athena.server import ServerBuilder, RouteBuilder
import time


HTTP_METHODS = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH']

def serve(builder: ServerBuilder):
    builder.add_server(lambda c: c
        .host('0.0.0.0')
        .port(4040)
        .send(HTTP_METHODS, '/api/echo', echo)
        .post('/api/response', response)
    )

#     builder.add_server(lambda c: c
#         .get('/foo/bar', lambda b: b.status(200))
#         .get('/baz/qux', auth)
#     )
#
# def auth(b: RouteBuilder):
#     if b.request.headers.get('X-API-KEY') == 'foobar':
#         return b.status(200)
#     return b.status(401)

# def run(athena: Athena):
#     client = athena.client(lambda b: b.base_url(''))
#     client.send('GET', '/foo/bar', lambda b: b
#         .query('a', 'b')
#         .body.form())


def echo(builder: RouteBuilder):
    request_data = {
        'timestamp': time.time(),
        'method': builder.request.method,
        'query': builder.request.query.to_dict(flat=False),
        'form': builder.request.body.form.to_dict(flat=False),
        'body': str(builder.request.body.data),
        'headers': dict(builder.request.headers)
    }

    builder.body.json(request_data)
    return builder


#
def response(builder: RouteBuilder):
    response_data = builder.request.body.json
    assert response_data is not None

    headers = response_data.get('headers', {})
    body = response_data.get('body', '')
    status_code = response_data.get('status_code', 200)
    duration = response_data.get('duration', 0)

    if duration > 0:
        time.sleep(duration)

    builder.body.text(body)
    builder.status(status_code)
    for k, v in headers.items():
        builder.header(k, v)

    return builder

