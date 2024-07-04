# CLI

## Creating a new project

The only thing athena needs to run is a file with the name `.athena`. You can create this file manually, or you can call [`init`](../reference#init) to create this file along with a couple optional files.

```sh
$ pwd
/home/haondt
$ athena init
Created athena project at: `/home/haondt/athena`
$ tree -a athena
athena
├── .athena
├── .gitignore
├── secrets.yml
└── variables.yml

0 directories, 4 files
```

## Running modules

The main way to run a test is with the [`run`](../reference#run) command.

```sh
athena run my_module.py
```

If the module executes without errors, the output will reflect this.

```sh
my_module: passed
```

If the module fails to complete, the output will display the errors.

```sh
my_module: failed
    │ File "/home/haondt/example/athena/my_module.py", line 23, in run
    │     raise Exception("I failed :(")
    │
    │ Exception: I failed :(
```

## Running modules without additional processing

athena can also run a module as if it is just executing a python script wtih  the [`exec`](../reference#exec) command.

```sh
athena exec my_module.py
```

### Specifying modules

Any number of files can be passed to the `run` (and similar) commands. If the file is not runnable (it is supposed to be ignored, it is not a python file, etc), the `run` command will silently ignore it. This enables you to glob modules.

```sh
athena run ./foo/*
athena run **/*
```

### Tracing requests

athena provides an easy way to trace the response data from any requests made in a module using the [`responses`](../reference#responses) command. This command will execute a module and for all requests made during the execution of the module, it will pretty-print the response data.

```python title="traceme.py"
from athena.client import Athena

def run(athena: Athena):
    client = athena.client()
    client.get('http://echo.jsontest.com/key/value')
    client.get('http://echo.jsontest.com/foo/bar')
```

```sh
$ athena responses traceme.py
traceme •
│ execution
│ │ environment: __default__
│
│ timings
│ │ http://echo...m/key/value    ·················· 186ms
│ │ http://echo...com/foo/bar                     ······· 70.9ms
│
│ traces
│ │ http://echo.jsontest.com/key/value
│ │ │ │ GET http://echo.jsontest.com/key/value
│ │ │ │ 200 OK 186ms
│ │ │
│ │ │ headers
│ │ │ │ Access-Control-Allow-Origin | *
│ │ │ │ Content-Type                | application/json
│ │ │ │ X-Cloud-Trace-Context       | 5b2294de4ceb12f2ceab1c17067728fc
│ │ │ │ Date                        | Sat, 15 Jun 2024 21:34:15 GMT
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
│ │ http://echo.jsontest.com/foo/bar
│ │ │ │ GET http://echo.jsontest.com/foo/bar
│ │ │ │ 200 OK 70.9ms
│ │ │
│ │ │ headers
│ │ │ │ Access-Control-Allow-Origin | *
│ │ │ │ Content-Type                | application/json
│ │ │ │ X-Cloud-Trace-Context       | 075af8912d5bb5087f4d2a5645aac3a7
│ │ │ │ Date                        | Sat, 15 Jun 2024 21:34:15 GMT
│ │ │ │ Server                      | Google Frontend
│ │ │ │ Content-Length              | 15
│ │ │
│ │ │ body | application/json [json] 15B
│ │ │ │ 1 {
│ │ │ │ 2   "foo": "bar"
│ │ │ │ 3 }
│ │ │ │
│ │ │
│ │
│
```

The [`trace`](../reference#trace) command can also be used to just print out the raw exceution trace of a module.

```sh
$ athena trace traceme.py | jq .
```

### Watching a Directory

The [`watch`](../reference#watch) command can be used to create a long-running thread that will watch a directory for changes. If a (runnable) module is written to inside that directory, the `responses` command will be called on it.

```sh
athena watch .
```

`responses` is the default command to use, but an alternative command can be supplied.

```sh
athena watch -c run .
```

This command will also use a pooled http client session where possible. 

## Application state

There are some commands for configuring the state of the athena project.

### Cache

You can clear the cache with [`clear cache`](../reference#cache).

```sh
athena clear cache
```

### Environment

The [`environment`](../reference#environment) commands can be used to configure the default environment.

```sh
athena get environment
athena set environment staging
athena clear environment
```

### History

athena maintains a log of execution traces in the `.history` file. this history can be viewed with [`get history`](../reference#history).

```sh
athena get history
```

and can be cleared in a similar manner

```sh
athena clear history
```
