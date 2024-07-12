# API


## Module structure

A module must have a top level function named `run`, that receives a single argument. athena will execute this function with an [`Athena`](../client/#athena.client.Athena) instance as the argument.

```python
from athena.client import Athena

def run(athena: Athena):
    client = athena.client()
    client.get('http://echo.jsontest.com/key/value')
```

The function may also be `async`, if an asynchronous context is desired.

```python
from athena.client import Athena

async def run(athena: Athena):
    client = athena.client()
    tasks = [client.get_async("https://google.com") for _ in range(10)]
    await asyncio.gather(*tasks)
```

## Sending requests

### Create a client

The injected `Athena` instance provides methods to create and send requests. Start by creating a new [`Client`](../request/#athena.request.Client).

```python
def run(athena: Athena):
    client = athena.client()
```

The client can be configured by providing a builder function. The builder will be applied to each request sent by the client. The configuration is done through the [`RequestBuilder`](../request/#athena.request.RequestBuilder) interface.

```python
def run(athena: Athena):
    client = athena.client(lambda requestBuilder: requestBuilder
        .base_url("https://www.example.com")
        .auth.bearer(my_token)
    )
```

### Send the request

The client provides methods to send requests, these methods can optionally include a configuration function. The configuration will be applied on top of the client configuration.

```python
def run(athena: Athena):
    client = athena.client(lambda requestBuilder: requestBuilder
        .base_url("https://www.example.com")
        .auth.bearer(my_token)
    )

    client.get('/foo')
    client.post('/bar', lambda r: r
        .body.json({
            'baz': 'qux'
        })
    )
```

### Parse the response

The client methods will return a [`ResponseTrace`](../trace/#athena.trace.ResponseTrace), which contains information about the response.

```python
def run(athena: Athena):
    ...
    response = client.get('/foo')
    print(f'status: {response.status_code} {response.reason}')

```

athena can provide more information about the rest of the request with the `trace` method, which will return the [`AthenaTrace`](../trace/#athena.trace.AthenaTrace) for the whole request/response saga.

```python
def run(athena: Athena):
    ...
    trace = athena.trace()
    print(f"request payload: {trace.request.text}")
    print(f"request time: {trace.elapsed}")
```

## Configuring the request

### Hooks

athena can run pre-request and post-request hooks at the client or request level, using the [`HookStepFactory`](../request/#athena.request.HookStepFactory).

```python
def run(athena: Athena):
    client = athena.client(lambda b: b
        .hook.before(lambda r: print("I am about to send a request with these headers: ", r.headers))
        .hook.after(lambda r: print("I just received a response with the reason:", r.reason))))
```

## Other utilities

### Environments, Variables and Secrets 

athena will provide variables and secrets to the module under test through the `Athena` object.

```python
def run(athena: Athena):
    # will return `None` if no such variable exists
    username = athena.variable.get('username')
    # will throw error if no such secret exists
    password = athena.secret['password']
    # will use default value if no such variable exists
    email = athena.variable.get('email', default='foo@bar.baz')
```

This will reference the `variables.yml` and `secrets.yml` environment files. athena will select all variable or secret files that can be found in any ancestor directory of the module being run (up to the athena root directory). For example, if we are running the following module:

```
./athena/foo/hello.py
```

then athena will look for variables in the following locations:

```
./athena/variables.yml
./athena/foo/variables.yml
```

#### Resource files

The format of both the secrets and variables files is the same, objects are defined as `name.environment: value`.

```yml title='variables.yml'
username:
  __default__: "bar"
  staging: "bar" 
  production: "athena"
```

```yml title='secrets.yml'
password:
  __default__: "foo"
  staging: "foo" 
  production: "InwVAQuKrm0rUHfd"
```

#### Environments

By default, athena will use the `__default__` environment, but you can specify one in the [`run`](../../cli/reference/#run) command.

```sh
athena run ./hello.py --environment staging
```

You can also set the default environment.

```sh
athena set environment staging
```

### Fixtures

athena supports adding fixtures using the same heirarchy strategy as the variables and secrets files. Any file named `fixture.py` in a directory that is a direct ancestor of the current module will be loaded. The fixtures are executed in top-down order, meaning you can access fixtures created in an ancestor directory from fixtures inside a descendant one.

athena will call the fixture method on `Athena.fixture` before running any modules. The fixture attribute is an anonymous object to which fixture methods can assign values or functions to. These values/functions are then available to the test module.

```python title='fixture.py'
from athena.client import Fixture, Athena

def fixture(fixture: Fixture):
    def build_client(athena: Athena):
        base_url = athena.variable["base_url"]
        api_key = athena.secret["api_key"]

        client = athena.client(lambda b: b
            .base_url(base_url)
            .auth.bearer(api_key))
        return client

    fixture.some_value = 'some_value'
    fixture.client = build_client
```

```python title='my_module.py'
from athena.client import Athena

def run(athena: Athena):
    some_value = athena.fixture.some_value
    client = athena.fixture.client(athena)
    client.post("path/to/resource")
```

#### Infix

athena also provides the `infix` attribute, short for "into fixture".
This property is used similarly to `fixture`, but it can only be called with fixtures that are functions. `infix`
will inject the `Athena` instance into the fixture function as the first argument, and pass along the rest, making for
a useful shorthand.

```python title='my_module.py'
from athena.client import Athena

def run(athena: Athena):
    client = athena.infix.client()
    client.post("path/to/resource")
```

### Fake

The [`fake`](../fake/#Fake) attribute is a thin wrapper / extension around [Faker](https://faker.readthedocs.io/en/master/). This allows you to generate randomized data for requests.

```python
from athena.client import Athena

def run(athena: Athena):
    client = athena.infix.client()
    client.post("api/users", lambda r: r
        .body.json({
            'name': athena.fake.first_name()
        })
    )
```

### Caching

athena provides a basic key (`str`) - value (`str`, `int`, `float`, `bool`) cache. The cache is global and is persisted between runs.

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

the cache is persisted in the `.cache` file, and can be cleared by deleting the file or from the cli:

```sh
athena clear cache
```

### Jsonification

athena provides a [`jsonify`](../client/#athena.client.jsonify) tool to json-dump athena objects, like `AthenaTrace`.
Apart from adding an encoder for athena objects, this method will pass-through arguments
like `indent` to `json.dumps`.

```python
from athena.client import Athena, jsonify

def run(athena: Athena):
    athena.client().get("http://haondt.com")
    traces = athena.traces()
    print(jsonify(traces, indent=4))
```

### Context

the `context` ([`Context`](../client/#athena.client.Context)) property provides information about the runtime environment of the module.

```python
from athena.client import Athena

def run(athena: Athena):
    print("current module:", athena.context.module_name)
    print("current environment:", athena.context.environment)
```

### Assertions

athena comes bundled with a thin wrapper around the `assert` statement called [`athert`](../test/#athena.test.athert). This wrapper provides
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


