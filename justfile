# Define variables
venv := "venv"
python := venv / "bin/python"
pip := venv / "bin/pip"

[script]
[arg("force", short="f", long="force", value="true")]
venv force="false":
    if [ -d "{{venv}}" ] && [ "{{force}}" != "true" ]; then exit 0; fi
    python3 -m venv {{venv}}

install: venv
    {{pip}} install -e .[dev]

clean:
    rm -rf {{venv}}

reinstall: clean install
