import os
import subprocess
import pickle
import logging
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
import smartcar
from version import __version__
import json
from datetime import datetime
import threading
import time
import pytz
from dateutil import parser

app = Flask(__name__, static_folder='static')

# Load environment variables from .env file
load_dotenv()

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
redirect_uri = os.getenv('SMARTCAR_REDIRECT_URI')

if not client_id or not client_secret or not redirect_uri:
    raise ValueError("CLIENT_ID, CLIENT_SECRET, and SMARTCAR_REDIRECT_URI must be set in the environment variables.")

port = int(os.getenv('PORT', 8123))  # Default to 8123 if PORT is not set
PERMISSIONS = os.getenv('PERMISSIONS', 'read_vehicle_info,read_location,read_odometer').split(',')

client = smartcar.AuthClient(client_id, client_secret, redirect_uri, 'live')

logging.basicConfig(level=logging.DEBUG)

# Ensure data.json exists
def ensure_data_json_exists():
    home_lat = os.getenv('HOME_LAT')
    home_lon = os.getenv('HOME_LON')
    app.logger.debug(f"Home location: {home_lat}, {home_lon}")
    home_location = {'latitude': float(home_lat), 'longitude': float(home_lon)} if home_lat and home_lon else {}
    
    if not os.path.exists('static/data.json'):
        with open('static/data.json', 'w') as file:
            json.dump({'last_refresh_time': None, 'home_location': home_location, 'locations': []}, file)
        app.logger.debug("data.json created with home location.")
    else:
        with open('static/data.json', 'r+') as file:
            data = json.load(file)
            data['home_location'] = home_location
            file.seek(0)
            json.dump(data, file, indent=4)
            file.truncate()
        app.logger.debug("Home location added to existing data.json.")

ensure_data_json_exists()

def update_last_refresh_time():
    with open('static/data.json', 'r+') as file:
        data = json.load(file)
        data['last_refresh_time'] = datetime.now().isoformat()
        file.seek(0)
        json.dump(data, file, indent=4)
        file.truncate()

def get_initial_location():
    with open('tokens.txt', 'rb') as file:
        tokens = pickle.load(file)

    token = tokens.access_token
    vehicles = smartcar.get_vehicles(token)
    vehicle_id = vehicles.vehicles[0]
    vehicle = smartcar.Vehicle(vehicle_id, token)

    vehicle_location = vehicle.location()

    # Read existing data from the data json file
    with open('static/data.json', 'r+') as file:
        data = json.load(file)
        location_data = data['locations']

    # Format data_age to a more human-friendly format
    data_age_human_friendly = vehicle_location.meta.data_age

    # Check for duplicate location
    duplicate_found = False
    for loc in location_data:
        if loc['latitude'] == vehicle_location.latitude and loc['longitude'] == vehicle_location.longitude:
            loc['data_age'] = data_age_human_friendly
            loc['request_id'] = vehicle_location.meta.request_id
            duplicate_found = True
            break

    if not duplicate_found:
        # Append new location data
        location_data.append({
            'latitude': vehicle_location.latitude,
            'longitude': vehicle_location.longitude,
            'data_age': data_age_human_friendly,
            'request_id': vehicle_location.meta.request_id
        })

    # Write updated data back to the data json file
    with open('static/data.json', 'w') as file:
        data['locations'] = location_data
        json.dump(data, file, indent=4)

def check_initial_tokens():
    try:
        with open('tokens.txt', 'rb') as file:
            tokens = pickle.load(file)
        token = tokens.access_token
        vehicles = smartcar.get_vehicles(token)
        if vehicles.vehicles:
            get_initial_location()
            update_last_refresh_time()
    except Exception as e:
        app.logger.error(f"Error checking tokens on initial app start: {e}")

check_initial_tokens()

@app.route('/')
def index():
    app.logger.debug('Serving index.html')
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/data.json')
def data_json():
    app.logger.debug('Serving data.json')
    return send_from_directory(app.static_folder, 'data.json')

@app.route('/auth_url', methods=['GET'])
def get_auth_url():
    auth_url = client.get_auth_url(PERMISSIONS).replace('mode=test', 'mode=live')
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
        
        update_last_refresh_time()

        threading.Thread(target=update_vehicle_location, daemon=True).start()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/version', methods=['GET'])
def get_version():
    return jsonify({'version': __version__})

@app.route('/check_tokens', methods=['GET'])
def check_tokens():
    try:
        with open('tokens.txt', 'rb') as file:
            tokens = pickle.load(file)
        token = tokens.access_token
        vehicles = smartcar.get_vehicles(token)
        if vehicles.vehicles:
            return jsonify({'valid': True})
        else:
            return jsonify({'valid': False})
    except Exception as e:
        return jsonify({'valid': False, 'message': str(e)}), 500

def refresh_token():
    with open('tokens.txt', 'rb') as file:
        tokens = pickle.load(file)

    refresh = tokens.refresh_token
    app.logger.debug(f"Saved refresh token is {refresh}")

    new_access = client.exchange_refresh_token(refresh)
    app.logger.debug(f"New access token: {new_access}")

    with open('tokens.txt', 'wb') as file:
        pickle.dump(new_access, file)

    update_last_refresh_time()

@app.route('/refresh_token', methods=['POST'])
def refresh_token_endpoint():
    try:
        refresh_token()
        return jsonify({'success': True, 'message': 'Token refreshed successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

def update_vehicle_location():
    with open('tokens.txt', 'rb') as file:
        tokens = pickle.load(file)

    token = tokens.access_token
    vehicles = smartcar.get_vehicles(token)
    vehicle_id = vehicles.vehicles[0]
    vehicle = smartcar.Vehicle(vehicle_id, token)

    previous_location = None

    home_lat = float(os.getenv('HOME_LAT', 'nan'))
    home_lon = float(os.getenv('HOME_LON', 'nan'))

    while True:
        current_time = time.time()
        
        # Get current time in Chicago time zone
        chicago_tz = pytz.timezone('America/Chicago')
        chicago_time = datetime.now(chicago_tz)

        # Skip updating location between 11pm and 4am Chicago time
        if 23 <= chicago_time.hour or chicago_time.hour < 4:
            print(f"[{chicago_time}] Skipping location update between 11pm and 4am Chicago time...")
            time.sleep(int(os.getenv('UPDATE_INTERVAL', 900)))  # Pause for 15 minutes
            continue

        vehicle_location = vehicle.location()

        # Read existing data from the data json file
        with open('static/data.json', 'r+') as file:
            data = json.load(file)
            location_data = data['locations']
            # Initialize previous_location with the last entry from location_data
            previous_location = location_data[-1] if location_data else None

        # Format data_age to a more human-friendly format
        data_age_human_friendly = vehicle_location.meta.data_age

        # Check for duplicate location
        duplicate_found = False
        for loc in location_data:
            if loc['latitude'] == vehicle_location.latitude and loc['longitude'] == vehicle_location.longitude:
                loc['data_age'] = data_age_human_friendly
                loc['request_id'] = vehicle_location.meta.request_id
                duplicate_found = True
                break

        if not duplicate_found:
            print(f"[{chicago_time}] Location has changed or first run, adding new location...")
            # Calculate distance from home
            if not (isnan(home_lat) or isnan(home_lon)):
                distance_from_home = calculate_distance(home_lat, home_lon, vehicle_location.latitude, vehicle_location.longitude)
            else:
                distance_from_home = None
            # Append new location data
            location_data.append({
                'latitude': vehicle_location.latitude,
                'longitude': vehicle_location.longitude,
                'data_age': data_age_human_friendly,
                'request_id': vehicle_location.meta.request_id,
                'distance_from_home': distance_from_home
            })

        # Write updated data back to the data json file
        with open('static/data.json', 'w') as file:
            data['locations'] = location_data
            json.dump(data, file, indent=4)

        # Pause for the appropriate interval
        if duplicate_found:
            time.sleep(int(os.getenv('PAUSE_INTERVAL', 1800)))  # Pause for 30 minutes
        else:
            time.sleep(int(os.getenv('UPDATE_INTERVAL', 900)))  # Pause for 15 minutes

        previous_location = {
            'latitude': vehicle_location.latitude,
            'longitude': vehicle_location.longitude
        }

def calculate_distance(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 3958.8  # Radius of the Earth in miles
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) * sin(dlat / 2) + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) * sin(dlon / 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c  # Distance in miles

# Schedule token refresh every 60 minutes
def schedule_token_refresh():
    while True:
        time.sleep(int(os.getenv('REFRESH_TOKEN_INTERVAL', 3600)))  # Pause for 60 minutes
        refresh_token()

# Start the token refresh scheduler in a separate thread
threading.Thread(target=schedule_token_refresh, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
