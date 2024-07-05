from athena.client import Athena

def run(athena: Athena):
    client = athena.client()
    client.get('http://echo.jsontest.com/key/value')
    client.get('http://echo.jsontest.com/foo/bar')

