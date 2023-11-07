from athena.client import Athena, Fixture

def build_client(athena: Athena):
    base_url = athena.variable("base_url")
    return athena.client(lambda r: r
        .base_url(base_url))

def build_api_client(athena: Athena):
    base_url = athena.variable("base_url") + "api/"
    username = athena.variable("user")
    password = athena.secret("pass")
    return athena.client(lambda r: r
        .base_url(base_url)
        .hook.after(lambda r: print("headers", r.headers))
        .auth.basic(username, password))

def fixture(fixture: Fixture):
    fixture.build_api_client = build_api_client
    fixture.build_client = build_client
