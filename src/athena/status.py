from typing import Callable
import os

from athena.exceptions import AthenaException
from .json import serializeable, deserializeable
from .resource import ResourceLoader, DEFAULT_ENVIRONMENT_KEY, _resource_value_type, _resource_type
from . import file

def search_environments(root, dir_keys: list[str]):
    def extract_environments(resource):
        environments = []
        if resource is not None:
            for value_set in resource.values():
                if value_set is not None:
                    for environment in value_set.keys():
                        if environment != DEFAULT_ENVIRONMENT_KEY:
                            environments.append(environment)
        return set(environments)
    loader = ResourceLoader()
    all_environments = set()
    for dir_key in dir_keys:
        parsed_key = _parse_resource_key(dir_key)
        if parsed_key.collection is not None:
            collection_variables = loader.load_collection_variables(root, parsed_key.workspace, parsed_key.collection)
            collection_secrets = loader.load_collection_secrets(root, parsed_key.workspace, parsed_key.collection)
            all_environments |= extract_environments(collection_variables)
            all_environments |= extract_environments(collection_secrets)
        workspace_variables = loader.load_workspace_variables(root, parsed_key.workspace)
        workspace_secrets = loader.load_workspace_secrets(root, parsed_key.workspace)
        all_environments |= extract_environments(workspace_variables)
        all_environments |= extract_environments(workspace_secrets)
    return all_environments

@serializeable
@deserializeable
class AggregatedResource:
    def __init__(self):
        self.values: dict[str, _resource_value_type] = {}

def _collect_resource( 
    root: str,
    dir_keys: list[str], 
    workspace_loader: Callable[[str, str], _resource_type],
    collection_loader: Callable[[str, str, str], _resource_type]
) -> AggregatedResource:
    aggregate_resource = AggregatedResource()
    for dir_key in dir_keys:
        parsed_key = _parse_resource_key(dir_key)

        if parsed_key.collection is None:
            loaded_workspace = workspace_loader(root, parsed_key.workspace)
            loaded_workspace = {k:v for k, v  in loaded_workspace.items() if v != {}}
            if loaded_workspace != {}:
                for name, entry in loaded_workspace.items():
                    for environment, value in entry.items():
                        key = f"{parsed_key.workspace}.{name}.{environment}"
                        aggregate_resource.values[key] = value

        else:
            loaded_collection = collection_loader(root, parsed_key.workspace, parsed_key.collection)
            loaded_collection = {k:v for k, v  in loaded_collection.items() if v != {}}
            if loaded_collection != {}:
                for name, entry in loaded_collection.items():
                    for environment, value in entry.items():
                        key = f"{parsed_key.workspace}:{parsed_key.collection}.{name}.{environment}"
                        aggregate_resource.values[key] = value
    return aggregate_resource

def collect_secrets(root: str, dir_keys: list[str]) -> AggregatedResource:
    loader = ResourceLoader()
    return _collect_resource(root, dir_keys, loader.load_workspace_secrets, loader.load_collection_secrets)
def collect_variables(root: str, dir_keys: list[str]) -> AggregatedResource:
    loader = ResourceLoader()
    return _collect_resource(root, dir_keys, loader.load_workspace_variables, loader.load_collection_variables)

class DryRunApplyResult:
    def __init__(self, new_workspaces: list[str], new_collections: list[str], overwritten_values: list[str], new_values: list[str]):
        self.new_workspaces = new_workspaces
        self.new_collections = new_collections
        self.overwritten_values = overwritten_values
        self.new_values = new_values


class ParsedResourceKey:
    def __init__(self,
                 workspace: str, 
                 workspace_name: str | None=None,
                 workspace_environment: str | None=None,
                 collection: str | None=None, 
                 collection_name: str | None=None,
                 collection_environment: str | None=None,
                 ):
        self.workspace = workspace
        self.workspace_name = workspace_name
        self.workspace_environment = workspace_environment
        self.collection = collection
        self.collection_name = collection_name
        self.collection_environment = collection_environment

def _parse_resource_key(key: str) -> ParsedResourceKey:
    try:
        parts = key.split(":")
        workspace_parts = parts[0].split(".")
        parsed_key = ParsedResourceKey(workspace_parts[0])

        if len(workspace_parts) > 1:
            parsed_key.workspace_name, parsed_key.workspace_environment = workspace_parts[1:]
        if  len(parts) > 1:
            collection_parts = parts[1].split(".")
            parsed_key.collection = collection_parts[0]
            if len(collection_parts) > 1:
                parsed_key.collection_name, parsed_key.collection_environment = collection_parts[1:]
        if len(parts) > 2:
            raise ValueError("too many parts")
        return parsed_key
    except Exception as e:
        raise AthenaException(f"unable to parse resource key `{key}`: {e}")

def _dry_run_apply_resource(
        root: str,
        resource: AggregatedResource,
        workspace_loader: Callable[[str, str], _resource_type],
        collection_loader: Callable[[str, str, str], _resource_type]
        ) -> DryRunApplyResult:
    created_workspaces: set[str] = set()
    created_collections: set[str] = set()
    overwritten_values: set[str] = set()
    added_values: set[str] = set()

    existing_workspaces: set[str] = set()
    existing_collections: set[str] = set()

    existing_dirs = list(file.list_directories(root).keys())
    for dir_key in existing_dirs:
        parsed_key = _parse_resource_key(dir_key)
        existing_workspaces.add(parsed_key.workspace)
        if parsed_key.collection is not None:
            existing_collections.add(f"{parsed_key.workspace}:{parsed_key.collection}")

    existing_data = _collect_resource(root, existing_dirs, workspace_loader, collection_loader).values.keys()

    for key in resource.values.keys():
        if key in existing_data:
            overwritten_values.add(key)
        else:
            parsed_key = _parse_resource_key(key)
            new_dir = False
            if parsed_key.workspace not in existing_workspaces:
                created_workspaces.add(parsed_key.workspace)
                new_dir = True
            if parsed_key.collection is not None:
                collection_key = f"{parsed_key.workspace}:{parsed_key.collection}"
                if collection_key not in existing_collections:
                    created_collections.add(collection_key)
                    new_dir = True
            if not new_dir:
                added_values.add(key)

    return DryRunApplyResult(
            list(created_workspaces), 
            list(created_collections),
            list(overwritten_values),
            list(added_values))

def dry_run_apply_secrets(
        root: str,
        secrets: AggregatedResource
        ) -> DryRunApplyResult:
    loader = ResourceLoader()
    return _dry_run_apply_resource(root, secrets, loader.load_workspace_secrets, loader.load_collection_secrets)

def dry_run_apply_variables(
        root: str,
        variables: AggregatedResource
        ) -> DryRunApplyResult:
    loader = ResourceLoader()
    return _dry_run_apply_resource(root, variables, loader.load_workspace_variables, loader.load_collection_variables)

def _apply_resource(
    root: str,
    resource: AggregatedResource,
    resource_name: str,
    no_cache_workspace_loader: Callable[[str, str], _resource_type],
    no_cache_collection_loader: Callable[[str, str, str], _resource_type]
):

    existing_workspaces: set[str] = set()
    existing_collections: set[str] = set()

    existing_dirs = list(file.list_directories(root).keys())
    for dir_key in existing_dirs:
        parsed_key = _parse_resource_key(dir_key)
        existing_workspaces.add(parsed_key.workspace)
        if parsed_key.collection is not None:
            existing_collections.add(f"{parsed_key.workspace}:{parsed_key.collection}")

    def set_value(resource_path: str, loader: Callable[[], _resource_type], name: str, environment: str, value: _resource_value_type):
        resource = loader()
        if name not in resource:
            resource[name] = {}
        resource[name][environment] = value
        with open(resource_path, "w") as f:
            f.write(file.export_yaml({f"{resource_name}": resource}))

    for key, value in resource.values.items():
        parsed_key = _parse_resource_key(key)

        if parsed_key.workspace not in existing_workspaces:
            file.create_workspace(root, parsed_key.workspace)
            existing_workspaces.add(parsed_key.workspace)

        if parsed_key.collection is None:
            assert parsed_key.workspace_name is not None
            assert parsed_key.workspace_environment is not None
            set_value(
                    os.path.join(root, parsed_key.workspace, f"{resource_name}.yml"),
                    lambda: no_cache_workspace_loader(root, parsed_key.workspace),
                    parsed_key.workspace_name,
                    parsed_key.workspace_environment,
                    value)
        else:
            assert parsed_key.collection_name is not None
            assert parsed_key.collection_environment is not None
            collection_key = f"{parsed_key.workspace}:{parsed_key.collection}"
            if collection_key not in existing_collections:
                file.create_collection(root, parsed_key.workspace, parsed_key.collection)
                existing_collections.add(collection_key)

            collection = parsed_key.collection
            set_value(
                    os.path.join(root, parsed_key.workspace, "collections", parsed_key.collection, f"{resource_name}.yml"),
                    lambda: no_cache_collection_loader(root, parsed_key.workspace, collection),
                    parsed_key.collection_name,
                    parsed_key.collection_environment,
                    value)

def apply_secrets(
    root: str,
    secrets: AggregatedResource,
):
    loader = ResourceLoader(cache=False)
    return _apply_resource(root, secrets, "secrets", loader.load_workspace_variables, loader.load_collection_variables)

def apply_variables(
    root: str,
    variables: AggregatedResource,
):
    loader = ResourceLoader(cache=False)
    return _apply_resource(root, variables, "variables", loader.load_workspace_variables, loader.load_collection_variables)
