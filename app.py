import os
import subprocess
import pickle
import logging
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
import smartcar
from version import __version__

app = Flask(__name__, static_folder='static')

# Load environment variables from .env file
load_dotenv()

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
redirect_uri = os.getenv('SMARTCAR_REDIRECT_URI')

if not client_id or not client_secret:
    raise ValueError("CLIENT_ID and CLIENT_SECRET must be set in the environment variables.")

port = int(os.getenv('PORT', 8123))  # Default to 8123 if PORT is not set
scopes = os.getenv('SCOPES', 'read_vehicle_info,read_location,read_odometer').split(',')

client = smartcar.AuthClient(client_id, client_secret, redirect_uri, 'live')

logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def index():
    app.logger.debug('Serving index.html')
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/location.json')
def location_json():
    app.logger.debug('Serving location.json')
    return send_from_directory(app.static_folder, 'location.json')

@app.route('/auth_url', methods=['GET'])
def get_auth_url():
    auth_url = client.get_auth_url(scopes).replace('mode=test', 'mode=live')
    return jsonify({'auth_url': auth_url})

@app.route('/vehicle_name', methods=['GET'])
def get_vehicle_name():
    vehicle_name = os.getenv('VEHICLE_NAME', 'Vehicle')
    return jsonify({'vehicle_name': vehicle_name})

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

@app.route('/version', methods=['GET'])
def get_version():
    return jsonify({'version': __version__})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
