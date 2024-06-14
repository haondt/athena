from athena.client import Fixture, Athena

def build_client(athena: Athena):
    base_url = athena.variable("base_url")
    return athena.client(lambda r: r
        .base_url(base_url))

def fixture(fixture: Fixture):
    fixture.build_client = build_client
