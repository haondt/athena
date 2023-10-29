import os, sys
from typing import Any, Dict, List

from athena.format import color, colors, indent, long_format_error, pretty_format_error, short_format_error
from athena.trace import AthenaTrace
from . import file
from .client import Athena
from .exceptions import AthenaException
from .resource import ResourceLoader, DEFAULT_ENVIRONMENT_KEY
import importlib, inspect

class Result:
    def __init__(self, success: bool, result: Any, traces: List[AthenaTrace], error: Exception | None):
        self.success = success
        self.traces = traces
        self.error = error
        self.result = result

    def format_short(self) -> str:
        if not self.success:
            if self.error is not None:
                message = short_format_error(self.error)
                return f"{color('failed', colors.red)}\n{indent(message, 1, '    │ ', indent_empty_lines=True)}"
            else:
                return f"{color('skipped', colors.yellow)}"
        else:
            return f"{color('passed', colors.green)}"

    def format_long(self) -> str:
        if not self.success:
            if self.error is not None:
                message = ""
                try:
                    message = pretty_format_error(self.error, truncate_trace=True)
                except:
                    message = long_format_error(self.error, truncate_trace=False)
                return f"{color('failed', colors.red)}\n{indent(message, 1, '    │ ', indent_empty_lines=True)}"
            else:
                return f"{color('skipped', colors.yellow)}"
        else:
            return f"{color('passed', colors.green)}"

def run_modules(modules, environment: str | None=None) -> Dict[str, Result]:
    sys.path[0] = ''
    root = file.find_root(os.getcwd())
    results = {}
    for k in modules:
        path = modules[k]
        results[k] = _run_module(root, k, path, environment)
    return results

def _run_module(module_root, module_key, module_path, environment=None) -> Result:
    if environment is None:
        environment = DEFAULT_ENVIRONMENT_KEY
    module_path = os.path.normpath(module_path)
    if not os.path.isfile(module_path):
        raise AthenaException(f"cannot find module at {module_path}")
    if not module_path.endswith(".py"):
        raise AthenaException(f"not a python module {module_path}")

    module_workspace, module_collection, module_fullname = module_key.split(":")
    module_name = module_fullname.split(".")[-1]

    module_dir = os.path.dirname(module_path)
    workspace_fixture_dir = os.path.join(module_root, module_workspace)
    collection_fixture_dir = os.path.join(module_root, module_workspace, "collections", module_collection)

    resource_loader = ResourceLoader()
    athena_instance = Athena(
        (
            module_root,
            module_workspace,
            module_collection),
        environment,
        resource_loader)

    # load workspace fixture
    if os.path.isfile(os.path.join(workspace_fixture_dir, "fixture.py")):
        success, _, error = __try_execute_module(workspace_fixture_dir, "fixture", "fixture", (athena_instance.fixture,))
        if not success and error is not None:
            return Result(success, None, athena_instance.traces(), error)

    # load collection fixture
    if os.path.isfile(os.path.join(collection_fixture_dir, "fixture.py")):
        success, _, error = __try_execute_module(collection_fixture_dir, "fixture", "fixture", (athena_instance.fixture,))
        if not success and error is not None:
            return Result(success, None, athena_instance.traces(), error)

    # execute module
    success, result, error = __try_execute_module(module_dir, module_name, "run", (athena_instance,))
    return Result(success, result, athena_instance.traces(), error)

def __try_execute_module(module_dir, module_name, function_name, function_args):
    sys.path.insert(0, module_dir)
    try:
        module = importlib.import_module(module_name)
        try:
            has_run_function, run_function = __try_get_function(module, function_name, len(function_args))
            if has_run_function:
                result = run_function(*function_args)
                return True, result, None
            else:
                return False, None, None
        finally:
            del sys.modules[module_name]
    except Exception as e:
        if isinstance(e, AthenaException):
            raise
        return False, None, e
    finally:
        sys.path.pop(0)

def __try_get_function(module, function_name, num_args):
    for name, value in inspect.getmembers(module):
        if inspect.isfunction(value) and name == function_name:
            arg_spec = inspect.getfullargspec(value)
            if len(arg_spec.args) != num_args:
                continue
            return True, value
    return False, lambda: None
