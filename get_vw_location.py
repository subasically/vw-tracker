import smartcar
import time
import pickle
from dateutil import parser
import urllib.request
from dotenv import load_dotenv
import os
import json  # Add import for json
import subprocess  # Add import for subprocess
import threading  # Add import for threading
import pytz  # Add import for pytz
from datetime import datetime  # Add import for datetime

# Load environment variables from .env file
load_dotenv()

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')

client = smartcar.AuthClient(client_id, client_secret, 'http://localhost/smartcar/redirect/', 'live')

# Alter this list to specify the scope of permissions your application is requesting access to
scopes = ['read_vehicle_info']

file = open('tokens.txt', 'rb')
tokens = pickle.load(file)
file.close()

token=tokens.access_token

vehicles = smartcar.get_vehicles(token)

vehicle_id = vehicles.vehicles[0]

vehicle = smartcar.Vehicle(vehicle_id, token)

previous_location = None
refresh_token_interval = int(os.getenv('REFRESH_TOKEN_INTERVAL', 3600))  # 60 minutes
last_refresh_time = time.time()

while True:
    current_time = time.time()
    
    # Run refreshtoken.py every 60 minutes
    if current_time - last_refresh_time >= refresh_token_interval:
        subprocess.run(["python", "refreshtoken.py"])
        last_refresh_time = current_time

    # Get current time in Chicago time zone
    chicago_tz = pytz.timezone('America/Chicago')
    chicago_time = datetime.now(chicago_tz)

    # print("Current time: ", chicago_time)
    # print("Current hour: ", chicago_time.hour)

    # Skip updating location between 11pm and 4am Chicago time
    if 23 <= chicago_time.hour or chicago_time.hour < 4:
        print(f"[{chicago_time}] Skipping location update between 11pm and 4am Chicago time...")
        time.sleep(int(os.getenv('UPDATE_INTERVAL', 900)))  # Pause for 15 minutes
        continue

    vehicle_location = vehicle.location()

    # Read existing location data from the location json file
    if os.path.exists('static/location.json') and os.path.getsize('static/location.json') > 0:
        try:
            with open('static/location.json', 'r') as file:
                location_data = json.load(file)
                # Initialize previous_location with the last entry from location_data
                previous_location = location_data[-1] if location_data else None
        except json.JSONDecodeError:
            location_data = []
            previous_location = None
    else:
        location_data = []
        previous_location = None

    # Format data_age to a more human-friendly format
    data_age_human_friendly = datetime.fromisoformat(vehicle_location.meta.data_age.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')

    # Append new location data
    location_data.append({
        'latitude': vehicle_location.latitude,
        'longitude': vehicle_location.longitude,
        'data_age': data_age_human_friendly,
        'request_id': vehicle_location.meta.request_id
    })

    # Write updated location data back to the location json file
    with open('static/location.json', 'w') as file:
        json.dump(location_data, file, indent=4)

    # Check if the location has changed
    if previous_location and (previous_location['latitude'] == vehicle_location.latitude and previous_location['longitude'] == vehicle_location.longitude):
        print(f"[{chicago_time}] Location has not changed, pausing for 30 minutes...")
        time.sleep(int(os.getenv('PAUSE_INTERVAL', 1800)))  # Pause for 30 minutes
    else:
        print(f"[{chicago_time}] Location has changed or first run, checking again in 15 minutes...")
        time.sleep(int(os.getenv('UPDATE_INTERVAL', 900)))  # Pause for 15 minutes

    previous_location = {
        'latitude': vehicle_location.latitude,
        'longitude': vehicle_location.longitude
    }


