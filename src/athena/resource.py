import os
from typing import Tuple
from . import file
from .exceptions import AthenaException
from .json import serializeable, deserializeable

DEFAULT_ENVIRONMENT_KEY = "__default__"
_resource_value_type = str | int | float | bool | None
_resource_type = dict[str, dict[str, _resource_value_type]]


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
def _merge_resources(r1: _resource_type, r2: _resource_type, conflicts="new") -> _resource_type:
    if conflicts not in ["new", "old", "err"]:
        raise ValueError("Unexpected conflict resolution:" + conflicts)
    result = r1.copy()
    for k, v in r2.items():
        if k not in result:
            result[k] = v
            continue
        if conflicts == "new":
            result[k] = v
        elif conflicts == "err":
            raise KeyError(f"Multiple entries found for key: .{k}")
    return result

@serializeable
@deserializeable
class AggregatedResource:
    def __init__(self):
        self.values: dict[str, _resource_value_type] = {}

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
            first_resource = _merge_resources(first_resource, resource)
        return first_resource

    def __load_and_aggregate_resources(self, root: str, module_path: str, filename: str) -> AggregatedResource:
        aggregated_resource = AggregatedResource()
        file_paths = self.__search_module_half_ancestors(root, module_path, filename)
        for path in file_paths:
            for key, entry in self.__load_or_cache_file(path).items():
                for environment, value in entry.items():
                    if value != {}:
                        aggregated_resource.values[f'{path}.{key}.{environment}'] = value
        return aggregated_resource

    
    def load_secrets(self, root: str, module_path: str):
        return self.__load_and_merge_resources(root, module_path, 'secrets.yml')

    def load_variables(self, root: str, module_path: str):
        return self.__load_and_merge_resources(root, module_path, 'variables.yml')

    def load_aggregated_secrets(self, root: str, module_path: str):
        return self.__load_and_aggregate_resources(root, module_path, 'secrets.yml')

    def load_aggregated_variables(self, root: str, module_path: str):
        return self.__load_and_aggregate_resources(root, module_path, 'variables.yml')

    def __load_or_cache_file(self, file_path: str) -> _resource_type:
        if file_path in self.loaded_resources:
            return self.loaded_resources[file_path]

        if not os.path.exists(file_path): 
            if self._cache:
                self.loaded_resources[file_path] = {}
            return {}

        if not os.path.isfile(file_path):
            raise AthenaException(f"unable to load {file_path}: is a directory")

        with open(file_path, "r") as f:
            file_string = f.read()
            serialized_file = file.import_yaml(file_string)

            result, error = self.__load_resource_file(serialized_file)
            if result is not None:
                if self._cache:
                    self.loaded_resources[file_path] = result
                return result
            raise AthenaException(f"unable to load {file_path}: {error}")

    def __load_resource_file(self, resource_obj: object) -> tuple[_resource_type | None, str]:
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

