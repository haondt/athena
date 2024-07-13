import subprocess, time, os, json, yaml
import pytest

@pytest.fixture(scope="module")
def resource_files():
    return {
        "secrets.yml": {
            "database_password": {
                "__default__": "default_password123",
                "production": "prod_password456",
                "development": "dev_password789",
                "testing": True
            },
            "api_key": {
                "__default__": "default_api_key_abc",
                "staging": "staging_api_key_def",
                "production": "prod_api_key_ghi",
                "testing": "test_api_key_jkl"
            },
        },
        "foo/bar/secrets.yml": {
            "encryption_key": {
                "__default__": "default_encryption_key_mno",
                "production": "prod_encryption_key_pqr",
                "staging": "staging_encryption_key_stu"
            },
        },
        "foo/secrets.yml": {
            "email_password": {
                "__default__": "email_default_pass_abc",
                "backup": "backup_email_pass_ghi"
            }
        },
        "foo/bar/variables.yml": {
            "app_name": {
                "__default__": "MyApp",
                "staging": "MyApp-Staging",
                "production": "MyApp-Prod",
                "testing": "MyApp-Test"
            },
            "timeout": {
                "__default__": 30,
                "production": 60,
                "development": 45,
                "testing": 15
            }
        },
        "foo/variables.yml": {
            "log_level": {
                "__default__": "INFO",
                "development": "DEBUG",
                "production": "WARN",
                "staging": "ERROR"
            }
        },
        "baz/variables.yml": {
            "max_connections": {
                "__default__": 10,
                "high_traffic": 50,
                "low_traffic": 5
            }
        }
    }

@pytest.fixture(scope="module")
def setup_athena(tmp_path_factory, resource_files):
    tmp_dir = tmp_path_factory.mktemp('test_tmp')
    subprocess.run(['athena', 'init', '--bare', tmp_dir], capture_output=True, text=True)
    athena_dir = os.path.join(tmp_dir, 'athena')

    for k, v in resource_files.items():
        path = os.path.join(athena_dir, k)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(yaml.dump(v))
    yield athena_dir

@pytest.fixture(scope="module")
def new_athena(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp('test_tmp_new')
    subprocess.run(['athena', 'init', '--bare', tmp_dir], capture_output=True, text=True)
    athena_dir = os.path.join(tmp_dir, 'athena')
    yield athena_dir

def test_export_secrets(setup_athena, resource_files):
    athena_dir = setup_athena
    result = subprocess.run(['athena', 'export', 'secrets'], cwd=athena_dir, capture_output=True, text=True)

    assert result.returncode == 0
    exported = json.loads(result.stdout)
    assert len(exported['values']) == 13

    for value in exported['values']:
        assert resource_files[value['path']][value['key']][value['environment']] == value['value']

def test_export_variables(setup_athena, resource_files):
    athena_dir = setup_athena
    result = subprocess.run(['athena', 'export', 'variables'], cwd=athena_dir, capture_output=True, text=True)

    assert result.returncode == 0
    exported = json.loads(result.stdout)
    assert len(exported['values']) == 15

    for value in exported['values']:
        assert resource_files[value['path']][value['key']][value['environment']] == value['value']
