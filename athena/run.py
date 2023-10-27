import os, sys
from . import file
from .client import Athena
from .exceptions import AthenaException
from .resource import ResourceLoader, DEFAULT_ENVIRONMENT_KEY
import importlib, inspect


def run_modules(modules, environment=None):
    root = file.find_root(os.getcwd())
    for k in modules:
        path = modules[k]
        success, result, err = _run_module(root, k, path, environment)
        if not success:
            if err is not None:
                print(f"failed with exception {err.__name__} {str(err)}")

def _run_module(module_root, module_key, module_path, environment=None):
    if environment is None:
        environment = DEFAULT_ENVIRONMENT_KEY
    module_path = os.path.normpath(module_path)
    if not os.path.isfile(module_path):
        raise AthenaException(f"cannot find module at {module_path}")
    if not module_path.endswith(".py"):
        raise AthenaException(f"not a python module {module_path}")

    module_dir = os.path.dirname(module_path)
    module_workspace, module_collection, _ = module_key.split(":")
    module_name = os.path.basename(module_path)[:-3]

    resource_loader = ResourceLoader()
    athena_instance = Athena(
        (
            module_root,
            module_workspace,
            module_collection),
        environment,
        resource_loader)

    sys.path.insert(0, module_dir)
    try:
        module = importlib.import_module(module_name)
        run_function = __get_run_function(module)
        run_function(athena_instance)
    except Exception as e:
        if isinstance(e, AthenaException):
            raise
        return False, None, e
    finally:
        sys.path.pop(0)

    return True, None, None

def __get_run_function(module):
    for name, value in inspect.getmembers(module):
        if inspect.isfunction(value) and name == "run":
            arg_spec = inspect.getfullargspec(value)
            if len(arg_spec.args) != 1:
                continue
            return value
    raise AthenaException(f"could not find run method in module {module.__name__}. please make sure there is a `run` function with a single argument.")



