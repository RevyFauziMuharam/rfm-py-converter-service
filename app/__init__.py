import os
from flask import Flask
from .config import Config
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Inisialisasi limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["2400 per day", "100 per hour"]
)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize limiter
    limiter.init_app(app)

    # Ensure storage directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)
    os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)

    # Register blueprints
    from app.api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    # Register error handlers
    from app.api.errors import register_error_handlers
    register_error_handlers(app)

    return app