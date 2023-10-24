# athena

# Usage

Start by running the init in your project directory.

```sh
python3 -m athena init
```

This will create an `athena` directory.

```sh
.
└── athena
    └── .athena
```

Enter this directory, and create a workspace

```sh
cd athena
python3 -m athena create workspace --name my-workspace
```

This will create a directory for the workspace and set up some environment files.

```sh
.
└── athena
    ├── .athena
    └── my-workspace
        ├── collections
        ├── environments.yml
        ├── lib
        │   ├── secrets.yml
        │   └── variables.yml
        ├── readme.md
        └── run
```

Lastly, create a new collection inside the workspace

```sh
python3 -m athena create collection --name my-collection --workspace my-workspace
```

This will add a new collection to the collections directory.

```sh
.
└── athena
    ├── .athena
    └── my-workspace
        ├── collections
        │   └── my-collection
        │       ├── lib
        │       │   ├── secrets.yml
        │       │   └── variables.yml
        │       ├── readme.md
        │       └── run
        ├── environments.yml
        ├── lib
        │   ├── secrets.yml
        │   └── variables.yml
        ├── readme.md
        └── run
```

# Development

To get started, set up a venv

```sh
python3 -m venv venv
. venv/bin/activate
```

and (optionally) use the athena alias

```sh
. ./alias.sh
```

To test changes, head into `example/athena` and run the alias

```sh
athena create workspace
```
