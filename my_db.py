from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()

# User Model
class User(db.Model):
    __tablename__ = 'users'  # Explicitly set the table name

    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    login = db.Column(db.Boolean, default=False)  # Login status
    read_access = db.Column(db.Boolean, default=False)  # Read access
    write_access = db.Column(db.Boolean, default=False)  # Write access

    def __init__(self, google_id, name, login=False, read_access=False, write_access=False):
        self.google_id = google_id
        self.name = name
        self.login = login
        self.read_access = read_access
        self.write_access = write_access

    def __repr__(self):
        return f'<User {self.name} ({self.google_id})>'

# Sensor Data Model
class SensorData(db.Model):
    __tablename__ = 'sensor_data'

    id = db.Column(db.Integer, primary_key=True)
    distance = db.Column(db.Float, nullable=False)
    led_status = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.Integer, nullable=False)

    def __init__(self, distance, led_status, timestamp):
        self.distance = distance
        self.led_status = led_status
        self.timestamp = timestamp

    def __repr__(self):
        return f"<SensorData {self.distance} cm, LED Status: {self.led_status}, Timestamp: {self.timestamp}>"

# Initialize the database
def init_db(app):
    """
    Initialize the database with the Flask app context.
    """
    db.init_app(app)
    with app.app_context():
        db.create_all()

# User Management Functions
def add_user_to_db(google_id, name, login=False, read_access=False, write_access=False):
    """
    Adds a new user to the database if they don't already exist.
    """
    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        new_user = User(google_id=google_id, name=name, login=login, read_access=read_access, write_access=write_access)
        db.session.add(new_user)
        db.session.commit()

def add_or_update_user(google_id, name, login=False, read_access=False, write_access=False):
    """
    Adds a new user or updates an existing user's data.
    """
    user = User.query.filter_by(google_id=google_id).first()
    if user:
        user.name = name
        user.login = login
        user.read_access = read_access
        user.write_access = write_access
    else:
        user = User(google_id=google_id, name=name, login=login, read_access=read_access, write_access=write_access)
        db.session.add(user)
    db.session.commit()

def get_user_by_google_id(google_id):
    """
    Retrieve a user by their Google ID.
    """
    return User.query.filter_by(google_id=google_id).first()

def update_user_login_status(google_id, status):
    """
    Updates the login status of a user.
    """
    user = get_user_by_google_id(google_id)
    if user:
        user.login = status
        db.session.commit()

def set_user_permissions(google_id, read_access, write_access):
    """
    Sets read and write permissions for a user.
    """
    user = get_user_by_google_id(google_id)
    if user:
        user.read_access = read_access
        user.write_access = write_access
        db.session.commit()

def delete_user(google_id):
    """
    Deletes a user from the database.
    """
    user = get_user_by_google_id(google_id)
    if user:
        db.session.delete(user)
        db.session.commit()

# Sensor Data Management Functions
def add_sensor_data(distance, led_status):
    """
    Save the sensor data to the database.
    """
    timestamp = int(datetime.now().timestamp())  # Current timestamp
    sensor_data = SensorData(distance=distance, led_status=led_status, timestamp=timestamp)
    db.session.add(sensor_data)
    db.session.commit()

def get_all_sensor_data():
    """
    Retrieve all sensor data from the database.
    """
    return SensorData.query.all()

def get_latest_sensor_data():
    """
    Retrieve the latest sensor data from the database.
    """
    return SensorData.query.order_by(SensorData.timestamp.desc()).first()

def get_sensor_data_history():
    """
    Retrieve the sensor data history ordered by timestamp.
    """
    return SensorData.query.order_by(SensorData.timestamp.desc()).all()

def get_sensor_data_by_time_range(start_timestamp, end_timestamp):
    """
    Retrieve sensor data between a specific time range.
    """
    return SensorData.query.filter(SensorData.timestamp >= start_timestamp, SensorData.timestamp <= end_timestamp).all()

