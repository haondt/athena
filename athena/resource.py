import os
from typing import Tuple
from . import file
from .exceptions import AthenaException

DEFAULT_ENVIRONMENT_KEY = "__default__"

def _build_file_name(file_name, root, workspace, collection=None):
    dir_path = os.path.join(root, workspace)
    if collection is not None:
        dir_path = os.path.join(dir_path, "collections", collection)
    return os.path.join(dir_path, file_name)


def try_extract_value_from_resource(resource, name, environment) -> Tuple[bool, str]:
    if resource is not None and name in resource:
        value_set = resource[name]
        if value_set is not None and environment in value_set:
            return True, value_set[environment]
        if DEFAULT_ENVIRONMENT_KEY in value_set:
            return True, value_set[DEFAULT_ENVIRONMENT_KEY]
    return False, ""

class ResourceLoader:
    def __init__(self):
        self.loaded_resources = {}
    def load_workspace_secrets(self, root, workspace):
        file_path = _build_file_name("secrets.yml", root, workspace)
        success, resource = self.__try_load_or_create_file("secrets", file_path)
        if not success:
            raise AthenaException(f"unable to find secrets.yml for workspace {workspace}. expected to be at {file_path}")
        return resource

    def load_collection_secrets(self, root, workspace, collection):
        file_path = _build_file_name("secrets.yml", root, workspace, collection)
        success, resource = self.__try_load_or_create_file("secrets", file_path)
        if not success:
            raise AthenaException(f"unable to find secrets.yml for collection {collection}. expected to be at {file_path}")
        return resource

    def load_workspace_variables(self, root, workspace):
        file_path = _build_file_name("variables.yml", root, workspace)
        success, resource = self.__try_load_or_create_file("variables", file_path)
        if not success:
            raise AthenaException(f"unable to find variables.yml for workspace {workspace}. expected to be at {file_path}")
        return resource

    def load_collection_variables(self, root, workspace, collection):
        file_path = _build_file_name("variables.yml", root, workspace, collection)
        success, resource = self.__try_load_or_create_file("variables", file_path)
        if not success:
            raise AthenaException(f"unable to find variables.yml for collection {collection}. expected to be at {file_path}")
        return resource

    def __try_load_or_create_file(self, yaml_root_key, file_path):
        if file_path not in self.loaded_resources:
            if os.path.exists(file_path): 
                if os.path.isfile(file_path):
                    with open(file_path, "r") as f:
                        file_string = f.read()
                        serialized_file = file.import_yaml(file_string)
                        if yaml_root_key in serialized_file:
                            self.loaded_resources[file_path] = serialized_file[yaml_root_key]
                        else:
                            raise AthenaException(f"unable to find root key `{yaml_root_key}` in resource at {file_path}")
                else:
                    raise AthenaException(f"unable to load {file_path}: is a directory")
            else:
                with open(file_path, "w") as f:
                    f.write(f"{yaml_root_key}:\n")
                self.loaded_resources[file_path] = None

        if file_path in self.loaded_resources:
            return True, self.loaded_resources[file_path]
        return False, None

