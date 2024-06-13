from athena.client import Athena
from athena.test import athert

def run(athena: Athena):
    print('hello?')
    client = athena.fixture.build_client(athena)
    response = client.get("api/planets")
    
    # this will fail due to the request being unauthorized
    athert(response.status_code).equals(200)
