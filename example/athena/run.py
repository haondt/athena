from athena.client import Athena

def run(athena: Athena):
    client = athena.client(lambda r: r.base_url('http://localhost:5000/'))
    # client.get("api/echo", lambda r: r
    #    .body.form({'foo': 5, 'bar': 10})
    #     .body.form_append('=', '=?&'))
    # client.get("api/echo", lambda r: r
    #    .query('foo', [5,10,15,20]))
    client.get("api/echo", lambda r: r
       .body.json({'foo': 5, 'bar': 10}))
    # client.get("api/echo", lambda r: r
    #    .auth.basic('foo', 'bar'))
