from athena.client import Athena
from athena.trace import serialize_trace

def run(athena: Athena):
    client = athena.fixture.build_api_client(athena)
    response = client.get("planets/Venus")
    trace = athena.trace()
    print(serialize_trace(trace))

    assert response.status_code == 200
