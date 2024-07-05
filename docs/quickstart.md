# Quickstart

## Installation

athena is available on PyPI and requires Python >= 3.11.

```sh
python3 -m pip install haondt-athena
```

## Setup

Start by running `init` in your project directory.

```sh
athena init
```

This will create an `athena` directory with some files to get you started.

```sh
.
└── athena
    ├── .athena
    ├── .gitignore
    ├── my_module.py
    ├── fixture.py
    ├── variables.yml
    └── secrets.yml
```

## Create a Module

To create a test case, add a python file somewhere inside the athena directory

```sh
cd athena
vim hello.py
```

In order for athena to run the module, there must be a top-level function named `run` that takes a single argument.
athena will call this function, with an `Athena` instance as the argument. The `Athena` instance can be used to instantiate a client.

```python title="hello.py"
from athena.client import Athena

def run(athena: Athena):
    client = athena.client()
    client.get('http://echo.jsontest.com/key/value')
```

## Execute a Module

The `responses` command can be used to run a module and pretty-print the response data

```sh
$ athena responses hello.py
hello •
│ execution
│ │ environment: __default__
│
│ timings
│ │ http://echo...m/key/value    ························ 431ms
│
│ traces
│ │ http://echo.jsontest.com/key/value
│ │ │ │ GET http://echo.jsontest.com/key/value
│ │ │ │ 200 OK 431ms
│ │ │
│ │ │ headers
│ │ │ │ Access-Control-Allow-Origin | *
│ │ │ │ Content-Type                | application/json
│ │ │ │ X-Cloud-Trace-Context       | cfca39362fd31539e246341cda420c14
│ │ │ │ Date                        | Sat, 15 Jun 2024 19:44:54 GMT
│ │ │ │ Server                      | Google Frontend
│ │ │ │ Content-Length              | 17
│ │ │
│ │ │ body | application/json [json] 17B
│ │ │ │ 1 {
│ │ │ │ 2   "key": "value"
│ │ │ │ 3 }
│ │ │ │
│ │ │
│ │
│
```
