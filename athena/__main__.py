import typer
import sys, os
from typing_extensions import Annotated
from . import file
from enum import Enum

app = typer.Typer()

@app.command()
def init(
        path: Annotated[str, typer.Argument(help="Path to initialize athena in")] = "."
    ):
    athena_path = file.init(path)
    print(f'Created athena project at: `{athena_path}`')


class Createables(str, Enum):
    workspace = "workspace"
    collection = "collection"

@app.command()
def create(
        item: Annotated[Createables, typer.Argument(
            help="Type of item",
            case_sensitive=False
            )],
        name: Annotated[str, typer.Option(
            help="Name of item",
            prompt=True
            )],
        workspace: Annotated[str, typer.Option(
            help="Workspace to create new collection inside of",
            )] = None
    ):
    if item is Createables.workspace:
        workspace_path = file.create_workspace(os.getcwd(), name)
        print(f'Created workspace at `{workspace_path}')
    elif item is Createables.collection:
        file.create_collection(os.getcwd(), workspace, name)

if __name__ == "__main__":
    try:
        app()
    except Exception as e:
        error_text = "\033[1;31merror:\033[0m"
        sys.stderr.write(f"{error_text} {str(e)}\n")
        sys.exit(1)
