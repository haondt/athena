import subprocess, time, os, json
import pytest

@pytest.fixture(scope="module")
def setup_athena(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp('test_tmp')
    subprocess.run(['athena', 'init', tmp_dir], capture_output=True, text=True)
    yield os.path.join(tmp_dir, 'athena')

API_HOST='flask-test-image:5000'

def test_timeout(setup_athena):
    athena_dir = setup_athena

    filename = 'test_timeout.py'
    code = f'''def run(athena):
    athena.client().post('http://{API_HOST}/api/response', lambda r: r
        .body.json({{'duration': 2}})
        .timeout(0.1))'''
    with open(os.path.join(athena_dir, filename), 'w') as f:
        f.write(code)

    start = time.time()
    result = subprocess.run(['athena', 'trace', filename], cwd=athena_dir, capture_output=True, text=True)
    end = time.time()

    assert result.returncode == 0
    trace = json.loads(result.stdout)[0]
    assert trace['success'] == False
    assert 'ReadTimeout' in trace['error']
    duration = end - start
    assert duration < 0.5

def test_param(setup_athena):
    athena_dir = setup_athena

    filename = 'test_param.py'
    code = f'''def run(athena):
    athena.client().get('http://{API_HOST}/api/echo', lambda r: r
        .query('foo', 'bar')
        .query('foo', ['bar', 'baz']))'''
    with open(os.path.join(athena_dir, filename), 'w') as f:
        f.write(code)

    result = subprocess.run(['athena', 'trace', filename], cwd=athena_dir, capture_output=True, text=True)

    assert result.returncode == 0
    trace = json.loads(result.stdout)[0]
    print(trace)
    assert trace['success'] == True
    response = trace['athena_traces'][0]['response']
    response_body = json.loads(response['text'])

    assert response_body['args'] == {'foo': ['bar', 'bar', 'baz']}

