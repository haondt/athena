import os

def init(base_dir: str):
    base_dir = os.path.normpath(base_dir)
    path = os.path.join(base_dir, "athena")
    if os.path.exists(path):
        raise Exception(f"path `{path}` already exists")
    os.mkdir(path)
    with open(os.path.join(path, ".athena"), "w") as f:
        pass
    return path

def find_root(current_dir: str):
    current_dir = os.path.normpath(current_dir)

    max_depth = 20
    prev_dir = None
    current_depth = 0
    while True:
        if prev_dir == current_dir or current_depth > max_depth:
            raise Exception(f"not an athena project")
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
        raise Exception(f"workspace '{name}' already exists")
    os.mkdir(path)

    readme_path = os.path.join(path, "readme.md")
    with open(readme_path, "w") as f:
        f.write(f"# {name}\n")

    with open(os.path.join(path, "environments.yml"), "w") as f:
        f.write("environments:\n")

    lib_dir = os.path.join(path, "lib")
    os.mkdir(lib_dir)
    variables_path = os.path.join(lib_dir, "variables.yml")
    with open(variables_path, "w") as f:
        f.write("variables:\n")
    secrets_path = os.path.join(lib_dir, "secrets.yml")
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
                raise Exception(f"cannot create collection {name}: workspace at `{workspace_path}` is a file")
        else:
            raise Exception(f"cannot create collection {name}: workspace at `{workspace_path}` does not exist")
    else:
        current_dir = os.path.normpath(current_dir)
        if current_dir == root:
            raise Exception(f"not inside a workspace and no workspace provided")
        relative_path = os.path.relpath(current_dir, root)
        workspace = relative_path.split(os.path.sep)[0]
        workspace_path = os.path.join(root, workspace)

    collections_path = os.path.join(workspace_path, "collections")
    if os.path.exists(collections_path):
        if os.path.isfile(collections_path):
                raise Exception(f"cannot create collection {name}: collections path at `{collections_path}` is a file")
    if not os.path.exists(collections_path):
        os.mkdir(collections_path)

    collection_path = os.path.join(collections_path, name)
    if os.path.exists(collection_path):
            raise Exception(f"collection at `{collection_path}` already exists")
    os.mkdir(collection_path)

    readme_path = os.path.join(collection_path, "readme.md")
    with open(readme_path, "w") as f:
        f.write(f"# {name}\n")

    lib_dir = os.path.join(collection_path, "lib")
    os.mkdir(lib_dir)
    variables_path = os.path.join(lib_dir, "variables.yml")
    with open(variables_path, "w") as f:
        f.write("variables:\n")
    secrets_path = os.path.join(lib_dir, "secrets.yml")
    with open(secrets_path, "w") as f:
        f.write("secrets:\n")

    run_dir = os.path.join(collection_path, "run")
    os.mkdir(run_dir)
