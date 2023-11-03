from athena.client import Athena, Client

def run(athena: Athena):
    client: Client = athena.infix.build_client()
    response = client.get("planets/Venus")
    trace = athena.trace()

    assert response.status_code == 200
