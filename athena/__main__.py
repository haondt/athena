import typer
import sys, os
from typing_extensions import Annotated
from . import file
from . import run as athena_run
from . import status as athena_status
from .exceptions import AthenaException
from enum import Enum

app = typer.Typer()

@app.command()
def init(
        path: Annotated[str, typer.Argument(help="Path to initialize athena in")] = "."
    ):
    athena_path = file.init(path)
    print(f'Created athena project at: `{athena_path}`')


class Createables(str, Enum):
    workspace = "workspace"
    collection = "collection"

@app.command()
def create(
        item: Annotated[Createables, typer.Argument(
            help="Type of item",
            case_sensitive=False
            )],
        name: Annotated[str, typer.Option(
            help="Name of item",
            prompt=True
            )],
        workspace: Annotated[str, typer.Option(
            help="Workspace to create new collection inside of",
            )] = None
    ):
    if item is Createables.workspace:
        workspace_path = file.create_workspace(os.getcwd(), name)
        print(f'Created workspace at `{workspace_path}')
    elif item is Createables.collection:
        file.create_collection(os.getcwd(), workspace, name)

@app.command()
def run(
        path: Annotated[str, typer.Argument(
            help="Name of module, collection or workspace to run, in the format workspace:collection:module. Each level can be replaced with `.` or `*` to use the one from the current working directory or to search from the root directory.",
            )],
        environment: Annotated[str, typer.Option(
            help="environment to run tests against. environment must exist in all referenced workspaces",
            )] = None
        ):
    root, workspace, collection = file.find_context(os.getcwd())
    paths = path.split(":")
    if len(paths) != 3:
        raise AthenaException("invalid format")
    if paths[0] == ".":
        if workspace is None:
            raise AthenaException("not inside a workspace")
    else:
        workspace = paths[0]
    if paths[1] == ".":
        if collection is None:
            raise AthenaException("not inside a collection")
    else:
        collection = paths[1]
    if paths[2] == ".":
        raise AthenaException("not inside a module")

    modules = file.search_modules(root, workspace, collection, paths[2])
    athena_run.run_modules(modules, environment)

class StatusCommand(str, Enum):
    environments = "environments"

@app.command()
def status(
        subcommand: Annotated[StatusCommand, typer.Argument(
            help="attribute to check status of",
            case_sensitive=False
            )],
        path: Annotated[str, typer.Argument(
            help="Name of module, collection or workspace to check status of, in the format workspace:collection:module. Each level can be replaced with `.` or `*` to use the one from the current working directory or to search from the root directory.",
            )]
        ):
    root, workspace, collection = file.find_context(os.getcwd())
    paths = path.split(":")
    if len(paths) != 3:
        raise AthenaException("invalid format")
    if paths[0] == ".":
        if workspace is None:
            raise AthenaException("not inside a workspace")
    else:
        workspace = paths[0]
    if paths[1] == ".":
        if collection is None:
            raise AthenaException("not inside a collection")
    else:
        collection = paths[1]
    if paths[2] == ".":
        raise AthenaException("not inside a module")

    modules = file.search_modules(root, workspace, collection, paths[2])
    print("modules:")
    print("\n".join(["  " + i for i in modules.keys()]))
    environments = athena_status.search_environments(root, modules.keys())
    print("environments:")
    print("\n".join(["  " + i for i in environments]))

if __name__ == "__main__":
    try:
        app()
    except AthenaException as e:
        error_text = "\033[1;31merror:\033[0m"
        sys.stderr.write(f"{error_text} {type(e).__name__}: {str(e)}\n")
        sys.exit(1)