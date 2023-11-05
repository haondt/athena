import os
from typing import Tuple
from typing_extensions import Dict
from . import file
from .exceptions import AthenaException

DEFAULT_ENVIRONMENT_KEY = "__default__"
_resource_value_type = str | int | float | bool | None
_resource_type = Dict[str, Dict[str, _resource_value_type]]

def _build_file_name(file_name, root, workspace, collection=None):
    dir_path = os.path.join(root, workspace)
    if collection is not None:
        dir_path = os.path.join(dir_path, "collections", collection)
    return os.path.join(dir_path, file_name)


def try_extract_value_from_resource(resource: _resource_type, name, environment: str | None) -> Tuple[bool, _resource_value_type]:
    if resource is not None and name in resource:
        value_set = resource[name]
        if value_set is not None and environment in value_set:
            return True, value_set[environment]
        if DEFAULT_ENVIRONMENT_KEY in value_set:
            return True, value_set[DEFAULT_ENVIRONMENT_KEY]
    return False, None

class ResourceLoader:
    def __init__(self, cache: bool=True):
        self._cache = cache
        self.loaded_resources: Dict[str, _resource_type] = {}
    def load_workspace_secrets(self, root: str, workspace: str) -> _resource_type:
        file_path = _build_file_name("secrets.yml", root, workspace)
        return self.__load_or_create_file("secrets", file_path)

    def load_collection_secrets(self, root: str, workspace: str, collection: str) -> _resource_type:
        file_path = _build_file_name("secrets.yml", root, workspace, collection)
        return self.__load_or_create_file("secrets", file_path)

    def load_workspace_variables(self, root: str, workspace: str) -> _resource_type:
        file_path = _build_file_name("variables.yml", root, workspace)
        return self.__load_or_create_file("variables", file_path)

    def load_collection_variables(self, root: str, workspace: str, collection: str) -> _resource_type:
        file_path = _build_file_name("variables.yml", root, workspace, collection)
        return self.__load_or_create_file("variables", file_path)

    def __load_or_create_file(self, yaml_root_key: str, file_path: str) -> _resource_type:
        if file_path in self.loaded_resources:
            return self.loaded_resources[file_path]

        if not os.path.exists(file_path): 
            with open(file_path, "w") as f:
                f.write(f"{yaml_root_key}:\n")
            if self._cache:
                self.loaded_resources[file_path] = {}
                return self.loaded_resources[file_path]
            else:
                return {}

        if not os.path.isfile(file_path):
            raise AthenaException(f"unable to load {file_path}: is a directory")

        with open(file_path, "r") as f:
            file_string = f.read()
            serialized_file = file.import_yaml(file_string)

            result, error = self.__load_resource_file(yaml_root_key, serialized_file)
            if result is not None:
                return result
            raise AthenaException(f"unable to load {file_path}: {error}")

    def __load_resource_file(self, root_key: str, resource_obj: object) -> tuple[_resource_type | None, str]:
        if resource_obj is None:
            return {}, "" 
        if not isinstance(resource_obj, Dict):
            return None, f"expected contents to be of type `Dict`, but found {type(resource_obj)}"
        if root_key not in resource_obj:
            return None, f"resource does not contain root key `{root_key}`"
        resource_obj = resource_obj[root_key]

        if resource_obj is None:
            return {}, ""
        if not isinstance(resource_obj, Dict):
            return None, f"expected first element to be of type `Dict` but found {type(resource_obj)}"

        result: _resource_type = {}
        for k, v in resource_obj.items():
            if not isinstance(k, str):
                return None, f"expected resource keys to be of type `str`, but found key `{k}` with type `{type(k)}`"
            if "." in k or ":" in k:
                return None, f"key names cannot contain '.' or ':', found in key `{k}`"
            if not isinstance(v, Dict):
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

