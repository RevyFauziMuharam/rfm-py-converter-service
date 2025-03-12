import os
from flask import Flask
from .config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
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
