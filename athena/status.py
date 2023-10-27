from .resource import ResourceLoader, DEFAULT_ENVIRONMENT_KEY
def search_environments(root, module_keys):
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
    for module_key in module_keys:
        module_workspace, module_collection, _ = module_key.split(":")
        collection_variables = loader.load_collection_variables(root, module_workspace, module_collection)
        workspace_variables = loader.load_workspace_variables(root, module_workspace)
        collection_secrets = loader.load_collection_secrets(root, module_workspace, module_collection)
        workspace_secrets = loader.load_workspace_secrets(root, module_workspace)
        all_environments |= extract_environments(collection_variables)
        all_environments |= extract_environments(workspace_variables)
        all_environments |= extract_environments(collection_secrets)
        all_environments |= extract_environments(workspace_secrets)
    return all_environments











