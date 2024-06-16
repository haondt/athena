# athena

[![PYPI - Version](https://img.shields.io/pypi/v/haondt_athena?label=PyPI)](https://pypi.org/project/haondt-athena/)
[![GitHub release (latest by date)](https://img.shields.io/gitlab/v/release/haondt/athena)](https://gitlab.com/haondt/athena/-/releases/permalink/latest)

athena is a file-based rest api client.

# Utilities

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
