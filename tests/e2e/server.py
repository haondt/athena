from flask import Flask, request, jsonify, request
import time

app = Flask(__name__)

HTTP_METHODS = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH']

@app.route('/api/echo', methods=HTTP_METHODS)
def echo():
    request_data = {
        'timestamp': time.time(),
        'method': request.method,
        'args': request.args.to_dict(flat=False),
        'form': request.form.to_dict(flat=False),
        'body': str(request.data),
        'headers': dict(request.headers)
    }
    return jsonify(request_data)

@app.route('/api/response', methods=['POST'])
def response():
    response_data = request.json

    headers = response_data.get('headers', {})
    content_type = headers.get('Content-Type', 'text/plain')
    body = response_data.get('body', '')
    status_code = response_data.get('status_code', 200)
    duration = response_data.get('duration', 0)

    if duration > 0:
        time.sleep(duration)
    return body, status_code, headers

# # Endpoint with JSON response
# @app.route('/api/planets/<string:planet_name>', methods=['GET'])
# @auth_required
# def get_planet(planet_name):
#     planet = next((p for p in solar_system_data["planets"] if p["name"] == planet_name), None)
#     if planet:
#         return jsonify(planet)
#     return jsonify({"error": f"Planet not found: {planet_name}"}), 404

app.run(host='0.0.0.0', debug=True, port=5000)
