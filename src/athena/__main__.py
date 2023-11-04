import asyncio
import sys, os
import click
from typing import Tuple, Callable, Dict

from .run import ExecutionTrace

from . import file
from . import run as athena_run
from . import status as athena_status
from .exceptions import AthenaException
from .format import colors, color
from . import display

athena = click.Group()

@athena.command()
@click.argument('path', type=click.Path(
    exists=True,
    dir_okay=True,
    file_okay=False,
    writable=True
    ))
def init(path: str):
    """
    Initializes an athena project at PATH/athena
    """
    athena_path = file.init(path)
    print(f'Created athena project at: `{athena_path}`')

@athena.group()
def create():
    pass

@create.command(name="workspace")
@click.argument('name', type=str)
def create_workspace(name: str):
    """
    Creates a workspace inside the current athena project

    NAME - name of workspace to create
    """
    workspace_path = file.create_workspace(os.getcwd(), name)
    print(f'Created workspace at `{workspace_path}')

@create.command(name="collection")
@click.argument('name', type=str)
@click.option('-w', '--workspace', type=str,
    help="Parent workspace of collection."
)
def create_collection(name: str, workspace: str):
    """
    Creates a collection inside the current athena project

    Will created collection inside WORKSPACE if provided, otherwise
    try to use the workspace in the current working directory.
    """
    collection_path = file.create_collection(os.getcwd(), workspace if workspace != "" else None, name)
    print(f'Created collectio at `{collection_path}`')

def resolve_module_path(path_or_key: str) -> Tuple[str, str, str, str]:
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

def run_modules_and(
        path_or_key: str,
        environment: str | None=None,
        module_callback: Callable[[str, ExecutionTrace], None] | None=None,
        final_callback: Callable[[Dict[str, ExecutionTrace]], None] | None=None
        ):
    root, workspace, collection, module = resolve_module_path(path_or_key)
    modules = file.search_modules(root, workspace, collection, module)
    loop = asyncio.get_event_loop()
    try:
        results = loop.run_until_complete(athena_run.run_modules(root, modules, environment, module_callback))
        if final_callback is not None:
            final_callback(results)
    finally:
        loop.close()


@athena.command()
@click.argument('path_or_key', type=str)
@click.option('-e', '--environment', type=str, help="environment to run tests against", default=None)
def run(path_or_key: str, environment: str | None):
    """
    Run one or more modules and print the output.
    
    PATH_OR_KEY - Name of module, collection or workspace to run. Can be provided as a module key, e.g. workspace:collection:path.to.module.
    or as a path to a file or directory.
    """
    run_modules_and(
            path_or_key,
            environment=environment,
            module_callback=lambda key, result: print(f"{key}: {result.format_long()}"))

@athena.command()
@click.argument('path_or_key', type=str)
def status(path_or_key: str):
    """
    Print information about this athena project.
    
    PATH_OR_KEY - Name of module, collection or workspace to run. Can be provided as a module key, e.g. workspace:collection:path.to.module.
    or as a path to a file or directory.
    """
    root, workspace, collection, module = resolve_module_path(path_or_key)
    modules = file.search_modules(root, workspace, collection, module)
    print("modules:")
    print("\n".join(["  " + i for i in modules.keys()]))
    environments = athena_status.search_environments(root, modules.keys())
    print("environments:")
    print("\n".join(["  " + i for i in environments]))

@athena.group()
def export():
    pass

@export.command(name='secrets')
def export_secrets():
    print("TODO!")


@athena.command()
@click.argument('path_or_key', type=str)
@click.option('-e', '--environment', type=str, help="environment to run tests against", default=None)
def responses(path_or_key: str, environment: str | None):
    """
    Run one or more modules and print the response traces.
    
    PATH_OR_KEY - Name of module, collection or workspace to run. Can be provided as a module key, e.g. workspace:collection:path.to.module.
    or as a path to a file or directory.
    """
    run_modules_and(
            path_or_key,
            environment=environment,
            module_callback=lambda _, result: print(f"{display.responses(result)}"))

if __name__ == "__main__":
    try:
        athena()
    except AthenaException as e:
        sys.stderr.write(f"{color('error:', colors.bold, colors.red)} {type(e).__name__}: {str(e)}\n")
        sys.exit(1)
