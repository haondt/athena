from flask import Flask, request

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "hello world!"


app.run(host='0.0.0.0', debug=True, port=5000)
