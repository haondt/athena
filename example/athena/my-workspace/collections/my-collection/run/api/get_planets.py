from athena.client import Athena

def run(athena: Athena):
    client = athena.fixture.build_client(athena)
    response = client.get("api/planets")
    
    # this will fail due to the request being unauthorized
    assert response.status_code == 200
