import json

with open("/var/www/FlaskApp/FlaskApp/.client_secrets.json") as config_file:
    config = json.load(config_file)
