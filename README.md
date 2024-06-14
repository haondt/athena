# athena

[![PYPI - Version](https://img.shields.io/pypi/v/haondt_athena?label=PyPI)](https://pypi.org/project/haondt-athena/)
[![GitHub release (latest by date)](https://img.shields.io/gitlab/v/release/haondt/athena)](https://gitlab.com/haondt/athena/-/releases/permalink/latest)

athena is a file-based rest api client.

# table of contents

- [motivation](#motivation)
- [installation](#installation)
- [usage](#usage)
  - [setup](#setup)
  - [creating tests](#creating-tests)
  - [sending requests](#sending-requests)
  - [running tests](#running-tests)
- [additional features](#additional-features)
  - [environments, variables and secrets](#environments-variables-and-secrets)
  - [cache](#cache)
  - [fixtures](#fixtures)
  - [fakes](#fakes)
  - [hooks](#hooks)
  - [async requests](#async-requests)
  - [jsonification](#jsonification)
  - [context](#context)
  - [assertions](#assertions)
- [utilities](#utilities)
  - [import/export](#importexport)
  - [responses](#responses)
  - [watch](#watch)
  - [history](#history)
- [development](#development)

# motivation

I can store my athena workspaces inside the repo of the project they test. Something I was originally doing with ThunderClient before they changed their payment
model, but even better since I can leverage some python scripting and automation inside my test cases. 
It's also much more lightweight than something like Postman. Since the workbook is just a collection of plaintext files, you can navigate an athena project with
any text editor.

# Installation

athena can be installed as a pypi package or from source. athena requires python>=3.11

```sh
# from pypi
python3 -m pip install haondt-athena
# from gitlab
python3 -m pip install haondt-athena --index-url https://gitlab.com/api/v4/projects/57154225/packages/pypi/simple
# from source
git clone https://gitlab.com/haondt/athena.git
python3 -m pip install ./athena
```

# usage

athena can be run as a module, or with the included binary.

```sh
python3 -m athena --help
athena --help
```

## Setup

Start by running the init in your project directory.

```sh
athena init
```

This will create an `athena` directory.

```sh
.
└── athena
    ├── .athena
    ├── .gitignore
    ├── variables.yml
    └── secrets.yml
```


## creating tests

To create a test case, add a python file somewhere inside the athena directory

```sh
vim athena/hello.py
```

In order for athena to run the test, there must be a function named `run` that takes a single argument.
athena will call this function, with an `Athena` instance as the argument.

```python
from athena.client import Athena

def run(athena: Athena):
    ...
```

## sending requests

The injected `Athena` instance provides methods to create and send requests. Start by creating a new `Client`.

```python
def run(athena: Athena):
    client = athena.client()
```

The client can be configured by providing a builder function. The builder will be applied to each request sent by the client.

```python
def run(athena: Athena):
    client = athena.client(lambda builder: builder
        .base_url("http://haondt.com/api/")
        .header("origin", "athena")
        .auth.bearer("some_secret_key"))

```

The client provides method to send restful requests. the requests themselves can also be configured with a builder.

```python
def run(athena: Athena):
    ...
    response = client.put("planets/saturn", lambda builder: builder
        .body.json({
            "diameter": "120 thousand km",
            "density": "687 kg/m^3",
            "distance_from_sun": "1.35 billion km"
        }))
```

The response is a `ResponseTrace`, which contains information about the response

```python
def run(athena: Athena):
    ...
    print(f"status: {response.status_code} {response.reason}")
```

athena can provide more information about the rest of the request with the `trace` method, which will return the `AthenaTrace` for the whole request/response saga.

```python
def run(athena: Athena):
    ...
    trace = athena.trace()
    print(f"request payload: {trace.request.raw}")
    print(f"request time: {trace.elapsed}")
```

## running tests

athena accepts one or more arguments for modules to run. if an argument points to an unrunnable module (not a python file, path to a directory, etc), then it is silently ignored. this allows the usage of glob patterns to run several tests at once.

```sh
# run all the modules inside the api directory
athena run /path/to/athena/api/*
```

# additional features

## environments, variables and secrets

athena will provide variables and secrets to the running method through the `Athena` object.

```python
from athena.client import Athena

def run(athena: Athena):
    password = athena.secret("password")
```

This will reference the `variables.yml` and `secrets.yml` environment files. athena will select all variable or secret files that can be found in any ancestor directory of the module being run. For example, if we are running the following module:

```
./athena/foo/hello.py
```

then athena will look for variables in the following locations:

```
./athena/variables.yml
./athena/foo/variables.yml
```

The format of both the secrets and variables files is a key for the value, and then a key for each environment the value applies to.

**`secrets.yml`**

```yml
password:
  __default__: "foo"
  staging: "foo" 
  production: "InwVAQuKrm0rUHfd"
```

**`variables.yml`**

```yml
username:
  __default__: "bar"
  staging: "bar" 
  production: "athena"
```

By default, athena will use the `__default__` environment, but you can specify one in the `run` command.

```sh
athena run "my-workspace:*:hello.py" --environment staging
```

You can also set the default environment.

```sh
athena set environment staging
```

## cache

athena also provides a basic key (`str`) - value (`str`, `int`, `float`, `bool`) cache. The cache is global and is persisted between runs.

```python
import time
from athena.client import Athena

def refresh_token(athena: Athena):
    if "token" not in athena.cache \
        or "token_exp" not in athena.cache \
        or athena.cache["token_exp"] < time.time():
        athena.cache["token"], athena.cache["token_exp"] = athena.infix.get_token()
    return athena.cache["token"]

def run(athena: Athena):
    token = refresh_token(athena)
    client = athena.infix.client(token)
    client.get("path/to/resource")
```

the cache can be manually cleared

```sh
athena clear cache
```


## fixtures

athena supports adding fixtures using the same heirarchy strategy as the variables and secrets files. any file names `fixture.py` in a directory that is a direct ancestor of the current module will be loaded.

athena will call the fixture method on `Athena.fixture` before running any modules.

`fixture.py`

```python
from athena.client import Fixture, Athena

def fixture(fixture: Fixture):
    def build_client(athena: Athena):
        base_url = athena.variable("base_url")
        api_key = athena.secret("api_key")

        client = athena.client(lambda b: b
            .base_url(base_url)
            .auth.bearer(api_key))
        return client

    fixture.client = build_client
```

`my_module.py`

```python
from athena.client import Athena

def run(athena: Athena):
    client = athena.fixture.client(athena)
    client.post("path/to/resource")
```

In addition to the `fixture` property, athena also provides a special `infix` property, short for "into fixture".
This property is used similarly to `fixture`, but it can only be called with fixtures that are functions. This field
will inject the `Athena` instance into the fixture function as the first argument, and pass along the rest, making for
a useful shorthand.

`my_module.py`

```python
from athena.client import Athena

def run(athena: Athena):
    client = athena.infix.client()
    client.post("path/to/resource")
```

## fakes

athena includes a module called `fakes` that is a thin wrapper / extension around [Faker](https://faker.readthedocs.io/en/master/). This allows you to generate randomized data for requests.

```python
from athena.client import Athena

def run(athena: Athena):
    client = athena.fixture.client(athena)
    client.post("api/planets", lambda r: r
        .body.json({
            'name': athena.fake.first_name()
        })
    )
```

## hooks

athena can run pre-request and post-request hooks at the client or request level.

```python
def run(athena: Athena):
    client = athena.client(lambda b: b
        .hook.before(lambda r: print("I am about to send a request with these headers: ", r.headers))
        .hook.after(lambda r: print("I just received a response with the reason:", r.reason))))
```

## async requests

athena can run modules asynchronously, and can send requests asynchronously with `aiohttp`. To run in async mode, simply change the
`run` function to async. All of the client methods have asynchronous counterparts, and can be run concurrently.

```python
from athena.client import Athena, Client
import asyncio

async def run(athena: Athena):
    client = athena.client()
    tasks =  [client.get_async("https://google.com") for _ in range(10)]
    await asyncio.gather(*tasks)
```



## jsonification

athena provides a `jsonify` tool to json-dump athena objects, like `AthenaTrace`.
Apart from adding an encoder for athena objects, this method will pass-through arguments
like `indent` to `json.dumps`.

```python
from athena.client import Athena, jsonify

def run(athena: Athena):
    athena.client().get("http://haondt.com")
    traces = athena.traces()
    print(jsonify(traces, indent=4))
```


## context

the `context` property provides information about the runtime environment of the module.

```python
from athena.client import Athena

def run(athena: Athena):
    print("current workspace:", athena.context.workspace)
    print("current environment:", athena.context.environment)
```

## assertions

athena comes bundled with a thin wrapper around the `assert` statement called `athert`. This wrapper provides
more informative error messages and a fluent syntax.

```python
from athena.client import Athena, Client
from athena.test import athert

def run(athena: Athena):
    client: Client = athena.infix.build_client()
    response = client.get("path/to/resource")

    athert(response.status_code).equals(200)
```

```sh
$ athena run ./my_module
my_module: failed
    │ File "/home/haondt/projects/my-project/athena/my-workspace/collections/my-collection/run/my_module.py", line 8, in run
    │     athert(response.status_code).equals(200)
    │
    │ AssertionError: expected `200` but found `404`
```

# utilities

## import/export

You can import and export secrets and variables with the `import` and `export` commands.
`export` will print to stdout and `import` will either take the values as an argument or take
the path to a file as an option. These commands will import/export all values for the entire
athena project.

```sh
athena export secrets > secrets.json

athena import secrets -f secrets.json
```

## responses

The `responses` command will run one or more modules and pretty-print information about the responses of
all the requests that were sent during the execution. 

```
$ athena responses get_planets.py

get_planets •
│ execution
│ │ environment: __default__
│ │ Warning: execution failed to complete successfully
│ │ AssertionError: expected `200` but found `401`
│ 
│ timings
│ │ api/planets     ····················· 2.59ms
│ │ planet/Venus                           ·············· 1.64ms
│ 
│ traces
│ │ api/planets
│ │ │ │ GET http://localhost:5000/api/planets
│ │ │ │ 401 UNAUTHORIZED 2.59ms
│ │ │ 
│ │ │ headers
│ │ │ │ Server         | Werkzeug/3.0.0 Python/3.10.12
│ │ │ │ Date           | Fri, 14 Jun 2024 11:09:26 GMT
│ │ │ │ Content-Type   | application/json
│ │ │ │ Content-Length | 39
│ │ │ │ Connection     | close
│ │ │ 
│ │ │ body | application/json [json] 39B
│ │ │ │ 1 {
│ │ │ │ 2   "error": "Authentication failed"
│ │ │ │ 3 }
│ │ │ │ 
│ │ │ 
│ │ 
│ │ planet/Venus
│ │ │ │ GET http://localhost:5000/planet/Venus
│ │ │ │ 200 OK 1.64ms
│ │ │ 
│ │ │ headers
│ │ │ │ Server         | Werkzeug/3.0.0 Python/3.10.12
│ │ │ │ Date           | Fri, 14 Jun 2024 11:09:26 GMT
│ │ │ │ Content-Type   | text/html; charset=utf-8
│ │ │ │ Content-Length | 160
│ │ │ │ Connection     | close
│ │ │ 
│ │ │ body | text/html [html] 160B
│ │ │ │ 1 <html>
│ │ │ │ 2 <head>
│ │ │ │ 3     <title>Venus</title>
│ │ │ │ 4 </head>
│ │ │ │ 5 <body>
│ │ │ │ 6     <h1>Venus</h1>
│ │ │ │ 7     <p>Description: Known for its thick atmosphere</p>
│ │ │ │ 8 </body>
│ │ │ │ 9 </html>
│ │ │ │ 
│ │ │ 
│ │ 
│ 
```

## watch

Watches the given directory for file writes. Any written modules inside the directory will be executed with the `responses` command.

```shell
athena watch .
```

## history

athena maintains a log of execution history in the `.history` file. this history can be viewed with

```sh
athena get history
```

and cleared with

```sh
athena clear history
```

# development

To get started, set up a venv

```sh
python3.11 -m venv venv
. venv/bin/activate
```

and install the dev dependencies

```sh
python3 -m pip install -r dev-requirements.txt
```

athena can be installed in the venv to use in a test project

```sh
cd src
python3 -m pip install .
```
