# Athena

[![PYPI - Version](https://img.shields.io/pypi/v/haondt_athena?label=PyPI)](https://pypi.org/project/haondt-athena/)
[![GitHub release (latest by date)](https://img.shields.io/gitlab/v/release/haondt/athena)](https://gitlab.com/haondt/athena/-/releases/permalink/latest)

athena is a file-based rest api client.

## Motivation

I can store my athena workspaces inside the repo of the project they test. Something I was originally doing with ThunderClient before they changed their payment
model, but even better since I can leverage some python scripting and automation inside my test cases. 

Since the workbook is just a few files in a directory, it is inherently much more lightweight than Postman or other similar api clients. All you need to run athena is a terminal, and (optionally) your text editor of choice.

## Installation

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

## Usage

See the [quickstart guide](./quickstart) to get things rolling. Then check out the [api usage guide](./api/usage) for how to create executable modules, and see the [cli usage guide](./cli/usage) for how to run them.
