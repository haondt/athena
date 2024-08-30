from collections.abc import Coroutine
import os, sys, logging
from typing import Any, Dict, List, Callable

from . import history

from .athena_json import jsonify, serializeable

from .format import color, colors, indent, long_format_error, pretty_format_error, short_format_error
from .trace import AthenaTrace
from . import cache, file
from .client import Athena, Context, AthenaSession
from .exceptions import AthenaException
from .resource import ResourceLoader
import importlib, inspect

def try_execute_module(module_dir, module_name, function_name, function_args):
    sys.path.insert(0, module_dir)
    try:
        module = importlib.import_module(module_name)
        try:
            has_function, function = try_get_function(module, function_name, len(function_args))
            if has_function:
                result = function(*function_args)
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

def execute_module(module_dir, module_name, function_name, function_args):
    sys.path.insert(0, module_dir)
    try:
        module = importlib.import_module(module_name)
        try:
            has_function, function = try_get_function(module, function_name, len(function_args))
            if not has_function:
                raise AthenaException(f'Module {module_name} at {module_dir} is missing a {function_name} function with {len(function_args)} arguments')
            return function(*function_args)
        finally:
            del sys.modules[module_name]
    finally:
        sys.path.pop(0)

async def try_execute_module_async(module_dir, module_name, function_name, function_args):
    sys.path.insert(0, module_dir)
    try:
        module = importlib.import_module(module_name)
        try:
            has_function, function = try_get_function(module, function_name, len(function_args))
            if has_function:
                if inspect.iscoroutinefunction(function):
                    result = await function(*function_args)
                else:
                    result = function(*function_args)
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

def try_get_function(module, function_name, num_args):
    for name, value in inspect.getmembers(module):
        if inspect.isfunction(value) and name == function_name:
            arg_spec = inspect.getfullargspec(value)
            if len(arg_spec.args) != num_args:
                continue
            return True, value
    return False, lambda: None
