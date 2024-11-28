# Step 1: Install smartcar python library by running:    pip install smartcar
# Step 2: Create an account, and register a new app to the smartcar.com dashboard
# Step 3: When you register a new app, youll get a clientID, Client Secret from the smartcar.com dashboard

import smartcar
import time
import pickle
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')

client = smartcar.AuthClient(client_id, client_secret, 'http://localhost/smartcar/redirect/', 'live')

# Alter this list to specify the scope of permissions your application is requesting access to
scopes = ['read_vehicle_info']

# Access(access_token='eccf54e6-a2b3-492f-877a-856189b6720c',
# token_type='Bearer', expires_in=7200,#
# expiration=datetime.datetime(2023, 11, 3, 17, 50, 20, 345967), refresh_token='3115960e-1030-4d0d-a921-ceaa9fb9db56', 

file = open('tokens.txt', 'rb')
tokens = pickle.load(file)
file.close()

refresh=tokens.refresh_token
print("Saved refresh token is " + refresh)

new_access = client.exchange_refresh_token(refresh)

print(new_access)
file = open('tokens.txt', 'wb')
pickle.dump(new_access, file)
file.close()

time.sleep(int(os.getenv('REFRESH_TOKEN_INTERVAL', 3600)))  # Pause for 60 minutes

