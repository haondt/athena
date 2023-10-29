from athena.client import Athena, jsonify

def run(athena: Athena):
    client = athena.fixture.build_api_client(athena)
    response = client.get("planets/Venus")
    trace = athena.trace()
    print(jsonify(trace, indent=4))

    assert response.status_code == 200
