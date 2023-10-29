from athena.client import Athena, jsonify

def example(athena: Athena):
    # form example
    client = athena.client(lambda r: r
        .base_url("http://helios.gabbro/"))
    response = client.put("hx/group/423d60b8-ecfb-4490-9503-f3334241d581", lambda r: r
        .form({
            "name": "Server",
            "id": "423d60b8-ecfb-4490-9503-f3334241d581"
        }))
    trace = athena.trace(response)
    print(jsonify(trace))

def example2(athena: Athena):
    secret = athena.get_secret("some_secret_key")
    base_url = athena.get_variable("base_url")

    client = athena.client(lambda r: r
        .base_url(base_url)
        .auth(lambda a: a.bearer(secret)))

    response1 = client.get("api/v1/hello")
    response2 = client.post("api/v1/hello", lambda r: r
        .header("foo", "bar")
        .header("baz", "qux")
        .json({
            "foo": "bar",
            "baz": [1, 2, 3]
        }))

