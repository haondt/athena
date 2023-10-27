# athena

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
    # your code here...
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
    # your code here...
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
