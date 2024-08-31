import subprocess, time, os, json, requests
import pytest

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
        server_process = subprocess.Popen(['athena', 'serve', filename], cwd=athena_dir, stderr=subprocess.PIPE)
        time.sleep(0.5)

        if server_process.poll() is not None:
            _, stderr = server_process.communicate()
            raise ContextualError("Server failed to start", { 'stderr': stderr.decode('utf-8') })

    yield _start_server

    if server_process:
        server_process.terminate()
        server_process.wait()

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

    assert excinfo.value.message == "Server failed to start"
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


