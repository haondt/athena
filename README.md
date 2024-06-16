# athena

[![PYPI - Version](https://img.shields.io/pypi/v/haondt_athena?label=PyPI)](https://pypi.org/project/haondt-athena/)
[![GitHub release (latest by date)](https://img.shields.io/gitlab/v/release/haondt/athena)](https://gitlab.com/haondt/athena/-/releases/permalink/latest)

athena is a file-based rest api client.

```sh
$ pip install haondt-athena
$ athena init
$ cat << EOF > athena/hello.py
from athena.client import Athena
from athena.test import athert

def run(athena: Athena):
    client = athena.client()
    response = client.get('https://example.com')
    athert(response.status_code).equals(200)
EOF
$ athena run hello.py
hello: passed
```

athena provides a lightweight alternative to full-blown api platforms like Postman with a few key advantages:

- You are free to use any text editor you would like as the api client. Lightweight editors like Neovim or VSCode allow for a much thinner client.
- As the workbook is just a collection of plaintext files, you can keep it in the same git repo as the project it is testing.
- Since requests are just python modules, you can script to your hearts content, and leverage external python libraries.

## Installation 

athena can be installed as a pypi package or from source. athena requires python>=3.11.

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

Quickstart guide and API / CLI reference available here: https://haondt.gitlab.io/docs/athena/
