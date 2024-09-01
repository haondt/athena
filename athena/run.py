from collections.abc import Coroutine
import os, sys, logging
from typing import Any, Dict, List, Callable

from . import history

from .athena_json import jsonify, serializeable

from .format import color, colors, indent, long_format_error, pretty_format_error, short_format_error
from .trace import AthenaTrace
from . import cache, file, module
from .client import Athena, Context, AthenaSession
from .exceptions import AthenaException
from .resource import ResourceLoader
import importlib, inspect


_logger = logging.getLogger(__name__)


@serializeable
class SerializableExecutionTrace:
    def __init__(self):
        self.success: bool = False
        self.athena_traces: List[AthenaTrace] = []
        self.error: str | None = None
        self.result: str | None = None
        self.filename: str | None  = None
        self.module_name: str = "None"
        self.environment: str | None = None

    def jsonify(self):
        return jsonify(self, indent=4)

class ExecutionTrace:
    def __init__(self, module_name: str):
        self.success: bool = False
        self.athena_traces: List[AthenaTrace] = []
        self.error: Exception | None = None
        self.result: Any = None
        self.filename: str | None  = None
        self.module_name: str = module_name
        self.environment: str | None = None

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
                    message = pretty_format_error(self.error, truncate_trace=True, target_file=self.filename)
                except:
                    message = long_format_error(self.error, truncate_trace=False)
                return f"{color('failed', colors.red)}\n{indent(message, 1, '    │ ', indent_empty_lines=True)}"
            else:
                return f"{color('skipped', colors.yellow)}"
        else:
            return f"{color('passed', colors.green)}"

    def as_serializable(self):
        output = SerializableExecutionTrace()
        output.success = self.success
        output.athena_traces = self.athena_traces
        output.error = short_format_error(self.error) if self.error is not None else None
        output.result = str(self.result) if self.result is not None else None
        output.filename = self.filename
        output.module_name = self.module_name
        output.environment = self.environment
        return output

async def run_modules(
    root, 
    modules: list[str], 
    environment: str | None=None,
    module_completed_callback: Callable[[str, ExecutionTrace], None] | None=None,
    session: AthenaSession | None = None) -> Dict[str, ExecutionTrace]:
    if session is not None:
        return await _run_modules(root, modules, environment, module_completed_callback, session)
    async with AthenaSession() as session:
        return await _run_modules(root, modules, environment, module_completed_callback, session)

async def _run_modules(
    root: str, 
    modules: list[str], 
    environment: str | None,
    module_completed_callback: Callable[[str, ExecutionTrace], None] | None,
    session: AthenaSession) -> Dict[str, ExecutionTrace]:
    sys.path[0] = ''
    athena_cache = cache.load(root)
    results = {}
    try:
        for path in modules:
            module_name = os.path.basename(path)[:-3]
            results[path] = await _run_module(root, module_name, path, session, athena_cache, environment)
            history.push(root, lambda: results[path].as_serializable().jsonify())
            if module_completed_callback is not None:
                module_completed_callback(module_name, results[path])
    finally:
        cache.save(root, athena_cache)
    return results

async def _run_module(module_root, module_name, module_path, athena_session: AthenaSession, athena_cache: cache.Cache, environment=None) -> ExecutionTrace:
    trace = ExecutionTrace(module_name)
    trace.filename = module_path
    trace.environment = environment

    module_path = os.path.normpath(module_path)
    if not os.path.isfile(module_path):
        raise AthenaException(f"cannot find module at {module_path}")
    if not module_path.endswith(".py"):
        raise AthenaException(f"not a python module {module_path}")

    module_dir = os.path.dirname(module_path)

    context = Context(
        environment,
        module_name,
        module_path,
        module_root,
    )

    athena_instance = Athena(
        context,
        athena_session,
        athena_cache.data
    )

    try:
        # load fixtures
        for fixture_path in file.search_module_half_ancestors(module_root, module_path, 'fixture.py'):
            success, _, trace.error = module.try_execute_module(os.path.dirname(fixture_path), "fixture", "fixture", (athena_instance.fixture,))
            if not success and trace.error is not None:
                trace.athena_traces = athena_instance.traces()
                return trace

        # execute module
        trace.success, trace.result, trace.error = await module.try_execute_module_async(module_dir, module_name, "run", (athena_instance,))
        trace.athena_traces = athena_instance.traces()
        return trace

    finally:
        athena_cache.data = athena_instance.cache._data

