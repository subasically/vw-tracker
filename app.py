import os
import subprocess
import pickle
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
import smartcar

app = Flask(__name__, static_folder='static')

# Load environment variables from .env file
load_dotenv()

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
port = int(os.getenv('PORT', 8123))  # Default to 8123 if PORT is not set
host = os.getenv('HOST', 'localhost') # Default to localhost if HOST is not set
scopes = os.getenv('SCOPES', 'read_vehicle_info,read_location,read_odometer').split(',')

client = smartcar.AuthClient(client_id, client_secret, 'http://localhost/smartcar/redirect/', 'live')

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/location.json')
def location_json():
    return send_from_directory(app.static_folder, 'location.json')

@app.route('/auth_url', methods=['GET'])
def get_auth_url():
    auth_url = client.get_auth_url(scopes).replace('mode=test', 'mode=live')
    return jsonify({'auth_url': auth_url})

@app.route('/submit_auth_code', methods=['POST'])
def submit_auth_code():
    data = request.get_json()
    auth_code = data.get('auth_code')
    if not auth_code:
        return jsonify({'success': False, 'message': 'Authorization code not provided.'}), 400

    try:
        new_access = client.exchange_code(auth_code)
        with open('tokens.txt', 'wb') as file:
            pickle.dump(new_access, file)
        subprocess.Popen(["python", "get_vw_location.py"])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
