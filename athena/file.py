import os, yaml
from .exceptions import AthenaException

def init(base_dir: str):
    base_dir = os.path.normpath(base_dir)
    path = os.path.join(base_dir, "athena")
    if os.path.exists(path):
        raise AthenaException(f"path `{path}` already exists")
    os.mkdir(path)
    with open(os.path.join(path, ".athena"), "w") as f:
        pass
    with open(os.path.join(path, ".gitignore"), "w") as f:
        f.write("__pycache__/\nsecrets.yml\n")
    return path

def find_root(current_dir: str):
    current_dir = os.path.normpath(current_dir)

    max_depth = 20
    prev_dir = None
    current_depth = 0
    while True:
        if prev_dir == current_dir or current_depth > max_depth:
            raise AthenaException(f"not an athena project")
        athena_file = os.path.join(current_dir, ".athena")
        if os.path.isfile(athena_file):
            return current_dir
        prev_dir = current_dir
        current_dir = os.path.dirname(current_dir)
        current_depth += 1

    return current_dir

def create_workspace(current_dir: str, name: str):
    base_dir = find_root(current_dir)
    path = os.path.join(base_dir, name)
    if os.path.exists(path):
        raise AthenaException(f"workspace '{name}' already exists")
    os.mkdir(path)

    readme_path = os.path.join(path, "readme.md")
    with open(readme_path, "w") as f:
        f.write(f"# {name}\n")

    variables_path = os.path.join(path, "variables.yml")
    with open(variables_path, "w") as f:
        f.write("variables:\n")
    secrets_path = os.path.join(path, "secrets.yml")
    with open(secrets_path, "w") as f:
        f.write("secrets:\n")

    run_dir = os.path.join(path, "run")
    os.mkdir(run_dir)

    collections_dir = os.path.join(path, "collections")
    os.mkdir(collections_dir)

    return path

def create_collection(current_dir: str, workspace: str, name: str):
    root = find_root(current_dir)
    workspace_path = None
    if workspace is not None:
        workspace_path = os.path.join(root, workspace)
        if os.path.exists(workspace_path):
            if os.path.isfile(workspace_path):
                raise AthenaException(f"cannot create collection {name}: workspace at `{workspace_path}` is a file")
        else:
            raise AthenaException(f"cannot create collection {name}: workspace at `{workspace_path}` does not exist")
    else:
        current_dir = os.path.normpath(current_dir)
        if current_dir == root:
            raise AthenaException(f"not inside a workspace and no workspace provided")
        relative_path = os.path.relpath(current_dir, root)
        workspace = relative_path.split(os.path.sep)[0]
        workspace_path = os.path.join(root, workspace)

    collections_path = os.path.join(workspace_path, "collections")
    if os.path.exists(collections_path):
        if os.path.isfile(collections_path):
                raise AthenaException(f"cannot create collection {name}: collections path at `{collections_path}` is a file")
    if not os.path.exists(collections_path):
        os.mkdir(collections_path)

    collection_path = os.path.join(collections_path, name)
    if os.path.exists(collection_path):
            raise AthenaException(f"collection at `{collection_path}` already exists")
    os.mkdir(collection_path)

    readme_path = os.path.join(collection_path, "readme.md")
    with open(readme_path, "w") as f:
        f.write(f"# {name}\n")

    variables_path = os.path.join(collection_path, "variables.yml")
    with open(variables_path, "w") as f:
        f.write("variables:\n")
    secrets_path = os.path.join(collection_path, "secrets.yml")
    with open(secrets_path, "w") as f:
        f.write("secrets:\n")

    run_dir = os.path.join(collection_path, "run")
    os.mkdir(run_dir)

def find_context(current_dir: str):
    workspace, collection = None, None

    current_dir = os.path.normpath(current_dir)
    root = find_root(current_dir)
    if current_dir == root:
        return root, workspace, collection

    relative_path = os.path.relpath(current_dir, root)
    paths = relative_path.split(os.path.sep)
    workspace = paths[0]
    if len(paths) >= 3:
        if paths[1] == "collections":
            collection = paths[2]
    return root, workspace, collection

def list_modules(root: str):
    module_list = {}
    for entry in os.listdir(root):
        workspace_path = os.path.join(root, entry)
        if os.path.isdir(workspace_path):
            collections_path = os.path.join(workspace_path, "collections")
            if os.path.isdir(collections_path):
                for collection in os.listdir(collections_path):
                    collection_path = os.path.join(collections_path, collection)
                    if os.path.isdir(collection_path):
                        modules_path = os.path.join(collection_path, "run")
                        if os.path.isdir(modules_path):
                            for module in os.listdir(modules_path):
                                module_path = os.path.join(modules_path, module)
                                if module.endswith(".py"):
                                    module_key = f"{entry}:{collection}:{module}"
                                    module_list[module_key] = module_path
    return module_list

def search_modules(root: str, workspace: str, collection: str, module: str):
    modules_list = list_modules(root)
    modules_search = {}
    for k in modules_list:
        ws, cl, md = k.split(":")
        if workspace not in ["*", ws]:
            continue
        if collection not in ["*", cl]:
            continue
        if module not in ["*", md, md[:-3]]:
            continue
        modules_search[k] = modules_list[k]
    return modules_search


def _import_yaml(file):
    return yaml.load(file, Loader=yaml.FullLoader)
