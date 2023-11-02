from athena.client import Athena, Client, jsonify

import asyncio
async def run(athena: Athena):
    client = athena.client()
    tasks = [client.get_async("https://google.com") for _ in range(10)]
    await asyncio.gather(*tasks)

def run2(athena: Athena):
    client: Client = athena.infix.build_client()
    response = client.get("planets/Venus")
    trace = athena.trace()

    print(jsonify(trace, indent=4))

    assert response.status_code == 200
