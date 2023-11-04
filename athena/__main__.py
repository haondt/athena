import asyncio
import typer
import sys, os
from typing_extensions import Annotated

from .resource import DEFAULT_ENVIRONMENT_KEY
from . import file
from . import run as athena_run
from . import status as athena_status
from .exceptions import AthenaException
from enum import Enum
from .format import colors, color
from . import display

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
            )] = ""
    ):
    if item is Createables.workspace:
        workspace_path = file.create_workspace(os.getcwd(), name)
        print(f'Created workspace at `{workspace_path}')
    elif item is Createables.collection:
        file.create_collection(os.getcwd(), workspace if workspace != "" else None, name)

def resolve_module_path(path_or_key: str):
    if path_or_key.count(":") == 2:
        current_dir = os.path.normpath(os.getcwd())
        root, workspace, collection = file.find_context(current_dir)
        paths = path_or_key.split(":")
        module = paths[2]
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
            if collection is None:
                raise AthenaException("not inside a module")
            collection_path = os.path.join(root, workspace, "collections", collection)
            relative_path = os.path.relpath(current_dir, collection_path)
            parts = relative_path.split(os.path.sep)
            if parts[0] != "run":
                raise AthenaException("not inside a module")
            module = ".".join(parts[1:])
            if len(module) == 0:
                module = "**"
            else:
                module += ".**"
        return root, workspace, collection, module
    else:
        path_or_key = os.path.abspath(path_or_key)
        if not os.path.exists(path_or_key):
            raise AthenaException(f"no such file or directory: {path_or_key}")
        root, workspace, collection = file.find_context(path_or_key)
        if workspace is not None and collection is not None:
            base_path = os.path.join(root, workspace, "collections", collection)
            rel_path = os.path.relpath(path_or_key, base_path)
            rel_path_parts = rel_path.split(os.path.sep)

            if rel_path == "." or \
                    (len(rel_path_parts) == 1 and rel_path_parts[0] == "run"):
                return root, workspace, collection, "**"

            if not rel_path_parts[0] == "run":
                raise AthenaException("cannot run modules outside of `run` directory")

            module_part = ".".join(rel_path_parts[1:])
            if module_part.endswith(".py"):
                module_part = module_part[:-3]
            else:
                module_part = module_part + ".**"
            return root, workspace, collection, module_part
        return root, workspace or "*", collection or "*", "**"

@app.command()
def run(
        path: Annotated[str, typer.Argument(
            help="Name of module, collection or workspace to run, in the format workspace:collection:path.to.module."
            )],
        environment: Annotated[str, typer.Option(
            help="environment to run tests against. environment must exist in all referenced workspaces",
            )] = DEFAULT_ENVIRONMENT_KEY
        ):
        
    root, workspace, collection, module = resolve_module_path(path)
    modules = file.search_modules(root, workspace, collection, module)
    loop = asyncio.get_event_loop()
    try:
        results = loop.run_until_complete(athena_run.run_modules(root, modules, environment))
        for key, result in results.items():
            print(f"{key}: {result.format_long()}")
    finally:
        loop.close()


@app.command()
def status(
        path: Annotated[str, typer.Argument(
            help="Name of module, collection or workspace to check status of, in the format workspace:collection:module. Each level can be replaced with `.` or `*` to use the one from the current working directory or to search from the root directory.",
            )]="*:*:**"
        ):
    root, workspace, collection, module = resolve_module_path(path)
    modules = file.search_modules(root, workspace, collection, module)
    print("modules:")
    print("\n".join(["  " + i for i in modules.keys()]))
    environments = athena_status.search_environments(root, modules.keys())
    print("environments:")
    print("\n".join(["  " + i for i in environments]))

'''TODO
@app.command()
def inspect(
        path: Annotated[str, typer.Argument(
            help="Name of module, collection or workspace to run, in the format workspace:collection:path.to.module."
            )],
        environment: Annotated[str, typer.Option(
            help="environment to run tests against. environment must exist in all referenced workspaces",
            )] = DEFAULT_ENVIRONMENT_KEY
        ):
    root, workspace, collection, module = resolve_module_path(path)
    modules = file.search_modules(root, workspace, collection, module)
    results = athena_run.run_modules(modules, environment)
    for key, result in results.items():
        print(f"{key}: {jsonify(result.athena_traces)}")
'''

@app.command()
def responses(
        path: Annotated[str, typer.Argument(
            help="Name of module, collection or workspace to run, in the format workspace:collection:path.to.module."
            )],
        environment: Annotated[str, typer.Option(
            help="environment to run tests against. environment must exist in all referenced workspaces",
            )] = DEFAULT_ENVIRONMENT_KEY
        ):
    root, workspace, collection, module = resolve_module_path(path)
    modules = file.search_modules(root, workspace, collection, module)
    loop = asyncio.get_event_loop()
    try:
        results = loop.run_until_complete(athena_run.run_modules(root, modules, environment))
        for _, result in results.items():
            print(f"{display.responses(result)}")
    finally:
        loop.close()

if __name__ == "__main__":
    try:
        app()
    except AthenaException as e:
        sys.stderr.write(f"{color('error:', colors.bold, colors.red)} {type(e).__name__}: {str(e)}\n")
        sys.exit(1)
