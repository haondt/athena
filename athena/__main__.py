import asyncio
import sys, os
import click
import logging
from typing import Callable

from .defaults import DEFAULT_FIXTURE_FILE_CONTENTS, DEFAULT_MODULE_FILE_CONTENTS, DEFAULT_SECRET_FILE_CONTENTS, DEFAULT_VARIABLE_FILE_CONTENTS

from .client import AthenaSession

from .resource import DEFAULT_ENVIRONMENT_KEY, create_sample_resource_file

from .run import ExecutionTrace

from . import file
from . import cache
from . import history
from . import state as athena_state
from . import run as athena_run
from . import status as athena_status
from .exceptions import AthenaException, QuietException
from .format import colors, color
from . import display
from .athena_json import jsonify, dejsonify
from .watch import watch_async as athena_watch_async, EVENT_TYPE_MODIFIED

LOG_TEMPLATE = '[%(levelname)s] %(name)s: %(message)s'
logging.basicConfig(format=LOG_TEMPLATE, level=100)
_logger = logging.getLogger(__name__)

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
    ), required=False)
@click.option('-b', '--bare', is_flag=True, help='initialize project without example files')
def init(path: str | None, bare: bool):
    """
    Initializes an athena project at PATH/athena
    """
    root = file.init(path or os.getcwd(), bare)
    state = athena_state.init()
    athena_state.save(root, state)

    if not bare:
        create_sample_resource_file(os.path.join(root, 'variables.yml'), DEFAULT_VARIABLE_FILE_CONTENTS)
        create_sample_resource_file(os.path.join(root, 'secrets.yml'), DEFAULT_SECRET_FILE_CONTENTS)
        with open(os.path.join(root, 'my_module.py'), 'w') as f:
            f.write(DEFAULT_MODULE_FILE_CONTENTS)
        with open(os.path.join(root, 'fixture.py'), 'w') as f:
            f.write(DEFAULT_FIXTURE_FILE_CONTENTS)

    click.echo(f'Created athena project at: `{root}`')

@athena.group()
def get():
    """
    get information about athena
    """
    pass

def internal_get_environment(path: str | None):
    path = path or os.getcwd()
    root = file.find_root(path)
    state = athena_state.load(root)
    return state.environment

@get.command(name='environment')
@click.option('-p', '--path', type=str, help="path to athena directory", default=None)
def get_environment(path: str | None):
    """
    Gets the default environment
    """
    environment = internal_get_environment(path)
    click.echo(environment)

@get.command(name='history')
@click.option('-p', '--path', type=str, help="path to athena directory", default=None)
def get_history(path: str | None):
    """
    Gets the default environment
    """
    path = path or os.getcwd()
    root = file.find_root(path)
    click.echo(history.get(root))

@athena.group(name='set')
def set_command():
    """
    set information about athena
    """
    pass

@set_command.command(name='environment')
@click.option('-p', '--path', type=str, help="path to athena directory", default=None)
@click.argument('environment', type=str)
def set_environment(path: str | None, environment: str):
    """
    Sets the default environment
    """
    path = path or os.getcwd()
    root = file.find_root(path)
    state = athena_state.load(root)
    state.environment = environment
    athena_state.save(root, state)


@athena.group()
def clear():
    """
    clear information about athena
    """
    pass

@clear.command(name='environment')
@click.option('-p', '--path', type=str, help="path to athena directory", default=None)
def clear_environment(path: str | None):
    """
    Clears the default environment
    """
    path = path or os.getcwd()
    root = file.find_root(path)
    state = athena_state.load(root)
    state.environment = DEFAULT_ENVIRONMENT_KEY
    athena_state.save(root, state)

@clear.command(name='history')
@click.option('-p', '--path', type=str, help="path to athena directory", default=None)
def clear_history(path: str | None):
    """
    Empties the history file
    """
    path = path or os.getcwd()
    root = file.find_root(path)
    history.clear(root)

@clear.command(name='cache')
@click.option('-p', '--path', type=str, help="path to athena directory", default=None)
def clear_cache(path: str | None):
    """
    Empties the cache file
    """
    path = path or os.getcwd()
    root = file.find_root(path)
    cache.clear(root)

def run_modules_and(
        paths: list[str],
        force_environment: str | None=None,
        module_callback: Callable[[str, ExecutionTrace], None] | None=None,
        final_callback: Callable[[dict[str, ExecutionTrace]], None] | None=None,
        loop: asyncio.AbstractEventLoop | None = None,
        ):
    paths = [os.path.abspath(p) for p in paths]
    if (logging.INFO >= logging.root.level):
        ignored_paths = []
        selected_paths = []
        for path in paths:
            if file.is_athena_module(path):
                selected_paths.append(path)
            else:
                ignored_paths.append(path)
        paths_string = '\n'.join(ignored_paths)
        _logger.info(f'ignoring the following paths:\n{paths_string}')
        paths = selected_paths
    else:
        paths = [p for p in paths if file.is_athena_module(p)]

    module_paths_by_root = {}
    for path in paths:
        if not os.path.exists(path):
            raise AthenaException(f"no such file or directory: {path}")
        root = file.find_root(path)
        if root not in module_paths_by_root:
            module_paths_by_root[root] = set()
        if path not in module_paths_by_root[root]:
            module_paths_by_root[root].add(path)

    for root, modules in module_paths_by_root.items():
        loop = loop or asyncio.get_event_loop()
        try:
            environment = force_environment or internal_get_environment(root)
            results = loop.run_until_complete(athena_run.run_modules(root, modules, environment, module_callback))
            if final_callback is not None:
                final_callback(results)
        finally:
            loop.close()


@athena.command()
@click.argument('paths', type=str, nargs=-1)
@click.option('-v', '--verbose', is_flag=True, help='increase verbosity of output')
@click.option('-e', '--environment', type=str, help="environment to run tests against", default=None)
def run(paths: list[str], environment: str | None, verbose: bool):
    """
    Run one or more modules and indicated whether they pass or fail.
    
    PATH - Path to module(s) to run.
    """
    if (verbose):
        logging.root.setLevel(logging.INFO)

    run_modules_and(
            paths,
            force_environment=environment,
            module_callback=lambda module_name, result: click.echo(f"{module_name}: {result.format_long()}"))

@athena.command()
@click.argument('paths', type=str, nargs=-1)
@click.option('-e', '--environment', type=str, help="environment to run tests against", default=None)
def exec(paths: list[str], environment: str | None):
    """
    Execute one or more modules without any additional processing of output.
    
    PATH - Path to module(s) to run.
    """
    run_modules_and(
            paths,
            force_environment=environment,
            module_callback=lambda _, __: None)


@athena.command()
@click.argument('path', type=str, required=False)
def status(path: str | None):
    """
    Print information about this athena project.
    
    PATH - Path to file or directory of modules to watch.
    """

    path = path or os.getcwd()
    root = file.find_root(path)

    modules = file.search_modules(root)
    secrets = file.search_secrets(root)
    variables = file.search_variables(root)
    environments = athena_status.search_environments(root)

    click.echo(f"root: {root}")
    click.echo("modules:")
    click.echo("\n".join(["  " + i for i in modules]))
    click.echo("secret files:")
    click.echo("\n".join(["  " + i for i in secrets]))
    click.echo("variable files:")
    click.echo("\n".join(["  " + i for i in variables]))
    click.echo("environments:")
    click.echo("\n".join(["  " + i for i in environments]))
    click.echo(f"default environment: {internal_get_environment(root)}")

@athena.group()
def export():
    """
    Export secrets or variables
    """
    pass

@export.command(name='secrets')
@click.argument('path', type=str, required=False)
def export_secrets(path: str | None):
    """
    Export all secrets in the athena project

    PATH - Path to athena project
    """
    path = path or os.getcwd()
    root = file.find_root(path)
    secrets = athena_status.collect_secrets(root)
    click.echo(jsonify(secrets, reversible=True))

@export.command(name='variables')
@click.argument('path', type=str, required=False)
def export_variables(path: str | None):
    """
    Export all variables in the athena project

    PATH - Path to athena project
    """
    path = path or os.getcwd()
    root = file.find_root(path)
    variables = athena_status.collect_variables(root)
    click.echo(jsonify(variables, reversible=True))

@athena.group(name="import")
def athena_import():
    """
    Import secrets or variables
    """
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
    raise AthenaException('Not implemeneted')
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
    raise AthenaException('Not implemeneted')
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
@click.argument('path', type=str, required=False)
@click.option('-v', '--verbose', is_flag=True, help='increase verbosity of output')
@click.option('-e', '--environment', type=str, help="environment to use for execution", default=None)
@click.option('-c', '--command', type=click.Choice(['requests', 'responses', 'traces', 'run', 'exec']), help="command to run on changed module", default="responses")
@click.option('-p', '--plain', is_flag=True, help="format output as plain json")
def watch(path: str | None, environment: str | None, command: str, verbose: bool, plain: bool):
    """
    Watch the given path for changes, and execute the given command on the changed file.

    PATH - Path to file or directory of modules to watch.
    """
    
    if plain and command not in ['responses', 'requests', 'traces']:
        click.echo('to use --plain, command must be one of (requests, responses, traces)', err=True)
        raise QuietException()

    if (verbose):
        logging.root.setLevel(logging.INFO)

    path = path or os.getcwd()
    root = file.find_root(path)

    def module_callback(module_name: str, result: ExecutionTrace):
        match command:
            case 'responses':
                if plain:
                    click.echo(f"{display.trace_plain(result, include_requests=False, include_responses=True)}")
                else:
                    click.echo(f"{display.trace(result, include_requests=False, include_responses=True)}")
            case 'requests':
                if plain:
                    click.echo(f"{display.trace_plain(result, include_requests=True, include_responses=False)}")
                else:
                    click.echo(f"{display.trace(result, include_requests=True, include_responses=False)}")
            case 'traces':
                if plain:
                    click.echo(f"{display.trace_plain(result, include_requests=True, include_responses=True)}")
                else:
                    click.echo(f"{display.trace(result, include_requests=True, include_responses=True)}")
            case 'run':
                click.echo(f"{module_name}: {result.format_long()}")
            case 'exec':
                pass

    async def on_change_async(changed_path: str, session: AthenaSession):
        env = environment or internal_get_environment(root)
        if not file.is_athena_module(changed_path):
            return
        await athena_run.run_modules(root, [changed_path], env, module_callback, session)

    async def inner():
        async with AthenaSession() as session:
            # retrieve the loop from the main thread
            loop = asyncio.get_event_loop()
            def on_change(event_type: str, changed_path: str):
                if file.is_resource_file(changed_path):
                    session.resource_loader.clear_cache()
                if event_type != EVENT_TYPE_MODIFIED:
                    return
                try:
                    asyncio.run_coroutine_threadsafe(on_change_async(changed_path, session), loop).result()
                except Exception as e:
                    sys.stderr.write(f"{color('error:', colors.bold, colors.red)} {type(e).__name__}: {str(e)}\n")
            click.echo(f'Starting to watch `{root}`. Press ^C to stop.')
            await athena_watch_async(root, 0.1, on_change)

    asyncio.run(inner())

@athena.command()
@click.argument('paths', type=str, nargs=-1)
@click.option('-v', '--verbose', is_flag=True, help='increase verbosity of output')
@click.option('-e', '--environment', type=str, help="environment to run tests against", default=None)
@click.option('-p', '--plain', is_flag=True, help="format output as plain json")
def responses(paths: list[str], environment: str | None, verbose: bool, plain: bool):
    """
    Run one or more modules and print the response traces.
    
    PATH - Path to file or directory of modules to watch.
    """
    if (verbose):
        logging.root.setLevel(logging.INFO)

    if plain:
        module_callback = lambda _, result: click.echo(f"{display.trace_plain(result, include_requests=False, include_responses=True)}")
    else:
        module_callback = lambda _, result: click.echo(f"{display.trace(result, include_requests=False, include_responses=True)}")

    run_modules_and(paths, force_environment=environment, module_callback=module_callback)

@athena.command()
@click.argument('paths', type=str, nargs=-1)
@click.option('-v', '--verbose', is_flag=True, help='increase verbosity of output')
@click.option('-e', '--environment', type=str, help="environment to run tests against", default=None)
@click.option('-p', '--plain', is_flag=True, help="format output as plain json")
def requests(paths: list[str], environment: str | None, verbose: bool, plain: bool):
    """
    Run one or more modules and print the request traces.
    
    PATH - Path to file or directory of modules to watch.
    """
    if (verbose):
        logging.root.setLevel(logging.INFO)

    if plain:
        module_callback = lambda _, result: click.echo(f"{display.trace_plain(result, include_requests=True, include_responses=False)}")
    else:
        module_callback = lambda _, result: click.echo(f"{display.trace(result, include_requests=True, include_responses=False)}")

    run_modules_and(paths, force_environment=environment, module_callback=module_callback)

@athena.command()
@click.argument('paths', type=str, nargs=-1)
@click.option('-v', '--verbose', is_flag=True, help='increase verbosity of output')
@click.option('-e', '--environment', type=str, help="environment to run tests against", default=None)
@click.option('-p', '--plain', is_flag=True, help="format output as plain json")
def traces(paths: list[str], environment: str | None, verbose: bool, plain: bool):
    """
    Run one or more modules and print the full traces.
    
    PATH - Path to file or directory of modules to watch.
    """
    if (verbose):
        logging.root.setLevel(logging.INFO)

    if plain:
        module_callback = lambda _, result: click.echo(f"{display.trace_plain(result, include_requests=True, include_responses=True)}")
    else:
        module_callback = lambda _, result: click.echo(f"{display.trace(result, include_requests=True, include_responses=True)}")

    run_modules_and(paths, force_environment=environment, module_callback=module_callback)

def main():
    try:
        athena()
    except AthenaException as e:
        sys.stderr.write(f"{color('error:', colors.bold, colors.red)} {type(e).__name__}: {str(e)}\n")
        sys.exit(1)
    except QuietException as e:
        if e.message is not None:
            sys.stderr.write(f"{e.message}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
