from athena.client import Athena

def run(athena: Athena):
    # client = athena.client(lambda r: r.base_url('http://localhost:5000/'))
    client = athena.client(lambda r: r.base_url('http://localhost:4040/'))
    # client.get("api/echo", lambda r: r
    #    .body.form({'foo': 5, 'bar': 10})
    #     .body.form_append('=', '=?&'))
    # client.get("api/echo", lambda r: r
    #    .query('foo', [5,10,15,20]))
    # client.get("api/echo", lambda r: r
    #    .body.form({'foo': 5, 'bar': 10}))
    # client.get("api/echo", lambda r: r
    #    .auth.basic('foo', 'bar'))

    client.post('/api/echo', lambda b: b
        .header('X-API-KEY', 'foobar')
        .query('foo', 'bar'))
    client.post('api/response', lambda b: b
        .body.json({
            'headers': {
                'TRACE-ID': '12345',
                'Content-Type': 'text/html'
            },
            'status_code': 202,
            'body': '<bold>Hi Mom!</bold>'
        })
    )
