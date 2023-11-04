from athena.client import Athena, Client, jsonify
from athena.test import athert

def run(athena: Athena):
    client: Client = athena.infix.build_client()
    response = client.get("api/planet/Venus")

    athert(response.status_code).equals(200)
