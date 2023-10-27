from . import file
from .resource import ResourceLoader, _try_extract_value_from_resource
from .exceptions import AthenaException
import os, sys

class Athena:
    def __init__(self, context, environment, resource_loader: ResourceLoader):
        self.__context = context
        self.__resource_loader = resource_loader
        self.__environment = environment

    def _get_context(self):
        return self.__context

    def get_variable(self, name):
        root, workspace, collection = self._get_context()

        collection_variables = self.__resource_loader.load_collection_variables(root, workspace, collection)
        success, value = _try_extract_value_from_resource(collection_variables, name, self.__environment)
        if success:
            return value

        workspace_variables = self.__resource_loader.load_workspace_variables(root, workspace)
        success, value = _try_extract_value_from_resource(workspace_variables, name, self.__environment)
        if success:
            return value

        raise AthenaException(f"unable to find variable \"{name}\" with environment \"{self.__environment}\". ensure variables have at least a default environment.")

    def get_secret(self, name):
        root, workspace, collection = self._get_context()

        collection_secrets = self.__resource_loader.load_collection_secrets(root, workspace, collection)
        success, value = _try_extract_value_from_resource(collection_secrets, name, self.__environment)
        if success:
            return value

        workspace_secrets = self.__resource_loader.try_load_workspace_secrets(root, workspace)
        success, value = _try_extract_value_from_resource(workspace_secrets, name, self.__environment)
        if success:
            return value

        raise AthenaException(f"unable to find secret \"{name}\" with environment \"{self.__environment}\". ensure secrets have at least a default environment")

