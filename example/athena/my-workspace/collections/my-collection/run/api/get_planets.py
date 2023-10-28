from athena.client import Athena
from athena.trace import serialize_trace

def run(athena: Athena):
    client = athena.fixture.build_client(athena)
    response = client.get("planets")
    trace = athena.trace(response)
    
    # this will fail due to the request being unauthorized
    assert response.status_code == 200
