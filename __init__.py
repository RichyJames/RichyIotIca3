import json
import os
import pathlib
import logging
import uuid
from datetime import datetime
from flask import Flask, session, abort, redirect, request, render_template, flash, url_for, jsonify
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.callbacks import SubscribeCallback
from werkzeug.utils import secure_filename
from .config import config

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # You can set it to ERROR for production

# Initialize Flask app
app = Flask(__name__)
app.secret_key = config.get("APP_SECRET_KEY")

# Google OAuth configuration
GOOGLE_CLIENT_ID = config.get("GOOGLE_CLIENT_ID")
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, ".client_secrets.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=[
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid",
    ],
    redirect_uri="https://sd3aiotrichy.online/callback",
)

# PubNub configuration
pnconfig = PNConfiguration()
pnconfig.publish_key = config["PUBNUB_PUBLISH_KEY"]
pnconfig.subscribe_key = config["PUBNUB_SUBSCRIBE_KEY"]
pnconfig.uuid = str(uuid.uuid4())  # Generate a unique UUID for each session
pubnub = PubNub(pnconfig)

class MySubscribeCallback(SubscribeCallback):
    def message(self, pubnub, message):
        app.logger.debug(f"Message received: {message.message}")
        # Process the received message here

# Add listener
pubnub.add_listener(MySubscribeCallback())
pubnub.subscribe().channels("sensor-channel").execute()

# Helper function: Check if user is logged in
def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        return function(*args, **kwargs)
    wrapper.__name__ = function.__name__
    return wrapper

# Flask routes and other parts of the code remain unchanged...

# Flask routes
@app.route("/login")
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)

# Custom filter for Jinja2 to convert timestamps
def todatetime(value):
    """Convert a timestamp to a human-readable datetime string."""
    if isinstance(value, (int, float)):  # Check if value is a timestamp
        return datetime.utcfromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
    return value  # If it's not a timestamp, return the original value

# Register the custom filter with Jinja2
app.jinja_env.filters['todatetime'] = todatetime

@app.route("/callback")
def callback():
    try:
        flow.fetch_token(authorization_response=request.url)
        if not session["state"] == request.args["state"]:
            app.logger.error("State mismatch during callback")
            abort(500)
        
        credentials = flow.credentials
        token_request = google.auth.transport.requests.Request()
        id_info = id_token.verify_oauth2_token(
            id_token=credentials._id_token,
            request=token_request,
            audience=GOOGLE_CLIENT_ID,
        )
        # Save user info to the session
        session["google_id"] = id_info.get("sub")  # Google unique user ID
        session["name"] = id_info.get("name")  # User's name from Google
        
        return redirect("/protected_area")
    except Exception as e:
        app.logger.error(f"Error during callback: {e}")
        abort(500)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/protected_area")
@login_is_required
def protected_area():
    user = {
        "name": session.get("name"),  # Fetch the user's name from the session
    }

    try:
        # Fetch the latest sensor data from PubNub
        sensor_data = fetch_sensor_data()  # Fetch real-time data from PubNub
    except Exception as e:
        app.logger.error(f"Error fetching sensor data: {e}")
        sensor_data = {"distance": "N/A", "led_status": "N/A", "timestamp": "N/A"}  # Handle errors gracefully

    return render_template("protected_area.html", user=user, sensor_data=sensor_data, config=config)

def fetch_sensor_data():
    # Inner function to handle received messages
    def message_received(pubnub, message):
        app.logger.debug(f"Message received: {message.message}")
        # Process and return the received message here if needed
    
    # Define a custom PubNub SubscribeCallback
    class MySubscribeCallback(SubscribeCallback):
        def message(self, pubnub, message):
            message_received(pubnub, message)
    
    # Add the custom listener to PubNub and subscribe to the channel
    pubnub.add_listener(MySubscribeCallback())
    pubnub.subscribe().channels("sensor-channel").execute()
    
    # Simulating a sensor data fetch (this will push data when it comes in)
    return {"distance": "N/A", "timestamp": "N/A"}

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/signin")
def signin():
    return render_template("signin.html")

@app.route("/api/store_distance_data", methods=["POST"])
@login_is_required
def store_distance_data():
    try:
        data = request.json
        distance = data.get("distance")
        led_status = data.get("led_status")  # Get LED status
        
        app.logger.debug(f"Received sensor data: {distance} cm, LED Status: {led_status}")
        
        # Publish to PubNub channel
        pubnub.publish().channel("sensor-channel").message({"distance": distance, "led_status": led_status}).sync()
        
        return jsonify({"status": "success", "message": "Distance data stored successfully."}), 201
    except Exception as e:
        app.logger.error(f"Error storing distance data: {e}")
        return jsonify({"status": "error", "message": f"An error occurred: {e}"}), 400

@app.route("/control-sensor", methods=["POST"])
def control_sensor():
    command = request.json.get('command')  # "on" or "off"
    
    if command == 'on':
        # Publish command to PubNub to turn the sensor on
        pubnub.publish().channel("control-channel").message({"command": "on"}).sync()
        return jsonify({"status": "success", "message": "Sensor turned on"})
    elif command == 'off':
        # Publish command to PubNub to turn the sensor off
        pubnub.publish().channel("control-channel").message({"command": "off"}).sync()
        return jsonify({"status": "success", "message": "Sensor turned off"})
    else:
        return jsonify({"status": "error", "message": "Invalid command"})

@app.context_processor
def inject_admin_id():
    google_admin_id = config.get("GOOGLE_ADMIN_ID")
    return {"google_admin_id": google_admin_id}

if __name__ == "__main__":
    app.run(debug=True)
