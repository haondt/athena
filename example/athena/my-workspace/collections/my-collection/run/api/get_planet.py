from athena.client import Athena, Client, jsonify

def run(athena: Athena):
    client: Client = athena.infix.build_api_client()

    response = client.get("planets/Venus")
    trace = athena.trace()
    print(jsonify(trace, indent=4))

    assert response.status_code == 200
