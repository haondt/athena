import os, sys
from . import file
from .client import Athena
from .exceptions import AthenaException
from .resource import ResourceLoader, DEFAULT_ENVIRONMENT_KEY
from .format import color, colors, indent
import importlib, inspect, traceback

def run_modules(modules, environment=None):
    root = file.find_root(os.getcwd())
    for k in modules:
        path = modules[k]
        success, result, err = _run_module(root, k, path, environment)
        if not success:
            if err is not None:
                #message = _short_format_error(err)
                #message = _long_format_error(err)
                message = _pretty_format_error(err)
                print(f"{k}:\n{indent(message, 1, '    │ ', indent_empty_lines=True)}")

def _short_format_error(err: Exception):
    return f"{err.__class__.__name__}: {str(err)}"

def _long_format_error(err: Exception):
    frame = traceback.extract_tb(err.__traceback__)[-1]
    underline = [" "]*frame.colno
    if frame.lineno == frame.end_lineno: 
        underline += ["^"]*(frame.end_colno - frame.colno)
    else:
        underline += ["^"]*(len(frame._line.rstrip()) - len(underline))
    underline = ''.join(underline)
    s = f"File \"{frame.filename}\", line {frame.lineno}, in {frame.name}\n{frame._line.rstrip()}\n{underline}\n\n{err.__class__.__name__}: {str(err)}"
    return s

def _pretty_format_error(err: Exception):
    frame = traceback.extract_tb(err.__traceback__)[-1]
    captured_lines = []
    with open(frame.filename, "r") as f:
        i = 1
        for line in f:
            if i >= frame.lineno:
                captured_lines.append(line)
            i += 1
            if i > frame.end_lineno:
                break

    head = captured_lines[0][:frame.colno]
    body = ""
    tail = ""
    if len(captured_lines) == 1:
        body = captured_lines[0][frame.colno:frame.end_colno]
        tail = captured_lines[0][frame.end_colno:]
    else:
        body = captured_lines[0][frame.colno:]
        for line in captured_lines[1:-1]:
            body += line
        body += captured_lines[-1][:frame.end_colno]
        tail = captured_lines[-1][frame.end_colno:]
    colored_body = "\n".join([color(i, colors.bold, colors.brightred) for i in body.split("\n")])

    s = f"File \"{color(frame.filename, colors.italic)}\", line {frame.lineno}, in {color(frame.name, colors.bold)}"
    s += f"\n{head + colored_body + tail}"
    s += f"\n{color(err.__class__.__name__ + ':', colors.red)} {str(err)}"
    return s

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



