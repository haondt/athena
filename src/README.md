# athena

athena is a file-based rest api client.

# Usage

## Setup

Start by running the init in your project directory.

```sh
python3 -m athena init .
```

Enter this directory, and create a workspace

```sh
cd athena
python3 -m athena create workspace my-workspace
```

Lastly, create a new collection inside the workspace

```sh
python3 -m athena create collection my-collection -w my-workspace
```

## Creating tests

To create a test case, add a python file in the `run` folder of a collection

```sh
vim athena/my-workspace/collections/my-collection/run/hello.py
```

Create a function called `run`, that takes the `Athena` instance as the argument.

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

athena can search the directory for modules to execute. Use `athena run` to start, and provide an argument of the module to run.
This can be a path to the module or to a directory along the module hierarchy. In the latter case, athena will run all the modules
it can find inside that directory.

```sh
# run all the modules inside the api directory
python3 -m athena run /path/to/athena/my-workspace/collections/my-collection/run/api
```

### Module keys

Any command that takes a module path can also take an argument of the form `workspace:collection:module`, and run all the modules that match.
This key will be computed relative to the current working directory, and allows for more precision in determining which modules to run.

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

The workspace and collection parts can contain wild cards. A single period (`.`) in either field will use the current directory.
A single asterisk (`*`) will use all directories.

```sh
# run all modules in "my-workspace" named "hello.py"
python3 -m athena run "my-workspace:*:hello"
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
python3 -m athena run "*:*:**blue"

# run all modules in the collection of the current directory
python3 -m athena run ".:.:**"
```

Internally, asterisks are compiled into the regular expression `[^.]+` and double asterisks are compiled into `.+`.

