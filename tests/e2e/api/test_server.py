import subprocess, time, os, json, requests, signal
import pytest
import logging
_logger = logging.getLogger(__name__)


class ContextualError(RuntimeError):
    def __init__(self, message, context):
        super().__init__(message)
        self.message = message
        self.context = context

@pytest.fixture(scope="module")
def setup_athena(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp('test_tmp')
    subprocess.run(['athena', 'init', tmp_dir], capture_output=True, text=True)
    yield os.path.join(tmp_dir, 'athena')

@pytest.fixture
def start_server(setup_athena):
    server_process = None
    athena_dir = setup_athena
    def _start_server(code):
        nonlocal server_process
        filename = 'server.py'
        with open(os.path.join(athena_dir, filename), 'w') as f:
            f.write(code)
        server_process = subprocess.Popen(['athena', 'serve', filename], cwd=athena_dir, stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=False)
        time.sleep(0.5)

        if server_process.poll() is not None:
            _, stderr = server_process.communicate()
            raise ContextualError(f"Server failed to start: {stderr.decode('utf-8')}", { 'stderr': stderr.decode('utf-8') })
        _logger.info(f'started server with pid {server_process.pid}')

    yield _start_server

    if server_process:
        _logger.info(f'cleaning up server with pid {server_process.pid}')
        server_process.send_signal(signal.SIGINT)
        server_process.wait()
        time.sleep(0.5)

def test_request_form(start_server):
    code = f'''def serve(builder):
    builder.add_server(lambda c: c
        .host('0.0.0.0')
        .port(5001)
        .post('test', lambda r: r
            .body.json(r.request.body.form)
        )
    )'''

    start_server(code)

    response = requests.post('http://localhost:5001/test', data={'hello': 'world!'})
    assert response.status_code == 200
    assert response.json() == [['hello', 'world!']]

def test_request_data(start_server):
    code = f'''def serve(builder):
    builder.add_server(lambda c: c
        .host('0.0.0.0')
        .port(5001)
        .post('test', lambda r: r
            .body.json({{'data': r.request.body.data.decode('utf-8')}})
        )
    )'''

    start_server(code)

    response = requests.post('http://localhost:5001/test', data='hello, world!')
    assert response.status_code == 200
    assert response.json() == {"data": "hello, world!"}

def test_request_json(start_server):
    code = f'''def serve(builder):
    builder.add_server(lambda c: c
        .host('0.0.0.0')
        .port(5001)
        .post('test', lambda r: r
            .body.json(r.request.body.json)
        )
    )'''

    start_server(code)

    response = requests.post('http://localhost:5001/test', json={'foo':'bar'})
    assert response.status_code == 200
    assert response.json() == {"foo": "bar"}

def test_request_properties(start_server):
    code = f'''def serve(builder):
    builder.add_server(lambda c: c
        .host('0.0.0.0')
        .port(5001)
        .post('test', lambda r: r
            .body.json({{
                'query': r.request.query,
                'headers': r.request.headers,
                'url': r.request.url,
                'method': r.request.method
            }})
        )
    )'''

    start_server(code)

    response = requests.post('http://localhost:5001/test?foo=bar&foo=baz&some=value', headers={'X-Test-Header': 'header value'})
    assert response.status_code == 200
    response_json = response.json()
    assert any([k.lower() == 'x-test-header' and v == 'header value' for k, v in  response_json['headers']])
    assert any([k.lower() == 'foo' and v == 'bar' for k, v in response_json['query']])
    assert any([k.lower() == 'foo' and v == 'baz' for k, v in response_json['query']])
    assert any([k.lower() == 'some' and v == 'value' for k, v in response_json['query']])
    assert response_json['url'] == 'http://localhost:5001/test?foo=bar&foo=baz&some=value'
    assert response_json['method'] == 'POST'

def test_json(start_server):
    code = f'''def serve(builder):
    builder.add_server(lambda c: c
        .host('0.0.0.0')
        .port(5001)
        .post('test', lambda r: r
            .body.json({{ 'hello': 'world!' }})
        )
    )'''

    start_server(code)

    response = requests.post('http://localhost:5001/test')
    assert response.status_code == 200
    assert response.json() == { 'hello': 'world!' }

def test_data(start_server):
    code = f'''def serve(builder):
    builder.add_server(lambda c: c
        .host('0.0.0.0')
        .port(5001)
        .post('test', lambda r: r
            .body.data('foo/bar', 'hello!'.encode('utf-8'))
        )
    )'''

    start_server(code)

    response = requests.post('http://localhost:5001/test')
    assert response.status_code == 200
    assert response.content.decode('utf-8') == 'hello!'
    assert response.headers['Content-Type'].split(';')[0].strip() == 'foo/bar'

def test_html(start_server):
    code = f'''def serve(builder):
    builder.add_server(lambda c: c
        .host('0.0.0.0')
        .port(5001)
        .post('test', lambda r: r
            .body.html('<bold>Hello!</bold>')
        )
    )'''

    start_server(code)

    response = requests.post('http://localhost:5001/test')
    assert response.status_code == 200
    assert response.headers['Content-Type'].split(';')[0].strip() == 'text/html'
    assert response.text == '<bold>Hello!</bold>'

def test_text(start_server):
    code = f'''def serve(builder):
    builder.add_server(lambda c: c
        .host('0.0.0.0')
        .port(5001)
        .post('test', lambda r: r
            .body.text('Hello!')
        )
    )'''

    start_server(code)

    response = requests.post('http://localhost:5001/test')
    assert response.status_code == 200
    assert response.headers['Content-Type'].split(';')[0].strip() == 'text/plain'
    assert response.text == 'Hello!'

def test_status_and_headers(start_server):
    code = f'''def serve(builder):
    builder.add_server(lambda c: c
        .host('0.0.0.0')
        .port(5001)
        .get('test', lambda r: r
            .status(201)
            .header('foo', 'bar')
            .header('baz', 'qux')
        )
    )'''

    start_server(code)

    response = requests.get('http://localhost:5001/test')
    assert response.status_code == 201
    assert response.headers['foo'] == 'bar'
    assert response.headers['baz'] == 'qux'
    
def test_verbs(start_server):
    code = f'''def serve(builder):
    builder.add_server(lambda c: c
        .host('0.0.0.0')
        .port(5001)
        .get('test', lambda r: r
            .body.text('get')
        )
        .post('test', lambda r: r
            .body.text('post')
        )
        .put('test', lambda r: r
            .body.text('put')
        )
        .delete('test', lambda r: r
            .body.text('delete')
        )
        .send('PATCH', 'test', lambda r: r
            .body.text('patch')
        )
        .send(['GET', 'POST'], 'test2', lambda r: r
            .body.text('test2')
        )
    )'''

    start_server(code)

    response = requests.post('http://localhost:5001/test')
    assert response.status_code == 200
    assert response.text == 'post'

    response = requests.get('http://localhost:5001/test')
    assert response.status_code == 200
    assert response.text == 'get'

    response = requests.put('http://localhost:5001/test')
    assert response.status_code == 200
    assert response.text == 'put'

    response = requests.delete('http://localhost:5001/test')
    assert response.status_code == 200
    assert response.text == 'delete'

    response = requests.patch('http://localhost:5001/test')
    assert response.status_code == 200
    assert response.text == 'patch'

    response = requests.post('http://localhost:5001/test2')
    assert response.status_code == 200
    assert response.text == 'test2'

    response = requests.get('http://localhost:5001/test2')
    assert response.status_code == 200
    assert response.text == 'test2'


def test_port_conflict(start_server):
    code = f'''def serve(builder):
    builder.add_server(lambda c: c
        .host('0.0.0.0')
        .port(5001)
        .post('test', lambda r: r
            .body.json({{ 'hello': 'world!' }})
        )
    )
    builder.add_server(lambda c: c
        .host('0.0.0.0')
        .port(5001)
        .post('test', lambda r: r
            .body.json({{ 'goodbye': 'world!' }})
        )
    )'''

    with pytest.raises(ContextualError) as excinfo:
        start_server(code)

    assert excinfo.value.message.startswith("Server failed to start")
    assert 'Multiple servers are trying to claim port 5001' in excinfo.value.context['stderr']

def test_multiple_servers(start_server):
    code = f'''def serve(builder):
    builder.add_server(lambda c: c
        .host('0.0.0.0')
        .port(5001)
        .post('test', lambda r: r
            .body.json({{ 'hello': 'world!' }})
        )
    )
    builder.add_server(lambda c: c
        .host('0.0.0.0')
        .port(5002)
        .post('test', lambda r: r
            .body.json({{ 'goodbye': 'world!' }})
        )
    )'''

    start_server(code)

    response = requests.post('http://localhost:5001/test')
    assert response.status_code == 200
    assert response.json() == { 'hello': 'world!' }

    response = requests.post('http://localhost:5002/test')
    assert response.status_code == 200
    assert response.json() == { 'goodbye': 'world!' }


