from athena.client import Athena, Client, jsonify

def run(athena: Athena):
    client: Client = athena.infix.build_client()
    response = client.get("api/planet/Venus")

    assert response.status_code == 200
