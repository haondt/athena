from flask import Flask, request, jsonify, render_template
from functools import wraps

app = Flask(__name__)

# Dummy data
users = {
    "admin": "password"
}

solar_system_data = {
    "planets": [
        {"name": "Mercury", "description": "Closest planet to the Sun"},
        {"name": "Venus", "description": "Known for its thick atmosphere"},
        {"name": "Earth", "description": "The only known planet with life"},
    ]
}

# authentication function
def check_auth(username, password):
    return users.get(username) == password

# authentication decorator
def auth_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return jsonify({"error": "Authentication failed"}), 401
        return func(*args, **kwargs)
    return decorated

# Authenticated endpoint
@app.route('/api/planets', methods=['GET'])
@auth_required
def get_planets():
    return jsonify(solar_system_data["planets"])

# Endpoint with JSON response
@app.route('/api/planets/<string:planet_name>', methods=['GET'])
@auth_required
def get_planet(planet_name):
    planet = next((p for p in solar_system_data["planets"] if p["name"] == planet_name), None)
    if planet:
        return jsonify(planet)
    return jsonify({"error": f"Planet not found: {planet_name}"}), 404

# Endpoint with HTML response
@app.route('/planet/<string:planet_name>', methods=['GET'])
def get_planet_html(planet_name):
    planet = next((p for p in solar_system_data["planets"] if p["name"] == planet_name), None)
    if planet:
        return render_template('planet.html', planet=planet)
    return "Planet not found", 404

# Create (POST) endpoint
@app.route('/api/planets', methods=['POST'])
@auth_required
def add_planet():
    if not request.json or 'name' not in request.json:
        return jsonify({"error": "Invalid data"}), 400

    new_planet = {
        "name": request.json['name'],
        "description": request.json.get('description', '')
    }
    solar_system_data["planets"].append(new_planet)
    return jsonify(new_planet), 201

# Update (PUT) endpoint
@app.route('/api/planets/<string:planet_name>', methods=['PUT'])
@auth_required
def update_planet(planet_name):
    planet = next((p for p in solar_system_data["planets"] if p["name"] == planet_name), None)
    if planet:
        data = request.json
        if data is not None and 'description' in data:
            planet['description'] = data['description']
        return jsonify(planet)
    return jsonify({"error": "Planet not found"}), 404

# Delete endpoint
@app.route('/api/planets/<string:planet_name>', methods=['DELETE'])
@auth_required
def delete_planet(planet_name):
    planet = next((p for p in solar_system_data["planets"] if p["name"] == planet_name), None)
    if planet:
        solar_system_data["planets"].remove(planet)
        return jsonify({"result": "Planet deleted"})
    return jsonify({"error": "Planet not found"}), 404

# Endpoint that does something based on header values
@app.route('/header-example', methods=['GET'])
def header_example():
    user_agent = request.headers.get('User-Agent')
    return f"User-Agent header value: {user_agent}"


app.run(host='0.0.0.0', debug=True, port=5000)
