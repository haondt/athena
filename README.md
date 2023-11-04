# athena

athena is a file-based rest api client.

# Purpose

I can store my athena workspaces inside the repo of the project they test. Something I was originally doing with ThunderClient before they changed their payment
model, but even better since I can leverage some python scripting and automation inside my test cases. 
It's also much more lightweight than something like Postman. Since the workbook is just a collection of plaintext files, you can navigate an athena project with
any text editor.

# Usage

## Setup
Start by running the init in your project directory.

```sh
python3 -m athena init
```

This will create an `athena` directory.

```sh
.
└── athena
    ├── .athena
    └── .gitignore
```

Enter this directory, and create a workspace

```sh
cd athena
python3 -m athena create workspace --name my-workspace
```

This will create a directory for the workspace and set up some environment files.

```sh
.
└── athena
    ├── .athena
    └── my-workspace
        ├── collections
        ├── secrets.yml
        ├── variables.yml
        ├── readme.md
        ├── fixture.py
        └── run
```

Lastly, create a new collection inside the workspace

```sh
python3 -m athena create collection --name my-collection --workspace my-workspace
```

This will add a new collection to the collections directory.

```sh
.
└── athena
    ├── .athena
    └── my-workspace
        ├── collections
        │   └── my-collection
        │       ├── secrets.yml
        │       ├── variables.yml
        │       ├── fixture.py
        │       ├── readme.md
        │       └── run
        ├── secrets.yml
        ├── variables.yml
        ├── readme.md
        └── run
```

## Creating tests

To create a test case, add a python file in the `run` folder of a collection

```sh
vim athena/my-workspace/collections/my-collection/run/hello.py
```

In order for athena to run the method, there must be a function named `run` that takes a single argument.
athena will call this function, with an `Athena` instance as the argument.

```python
from athena.client import Athena

def run(athena: Athena):
    ...
```

## Sending requests

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
        # the authentication can also be configured with a builder
        .auth(lambda auth_builder: auth_builder.bearer("some_secret_key")))

```

The client can be used to send api requests. The requets themselves can also be configured with a builder.

```python
def run(athena: Athena):
    ...
    response = client.put("planets/saturn", lambda builder: builder
        .json({
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
    trace = athena.trace(response)
    print(f"request payload: {trace.request.raw}")
    print(f"request time: {trace.elapsed}")
```

## Running tests

athena can search the directory for modules to execute. Use `athena run` to start.
This command will take an argument in the form of `workspace:collection:module`, and run all the modules that match.


```sh
# run all modules in "my-workspace" named "hello.py"
python3 -m athena run "my-workspace:*:hello"
```

For any module in a collection `run` folder, the directory path relative to the `run` folder will make up the module name. 
For example, given the following files:

```
athena/my-workspace/collections/my-collection/run/red.py
athena/my-workspace/collections/my-collection/run/green.py
athena/my-workspace/collections/my-collection/run/toast/blue.py
athena/my-workspace/collections/my-second-collection/run/red.py
```

You would have the following module keys:

```
my-workspace:my-collection:red
my-workspace:my-collection:green
my-workspace:my-collection:toast.blue
my-workspace:my-second-collection:red
```

The module key parameter can contain wild cards. A single period (`.`) in any field will use the current directory.
A single asterisk (`*`) will use all directories.

```sh
# run all modules in "my-workspace" named "hello.py"
python3 -m athena run "my-workspace:*:hello.py"

# run all modules in the collection of the current directory
python3 -m athena run ".:.:*"
```

For the module name, asterisks can be used to denote "any module/directory", and double asterisks (`**`) can be used to denote any subdirectory.

```sh
# runs all files
python3 -m athena run "*:*:**"

# runs red.py and green.py
python3 -m athena run "*:*:*"

# runs only blue.py
python3 -m athena run "*:*:*.*"
python3 -m athena run "*:*:toast.*"
python3 -m athena run "*:*:**.blue.py"
```

Internally, asterisks are compiled into the regular expression `[^.]+` and double asterisks are compiled into `.+`.

## Environments, Variables and Secrets

athena will provide variables and secrets to the running method through the `Athena` object.

```python
from athena.client import Athena

def run(athena: Athena):
    password = athena.secret("password")
```

This will reference the `variables.yml` and `secrets.yml` environment files. For a given module,
athena will first check in the collection variables, and if the variable or secret is not present there,
it will check in the workspace variables. The structure for the secret and variable files are the same,
with the exception of a different root element. For each entry in the file, a value is given for each
environment, as well as a default for when the environment is not listed or not given.

**`secrets.yml`**

```yml
secrets:
  password:
    __default__: "foo"
    staging: "foo" 
    production: "InwVAQuKrm0rUHfd"
```

**`variables.yml`**

```yml
variables:
  username:
    __default__: "bar"
    staging: "bar" 
    production: "athena"
```

By default, athena will use the `__default__` environment, but you can specify one in the `run` command


```sh
python3 -m athena run "my-workspace:*:hello.py" --environment staging
```

You can see which environments are referenced by 1 or more variables with the `status` command,
which takes a module mask argument as well.

```sh
python3 -m athena status environments "my-workspace:*:hello.py"
```

## Cache

athena also provides a basic key (`str`) - value (`str`, `int`, `float`, `bool`) cache. The cache is global and is persisted between runs.

```python
from athena.client import Athena, time

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


## Fixtures

athena supports adding fixtures at the workspace and collection level. In both of these directories is a file called `fixture.py` with the following (default) contents:

```python
from athena.client import Fixture

def fixture(fixture: Fixture):
    pass
```

athena will call the fixture method on `Athena.fixture` before running any modules. With this you can do configuration at the collection / workspace level before running a module.

`fixture.py`

```python
from athena.client import Fixture, Athena

def fixture(fixture: Fixture):
    def build_client(athena: Athena):
        base_url = athena.variable("base_url")
        api_key = athena.secret("api_key")

        client = athena.client(lambda b: b
            .base_url(base_url)
            .auth(lambda a: a.bearer(api_key)))
        return client

    fixture.client = build_client
```

`my-module.py`

```python
from athena.client import Athena

def run(athena: Athena):
    client = athena.fixture.client(athena)
    client.post("path/to/resource")
```

## Hooks

athena can run pre-request and post-request hooks at the client or request level.

```python
def run(athena: Athena):
    client = athena.client(lambda b: b
        .hook(lambda h: h
            .before(lambda r: print("I am about to send a request with these headers: ", r.headers))
            .after(lambda r: print("I just received a response with the reason:", r.reason))))
```

## Async Requests

athena can run modules asynchronously, and can send requests asynchronously with `aiohttp`. To run in async mode, simply change the
`run` function to async. All of the client methods have asynchronous counterparts, and can be run concurrently.

```python
from athena.client import Athena, Client, jsonify
import asyncio

async def run(athena: Athena):
    client = athena.client()
    tasks =  [client.get_async("https://google.com") for _ in range(10)]
    await aysncio.gather(*tasks)
```

## Utilities

### Executable

**status**

You can check the available modules and environments with the `status` command

```sh
# check for all modules and environments
python3 -m athena status

# filter to current collection
python3 -m athena status ".:.:**"
```

### Imported

**jsonify**

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

**infix**

In addition to the `fixture` property, athena also provides a special `infix` property, short for "into fixture".
This property is used similarly to `fixture`, but it can only be called with fixtures that are functions. This field
will inject the `Athena` instance into the fixture function as the first argument, and pass along the rest, making for
a useful shorthand.

`fixture.py`

```python
from athena.client import Fixture, Athena

def fixture(fixture: Fixture):
    def build_client(athena: Athena, flavor: str):
        ...
    fixture.client = build_client
```

`my-module.py`

```python
from athena.client import Athena

def run(athena: Athena):
    # these are equivalent function calls
    client = athena.fixture.client(athena, "vanilla")
    client = athena.infix.client("vanilla")
```

**context**

the `context` property provides information about the runtime environment of the module.

```python
from athena.client import Athena

def run(athena: Athena):
    print("current workspace:", athena.context.workspace)
    print("current environment:", athena.context.environment)
```

**assertions**

athena comes bundled with a small wrapper around the `assert` statement called `athert`. This wrapper provides
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
$ python3 -m athena run "*:*:my_module"
my-workspace:my-collection:my_module: failed
    │ File "/home/haondt/projects/my-project/athena/my-workspace/collections/my-collection/run/my_module.py", line 8, in run
    │     athert(response.status_code).equals(200)
    │
    │ AssertionError: expected `200` but found `404`
```

# Development

To get started, set up a venv

```sh
python3 -m venv venv
. venv/bin/activate
```

and install athena

```sh
python3 -m pip install athena
```
