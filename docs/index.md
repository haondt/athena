# Athena

[![PYPI - Version](https://img.shields.io/pypi/v/haondt_athena?label=PyPI)](https://pypi.org/project/haondt-athena/)
[![GitHub release (latest by date)](https://img.shields.io/gitlab/v/release/haondt/athena)](https://gitlab.com/haondt/athena/-/releases/permalink/latest)

athena is a file-based rest api client.

## Motivation

I can store my athena workspaces inside the repo of the project they test. Something I was originally doing with ThunderClient before they changed their payment
model, but even better since I can leverage some python scripting and automation inside my test cases. 
It's also much more lightweight than something like Postman. Since the workbook is just a collection of plaintext files, you can navigate an athena project with
any text editor.



For full documentation visit [mkdocs.org](https://www.mkdocs.org).

## Commands

* `mkdocs new [dir-name]` - Create a new project.
* `mkdocs serve` - Start the live-reloading docs server.
* `mkdocs build` - Build the documentation site.
* `mkdocs -h` - Print help message and exit.

## Project layout

    mkdocs.yml    # The configuration file.
    docs/
        index.md  # The documentation homepage.
        ...       # Other markdown pages, images and other files.

<!-- ::: athena.__main__ -->

