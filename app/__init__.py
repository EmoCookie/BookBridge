import os
from flask import Flask


def create_app():
    # creates a Flask application instance
    app = Flask(__name__)

    # secret key for session management & security features
    app.secret_key = "thIs_Is_A_se12cRet_K4e5y"

    # defines the folder path where uploaded files like images will be stored
    UPLOAD_FOLDER = os.path.join("app", "static", "uploads")
    # creates the upload directory if it doesn't exist to avoid errors when saving files
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # configures the app to use the defined upload folder path
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

    # imports the 'main' Blueprint that contains route definitions
    from .routes import main

    # registers the 'main' Blueprint with the Flask app
    app.register_blueprint(main)

    # returns the Flask app instance to be used by the server
    return app
