# athena

athena is a file-based rest api client.

# Purpose

I can store my athena workspaces inside the repo of the project they test. Something I was originally doing with ThunderClient before they changed their payment
model, but even better since I can leverage some python scripting and automation inside my test cases. 
It's also much more lightweight than something like Postman. Since the workbook is just a collection of plaintext files, you can navigate an athena directory with
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
    └── .athena
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
    client = athena.client(lambda builder: builder # see `AuthBuilder`
        .base_url("http://haondt.com/api/")
        .header("origin", "athena")
        # the authentication can also be configured with an AuthBuilder
        .auth(lambda auth_builder: auth_builder.bearer("some_secret_key")))

```

The client can be used to send api requests, and can also be configured with a builder.

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

The response is a `ResponseTrace`, which contains info about the response

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
You can substitute values with `.` for the current directory, or `*` for any directory.

```sh
# run all modules in "my-workspace" named "hello.py"
python3 -m athena run "my-workspace:*:hello.py"
```

## Environments, Variables and Secrets

athena will provide variables and secrets to the running method through the `Athena` object.

```python
from athena.client import Athena

def run(athena: Athena):
    password = athena.get_secret("password")
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
