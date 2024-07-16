import os

from .resource import ResourceLoader, DEFAULT_ENVIRONMENT_KEY, _resource_value_type, _resource_type, AggregatedResource, dump_resource_file, load_resource_file, merge_resources, update_resource

def search_environments(root: str) -> list[str]:
    loader = ResourceLoader()
    secrets = loader.load_all_secrets(root)
    variables = loader.load_all_variables(root)
    all_environments: set[str] = set()
    for value in secrets.values + variables.values:
        all_environments.add(value.environment)

    return list(all_environments)

def collect_secrets(root: str) -> AggregatedResource:
    loader = ResourceLoader()
    return loader.load_all_secrets(root)

def collect_variables(root: str) -> AggregatedResource:
    loader = ResourceLoader()
    return loader.load_all_variables(root)

class DryRunApplyResult:
    def __init__(self, overwritten_values: list[str], new_values: list[str]):
        self.overwritten_values = overwritten_values
        self.new_values = new_values

class ApplyResult:
    def __init__(self, errors: list[str]):
        self.errors = errors

def dry_run_apply_secrets(
        root: str,
        secrets: AggregatedResource
        ) -> DryRunApplyResult:
    loader = ResourceLoader()
    existing_secrets = loader.load_all_secrets(root)

    flattened_incoming_secrets = secrets.flatten()
    flattened_existing_secrets = existing_secrets.flatten()

    changed_values: list[str] = []
    new_values: list[str] = []
    for k, v in flattened_incoming_secrets.items():
        if k in flattened_existing_secrets:
            if flattened_existing_secrets[k] == v:
                continue
            changed_values.append(k)
            continue
        new_values.append(k)
    return DryRunApplyResult(
        changed_values,
        new_values
    )

def dry_run_apply_variables(
        root: str,
        variables: AggregatedResource
        ) -> DryRunApplyResult:
    loader = ResourceLoader()
    existing_variables = loader.load_all_variables(root)

    flattened_incoming_variables = variables.flatten()
    flattened_existing_variables = existing_variables.flatten()

    changed_values: list[str] = []
    new_values: list[str] = []
    for k, v in flattened_incoming_variables.items():
        if k in flattened_existing_variables:
            if flattened_existing_variables[k] == v:
                continue
            changed_values.append(k)
            continue
        new_values.append(k)
    return DryRunApplyResult(
        changed_values,
        new_values
    )

def apply_resource(
    root: str,
    resource: AggregatedResource,
):
    files_to_write: dict[str, _resource_type] = {}
    errors: list[str] = []

    for value in resource.values:
        path = os.path.join(root, value.path)
        if path not in files_to_write:
            files_to_write[path] = load_resource_file(path)
        update_resource(files_to_write[path], value)

    for path, value in files_to_write.items():
        try:
            dump_resource_file(path, value)
        except Exception as e:
            errors.append(f'Error while updating resource file {path}: {e}')
    return ApplyResult(errors)

