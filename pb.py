import json
import time
import random
import threading
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.models.consumer.v3.channel import Channel
from pubnub.exceptions import PubNubException

# PubNub credentials
publish_key = "pub-c-c47524f4-9a19-4e27-ac05-48aabca96f0e"  # Your PubNub Publish Key
subscribe_key = "sub-c-784a6cf6-7ec1-4fe4-9b7d-7d8b12c304b6"  # Your PubNub Subscribe Key
secret_key = "sec-c-NWE5MDU0MTMtNTk5YS00YWQ5LTk1ZTMtOTBhMjc4YTcyMzJh"  # Your PubNub Secret Key

# PubNub configuration
pn_config = PNConfiguration()
pn_config.publish_key = publish_key
pn_config.subscribe_key = subscribe_key
pn_config.uuid = "raspberry-pi"  # Unique ID for your device
pn_config.secret_key = secret_key

# Initialize PubNub
pubnub = PubNub(pn_config)

# Define the channel for your ultrasonic sensor
channel_name = "sensor-channel"

# Function to generate a new token
def generate_token():
    try:
        envelope = (
            pubnub.grant_token()
            .channels([Channel.id(channel_name).read().write()])
            .ttl(60)  # Token valid for 60 minutes
            .sync()
        )
        return envelope.result.token
    except PubNubException as e:
        print(f"Error generating token: {e}")
        return None

# Set the initial token
token = generate_token()
if token:
    pn_config.auth_key = token
else:
    print("Failed to generate initial token.")

# Background task to refresh the token periodically
def refresh_token():
    while True:
        try:
            time.sleep((60 - 10) * 60)  # Refresh the token 10 minutes before expiration
            new_token = generate_token()
            if new_token:
                pubnub.set_auth_key(new_token)
                print("Token refreshed successfully.")
            else:
                print("Failed to refresh token.")
        except Exception as e:
            print(f"Error refreshing token: {e}")

# Start the token refresh thread
threading.Thread(target=refresh_token, daemon=True).start()

# Function to publish data to the PubNub channel
def send_data_to_channel(distance):
    led_status = "green" if distance >= 10 else "red"  # Simulated LED status
    message = {
        "distance": distance,
        "led_status": led_status,
        "timestamp": time.time(),  # Current time in seconds since the epoch
    }
    print("Publishing message:", message)
    try:
        pubnub.publish().channel(channel_name).message(message).sync()
    except PubNubException as e:
        print(f"Error publishing message: {e}")

# Function to simulate distance measurement
def get_distance():
    distance = random.randint(5, 200)  # Simulated distance in cm
    print(f"Measured Distance: {distance} cm")
    return distance

# Function to start the ultrasonic sensor simulation
def start_ultrasonic_sensor():
    print("Starting ultrasonic sensor simulation...")
    while True:
        try:
            distance = get_distance()  # Simulate distance measurement
            send_data_to_channel(distance)  # Publish data to PubNub
            time.sleep(2)  # Simulated interval between measurements
        except Exception as e:
            print(f"Unexpected error occurred during data transmission: {e}")
            time.sleep(5)  # Wait before retrying

# Main entry point
if __name__ == "__main__":
    try:
        start_ultrasonic_sensor()
    except KeyboardInterrupt:
        print("Sensor data transmission interrupted by user.")
    except Exception as e:
        print(f"Unexpected error occurred: {e}")

