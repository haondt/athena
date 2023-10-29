from athena.client import Athena, Fixture

def build_client(athena: Athena):
    base_url = athena.get_variable("base_url")
    return athena.client(lambda r: r
        .base_url(base_url))

def build_api_client(athena: Athena):
    base_url = athena.get_variable("base_url") + "api/"
    username = athena.get_variable("user")
    password = athena.get_secret("pass")
    return athena.client(lambda r: r
        .base_url(base_url)
        .auth(lambda a: a.basic(username, password)))

def fixture(fixture: Fixture):
    fixture.build_api_client = build_api_client
    fixture.build_client = build_client
