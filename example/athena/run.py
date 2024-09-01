from athena.client import Athena

def run(athena: Athena):
    client = athena.client(lambda r: r.base_url('http://localhost:5000/'))
    client.get("api/echo", lambda r: r
        .auth.basic('username', 'password')
        .body.form({'foo': 5, 'bar': 10}))

    client.post('api/response', lambda b: b
        .body.json({
            'headers': {
                'TRACE-ID': '12345',
                'Content-Type': 'text/html'
            },
            'status_code': 201,
            'body': '<bold>Hi Mom!</bold>'
        })
    )

