# Utilities

## import/export

You can import and export secrets and variables with the `import` and `export` commands.
`export` will print to stdout and `import` will either take the values as an argument or take
the path to a file as an option. These commands will import/export all values for the entire
athena project.

```sh
athena export secrets > secrets.json

athena import secrets -f secrets.json
```

