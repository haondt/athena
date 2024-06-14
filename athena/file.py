from typing import Callable
import os, yaml, re, glob

from .exceptions import AthenaException

def init(base_dir: str):
    base_dir = os.path.abspath(base_dir)
    base_dir = os.path.normpath(base_dir)
    if not os.path.exists(base_dir):
        raise AthenaException(f"path `{base_dir}` does not exist")
    if not os.path.isdir(base_dir):
        raise AthenaException(f"`{base_dir}` is not a directory")
    path = os.path.join(base_dir, "athena")
    if os.path.exists(path):
        raise AthenaException(f"path `{path}` already exists")
    os.mkdir(path)
    with open(os.path.join(path, ".athena"), "w") as f:
        pass
    with open(os.path.join(path, ".gitignore"), "w") as f:
        f.write("__pycache__/\nsecrets.yml\n.cache\n.history\n")
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


def __search_for_python_files(root: str, current_name=""):
    contents = {}
    for item in os.listdir(root):
        full_path = os.path.join(root, item)
        full_name = f"{current_name}.{item}"
        if current_name == "":
            full_name = f"{item}"
        if os.path.isfile(full_path) and item.endswith(".py"):
            contents[full_name[:-3]] = full_path
        elif os.path.isdir(full_path) and not (
            item.startswith(".")
            or item.startswith("__")):
            sub_contents = __search_for_python_files(full_path, full_name)
            contents |= sub_contents
    return contents



def search_module_half_ancestors(root: str, module_path: str, ancestor_name: str):
    output = []

    def check_and_add_ancestor(relpath):
        nonlocal output
        ancestor_path = os.path.normpath(os.path.join(root, relpath, ancestor_name))
        if os.path.isfile(ancestor_path):
            output.append(ancestor_path)

    check_and_add_ancestor('')
    module_relpath = os.path.relpath(module_path, root)
    relpath = ''
    for relpart in module_relpath.split(os.path.sep):
        if relpart.endswith('.py'):
            break
        relpath = os.path.join(relpath, relpart)
        check_and_add_ancestor(relpath)
    return output

def should_ignore_file(path: str):
    if not path.endswith('.py'):
        return True
    if path.endswith('fixture.py'):
        return True
    parts = path.split(os.pathsep)
    for part in parts:
        if part.startswith('__'):
            return True
        if part.startswith('.'):
            return True
    return False

def import_yaml(file) -> object:
     return yaml.load(file, Loader=yaml.FullLoader)

def export_yaml(obj) -> str:
    return yaml.dump(obj, default_flow_style=False)


