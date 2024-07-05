# athena

[![PYPI - Version](https://img.shields.io/pypi/v/haondt_athena?label=PyPI)](https://pypi.org/project/haondt-athena/)
[![GitHub release (latest by date)](https://img.shields.io/gitlab/v/release/haondt/athena)](https://gitlab.com/haondt/athena/-/releases/permalink/latest)

athena is a file-based rest api client.

```sh
$ pip install haondt-athena
$ athena init
$ cat << EOF > athena/hello.py
from athena.client import Athena

def run(athena: Athena):
    client = athena.client()
    client.get('http://echo.jsontest.com/key/value')
EOF
$ athena responses athena/hello.py
hello •
│ execution
│ │ environment: __default__
│
│ timings
│ │ http://echo...m/key/value    ························ 470ms
│
│ traces
│ │ http://echo.jsontest.com/key/value
│ │ │ │ GET http://echo.jsontest.com/key/value
│ │ │ │ 200 OK 470ms
│ │ │
│ │ │ response
│ │ │ │ headers
│ │ │ │ │ Access-Control-Allow-Origin | *
│ │ │ │ │ Content-Type                | application/json
│ │ │ │ │ X-Cloud-Trace-Context       | 35b9c247eaaa4175c1949b97dd13548a
│ │ │ │ │ Date                        | Fri, 05 Jul 2024 20:33:16 GMT
│ │ │ │ │ Server                      | Google Frontend
│ │ │ │ │ Content-Length              | 17
│ │ │ │
│ │ │ │ body | application/json [json] 17B
│ │ │ │ │ 1 {
│ │ │ │ │ 2   "key": "value"
│ │ │ │ │ 3 }
│ │ │ │ │
│ │ │ │
│ │ │
│ │
│
```

athena provides a lightweight alternative to full-blown api platforms like Postman with a few key advantages:

- You are free to use any text editor you would like as the api client. Lightweight editors like Neovim or VSCode allow for a much thinner client.
- As the workbook is just a collection of plaintext files, you can keep it in the same git repo as the project it is testing.
- Since requests are just python modules, you can script to your hearts content, and leverage external python libraries.

## Installation 

athena can be installed as a pypi package or from source. athena requires python>=3.11.

```sh
# from pypi
python3 -m pip install haondt-athena

# from gitlab
python3 -m pip install haondt-athena --index-url https://gitlab.com/api/v4/projects/57154225/packages/pypi/simple

# from source
git clone https://gitlab.com/haondt/athena.git
python3 -m pip install .
```

## Usage

Quickstart guide and API / CLI reference available here: https://haondt.gitlab.io/docs/athena/


## Development

### Running Tests

#### How to run the E2E tests

- build docker images for the api echo server and for the test runner images

```sh
./tests/e2e/build_dockerfile.sh
```

- start both images to run the tests

```sh
./tests/e2e/run_tests.sh
```
