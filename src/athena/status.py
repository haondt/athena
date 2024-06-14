from typing import Callable
import os

from .exceptions import AthenaException
from .resource import ResourceLoader, DEFAULT_ENVIRONMENT_KEY, _resource_value_type, _resource_type, AggregatedResource
from . import file

def search_environments(root: str, module_paths: list[str]):
    loader = ResourceLoader()
    def extract_environments(resource):
        environments = []
        if resource is not None:
            for value_set in resource.values():
                if value_set is not None:
                    for environment in value_set.keys():
                        if environment != DEFAULT_ENVIRONMENT_KEY:
                            environments.append(environment)
        return set(environments)
    all_environments = set()
    for path in module_paths:
        secrets = loader.load_secrets(root, path)
        variables = loader.load_variables(root, path)
        all_environments |= extract_environments(secrets)
        all_environments |= extract_environments(variables)
    return list(all_environments)


def collect_secrets(root: str) -> AggregatedResource:
    loader = ResourceLoader()
    return loader.load_all_secrets(root)
def collect_variables(root: str) -> AggregatedResource:
    loader = ResourceLoader()
    return loader.load_all_variables(root)

class DryRunApplyResult:
    def __init__(self, new_directories: list[str], overwritten_values: list[str], new_values: list[str]):
        self.new_directories = new_directories
        self.overwritten_values = overwritten_values
        self.new_values = new_values

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
