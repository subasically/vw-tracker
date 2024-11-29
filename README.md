# VW Tracker

Simple scripts for getting car status from Smartcar.com. This project uses Flask to create a web interface for tracking the location of a VW car.

## Prerequisites

- Docker
- DockerHub account

## Setup

1. **Clone the repository**:

   ```sh
   git clone https://github.com/yourusername/vw-tracker.git
   cd vw-tracker
   ```

2. **Create a `.env` file: Create a `.env` file in the root directory of the project and add the following environment variables:**

   ```sh
   UPDATE_INTERVAL=900
   PAUSE_INTERVAL=1800
   REFRESH_TOKEN_INTERVAL=3600
   CLIENT_ID=your_client_id
   CLIENT_SECRET=your_client_secret
   PERMISSIONS=Get permissions from here: https://smartcar.com/docs/api-reference/permissions and add them
   ```

3. **Build and run the Docker container:**:

   ```sh
   docker build -t vw-tracker .
   docker run -p 8123:8123 --env-file .env vw-tracker
   ```

4. **Access the web interface: Open your web browser and go to `http://localhost:8123` to access the web interface.**

## Usage

1. Authenticate with Smartcar:

- Click on the "Authenticate" button on the web interface.
- Follow the instructions to link your car and allow access.
- Copy the authorization code from the URL and paste it into the input field on the web interface.
- Click "Submit" to start tracking your car's location.

1. View location history:

- The map on the web interface will display the location history of your car.
- The map will automatically update every 15 minutes with the latest location data.

## Additional Information

- The application uses environment variables to configure update intervals and Smartcar API credentials.
- The location data is stored in a JSON file (static/location.json) and displayed on the map using Leaflet.js.
- The application includes a script (refreshtoken.py) to refresh the Smartcar API tokens every 60 minutes.

## License

This project is licensed under the GNU General Public License v3.0. See the LICENSE file for details.
