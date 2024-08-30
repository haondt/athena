import os, glob
from typing import Tuple
from . import file
from .exceptions import AthenaException
from .athena_json import serializeable, deserializeable, deserializeable_default

DEFAULT_ENVIRONMENT_KEY = "__default__"
_resource_value_type = str | int | float | bool | None
_resource_type = dict[str, dict[str, _resource_value_type]]


def validate_resource(resource_obj: object) -> tuple[_resource_type | None, str]:
    if resource_obj is None:
        return {}, "" 
    if not isinstance(resource_obj, dict):
        return None, f"expected contents to be of type `Dict`, but found {type(resource_obj)}"
    resource_obj = resource_obj

    result: _resource_type = {}
    for k, v in resource_obj.items():
        if not isinstance(k, str):
            return None, f"expected resource keys to be of type `str`, but found key `{k}` with type `{type(k)}`"
        if "." in k or ":" in k:
            return None, f"key names cannot contain '.' or ':', found in key `{k}`"
        if not isinstance(v, dict):
            return None, f"expected value for key `{k}` to be of type `Dict` but found {type(v)}"

        result[k] = {}
        for _k, _v in v.items():
            if not isinstance(_k, str):
                return None, f"expected resource entry key to be of type `str`, but found key `{k}.{_k}` with type `{type(_k)}`"
            if "." in _k or ":" in _k:
                return None, f"key names cannot contain '.' or ':', found in key `{_k}`"
            if not isinstance(_v, (str | int | bool | float | None)):
                return None, f"expected resource entry values to be of type `{_resource_type}`, but found value for key `{k}.{_k}` with type `{type(_v)}`"
            result[k][_k] = _v
    return result, ""

def load_resource_file(file_path: str) -> _resource_type:
    if not os.path.exists(file_path): 
        return {}

    if not os.path.isfile(file_path):
        raise AthenaException(f"unable to load {file_path}: is a directory")

    with open(file_path, "r") as f:
        file_string = f.read()
        serialized_file = file.import_yaml(file_string)
    
    result, error = validate_resource(serialized_file)
    if result is None:
        raise AthenaException(f"unable to load {file_path}: {error}")
    return result

def dump_resource_file(file_path: str, data: _resource_type):
    result, error = validate_resource(data)
    if result is None:
        raise AthenaException(f"Error while validating resource: {error}")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        f.write(file.export_yaml(data))

def try_extract_value_from_resource(resource: _resource_type, name, environment: str | None) -> Tuple[bool, _resource_value_type]:
    if resource is not None and name in resource:
        value_set = resource[name]
        if value_set is not None and environment in value_set:
            return True, value_set[environment]
        if DEFAULT_ENVIRONMENT_KEY in value_set:
            return True, value_set[DEFAULT_ENVIRONMENT_KEY]
    return False, None

# deep merge two resources
# lists are concatenated, dicts are merged, conflicts are decided via the conflict resolution arg
def merge_resources(old: _resource_type, new: _resource_type, conflicts="new") -> _resource_type:
    if conflicts not in ["new", "old", "err"]:
        raise ValueError("Unexpected conflict resolution:" + conflicts)
    result = old.copy()
    for k, v in new.items():
        if k not in result:
            result[k] = v
            continue
        if conflicts == "new":
            result[k] = v
        elif conflicts == "err":
            raise KeyError(f"Multiple entries found for key: .{k}")
    return result



@serializeable
@deserializeable_default("", "", "", "")
class ScopedResourceValue:
    def __init__(self, path: str, key: str, environment: str, value: _resource_value_type):
        self.path = path
        self.key = key
        self.environment = environment
        self.value = value

    def get_key(self):
        return f'{self.path}:{self.key}:{self.environment}'

def update_resource(resource: _resource_type, value: ScopedResourceValue):
    if value.key in resource and value.environment in resource[value.key] and resource[value.key][value.environment] == value.value:
        return False

    if value.key not in resource:
        resource[value.key] = {}
    resource[value.key][value.environment] = value.value
    return True


@serializeable
@deserializeable
class AggregatedResource:
    def __init__(self):
        self.values: list[ScopedResourceValue] = []

    def flatten(self) -> dict[str, _resource_value_type]:
        result: dict[str, _resource_value_type] = {}
        for value in self.values:
            key = value.get_key()
            if key in result:
                raise AthenaException(f'Unable to flatten AggregatedResource: multiple entries found for aggregated key {key}')
            result[key] = value.value
        return result

class ResourceLoader:
    def __init__(self, cache: bool=True):
        self._cache = cache
        self.loaded_resources: dict[str, _resource_type] = {}
        self.explored_files: dict[tuple[str, str, str], list[str]] = {}

    def __search_module_half_ancestors(self, root: str, module_path: str, filename: str):
        if self._cache:
            key = (root, module_path, filename)
            if key not in self.explored_files:
                self.explored_files[key] = file.search_module_half_ancestors(root, module_path, filename)
            return self.explored_files[key]
        return file.search_module_half_ancestors(root, module_path, filename)

    def __load_and_merge_resources(self, root: str, module_path: str, filename: str) -> _resource_type:
        file_paths = self.__search_module_half_ancestors(root, module_path, filename)
        resources = [self.__load_or_cache_file(f) for f in file_paths]
        if len(resources) == 0:
            return {}
        first_resource = resources[0]
        for resource in resources[1:]:
            first_resource = merge_resources(first_resource, resource)
        return first_resource

    def __load_and_aggregate_all_resources(self, root: str, filename: str) -> AggregatedResource:
        aggregated_resource = AggregatedResource()
        file_paths = glob.glob(os.path.join(root, '**', filename), recursive=True)
        for path in file_paths:
            for key, entry in self.__load_or_cache_file(path).items():
                for environment, value in entry.items():
                    if value != {}:
                        relpath = os.path.relpath(path, root)
                        aggregated_resource.values.append(ScopedResourceValue(relpath, key, environment, value))
        return aggregated_resource

    
    def load_secrets(self, root: str, module_path: str):
        return self.__load_and_merge_resources(root, module_path, 'secrets.yml')

    def load_variables(self, root: str, module_path: str):
        return self.__load_and_merge_resources(root, module_path, 'variables.yml')

    def load_all_secrets(self, root: str) -> AggregatedResource:
        return self.__load_and_aggregate_all_resources(root, 'secrets.yml')

    def load_all_variables(self, root: str) -> AggregatedResource:
        return self.__load_and_aggregate_all_resources(root, 'variables.yml')

    def __load_or_cache_file(self, file_path: str) -> _resource_type:
        if self._cache:
            if file_path not in self.loaded_resources:
                self.loaded_resources[file_path] = load_resource_file(file_path)
            return self.loaded_resources[file_path]
        return load_resource_file(file_path)

    def clear_cache(self):
        if not self._cache:
            return
        self.loaded_resources = {}
        self.explored_files = {}
