from athena.client import Athena

async def run(athena: Athena):
    client = athena.client()
    # raise ValueError("what now")
    await client.get_async('http://echo.free.beeceptor.com/key/value')
    await client.post_async(
        'http://echo.free.beeceptor.com/key/value',
        lambda r: r.body.form({
            'foo': 'yes'
        }))

