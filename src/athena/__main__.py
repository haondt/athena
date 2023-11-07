import asyncio
import sys, os
import click
from typing import Tuple, Callable, Dict
from click import version_option

from .run import ExecutionTrace

from . import file
from . import run as athena_run
from . import status as athena_status
from .exceptions import AthenaException
from .format import colors, color
from . import display
from .json import jsonify, dejsonify

@click.group()
@click.version_option()
def athena():
    pass

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
    click.echo(f'Created athena project at: `{athena_path}`')

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
    click.echo(f'Created workspace at `{workspace_path}')

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
    click.echo(f'Created collectio at `{collection_path}`')

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
            module_callback=lambda key, result: click.echo(f"{key}: {result.format_long()}"))

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
    click.echo("modules:")
    click.echo("\n".join(["  " + i for i in modules.keys()]))
    directories = file.list_directories(root)
    environments = athena_status.search_environments(root, list(directories.keys()))
    click.echo("environments:")
    click.echo("\n".join(["  " + i for i in environments]))

@athena.group()
def export():
    pass

@export.command(name='secrets')
def export_secrets():
    current_dir = os.path.normpath(os.getcwd())
    root, _, _ = file.find_context(current_dir)
    directories = file.list_directories(root)
    secrets = athena_status.collect_secrets(root, list(directories.keys()))
    click.echo(jsonify(secrets, reversible=True))

@export.command(name='variables')
def export_variables():
    current_dir = os.path.normpath(os.getcwd())
    root, _, _ = file.find_context(current_dir)
    directories = file.list_directories(root)
    variables = athena_status.collect_variables(root, list(directories.keys()))
    click.echo(jsonify(variables, reversible=True))

@athena.group(name="import")
def athena_import():
    pass

@athena_import.command(name='secrets')
@click.argument('secret_data', type=str, default="")
@click.option('secret_path', '-f', '--file', type=click.Path(
    exists=True,
    dir_okay=False,
    file_okay=True,
    readable=True,
    ), help="secret data file to import")
def athena_import_secrets(secret_data: str, secret_path: str | None):
    """
    Import secrets for the athena project. Will prompt for confirmation.

    SECRET_DATA - secret data to import. Alternatively, a file can be supplied.
    """
    if secret_path is None:
        if secret_data is None:
            raise AthenaException("no data provided")
    else:
        with open(secret_path, "r") as f:
            secret_data = f.read()

    secrets = dejsonify(secret_data, expected_type=athena_status.AggregatedResource)
    current_dir = os.path.normpath(os.getcwd())
    root = file.find_root(current_dir)

    dry_run = athena_status.dry_run_apply_secrets(root, secrets)
    warnings = []
    if len(dry_run.new_workspaces) > 0:
        warning = "Importing will create the following new workspaces:\n"
        warning += "\n".join([f"    {i}" for i in dry_run.new_workspaces])
        warnings.append(warning)
    if len(dry_run.new_collections) > 0:
        warning = "Importing will create the following new collections:\n"
        warning += "\n".join([f"    {i}" for i in dry_run.new_collections])
        warnings.append(warning)
    if len(dry_run.overwritten_values) > 0:
        warning = "Importing will overwrite the following values:\n"
        warning += "\n".join([f"    {i}" for i in dry_run.overwritten_values])
        warnings.append(warning)
    if len(dry_run.new_values) > 0:
        warning = "Importing will create the following values:\n"
        warning += "\n".join([f"    {i}" for i in dry_run.new_values])
        warnings.append(warning)
    if len(warnings) == 0:
        click.echo("input yielded no changes to current project")
        return
    click.echo("Warning: \n" + "\n".join(warnings))
    response = input(f"Continue? (y/N): ")
    if response.lower() not in ["y", "yes"]:
        click.echo("secret import cancelled.")
        return
    athena_status.apply_secrets(root, secrets)
    click.echo("Secrets imported.")

@athena_import.command(name='variables')
@click.argument('variable_data', type=str, default="")
@click.option('variable_path', '-f', '--file', type=click.Path(
    exists=True,
    dir_okay=False,
    file_okay=True,
    readable=True,
    ), help="variable data file to import")
def athena_import_variables(variable_data: str, variable_path: str | None):
    """
    Import variables for the athena project. Will prompt for confirmation.

    VARIABLE_DATA - variable data to import. Alternatively, a file can be supplied.
    """
    if variable_path is None:
        if variable_data is None:
            raise AthenaException("no data provided")
    else:
        with open(variable_path, "r") as f:
            variable_data = f.read()

    variables = dejsonify(variable_data, expected_type=athena_status.AggregatedResource)
    current_dir = os.path.normpath(os.getcwd())
    root = file.find_root(current_dir)

    dry_run = athena_status.dry_run_apply_variables(root, variables)
    warnings = []
    if len(dry_run.new_workspaces) > 0:
        warning = "Importing will create the following new workspaces:\n"
        warning += "\n".join([f"    {i}" for i in dry_run.new_workspaces])
        warnings.append(warning)
    if len(dry_run.new_collections) > 0:
        warning = "Importing will create the following new collections:\n"
        warning += "\n".join([f"    {i}" for i in dry_run.new_collections])
        warnings.append(warning)
    if len(dry_run.overwritten_values) > 0:
        warning = "Importing will overwrite the following values:\n"
        warning += "\n".join([f"    {i}" for i in dry_run.overwritten_values])
        warnings.append(warning)
    if len(dry_run.new_values) > 0:
        warning = "Importing will create the following values:\n"
        warning += "\n".join([f"    {i}" for i in dry_run.new_values])
        warnings.append(warning)
    if len(warnings) == 0:
        click.echo("input yielded no changes to current project")
        return
    click.echo("Warning: \n" + "\n".join(warnings))
    response = input(f"Continue? (y/N): ")
    if response.lower() not in ["y", "yes"]:
        click.echo("variable import cancelled.")
        return
    athena_status.apply_variables(root, variables)
    click.echo("Variables imported.")

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
            module_callback=lambda _, result: click.echo(f"{display.responses(result)}"))

def main():
    try:
        athena()
    except AthenaException as e:
        sys.stderr.write(f"{color('error:', colors.bold, colors.red)} {type(e).__name__}: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
