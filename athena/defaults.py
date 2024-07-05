
DEFAULT_VARIABLE_FILE_CONTENTS = {
    'my_variable': { '__default__': 'my value' }
}
DEFAULT_SECRET_FILE_CONTENTS = {
    'my_secret': { '__default__': 'my secret value' }
}
DEFAULT_MODULE_FILE_CONTENTS = '''from athena.client import Athena, Client
from athena.test import athert

def run(athena: Athena):
    client: Client = athena.infix.client()
    response = client.get('api/hello')
    athert(response.status_code).equals(200)
'''
DEFAULT_FIXTURE_FILE_CONTENTS = '''from athena.client import Fixture, Athena

def fixture(fixture: Fixture):
    def build_client(athena: Athena):
        client = athena.client(lambda b: b
            .base_url('https://example.com/'))
        return client

    fixture.client = build_client
'''
