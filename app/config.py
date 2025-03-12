import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(os.path.dirname(basedir), '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    
    # File storage configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(basedir, '../storage/uploads')
    RESULT_FOLDER = os.environ.get('RESULT_FOLDER') or os.path.join(basedir, '../storage/results')
    TEMP_FOLDER = os.environ.get('TEMP_FOLDER') or os.path.join(basedir, '../storage/temp')
    
    # Max allowed file size (1000MB)
    MAX_CONTENT_LENGTH = 1000 * 1024 * 1024
    
    # Default chunk size (25MB)
    DEFAULT_CHUNK_SIZE_MB = 25
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'mp4'}
    
    # Redis & Celery configuration
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    
    # File serve configuration
    RESULTS_SERVE_EXPIRY = 3600  # 1 hour in seconds

    # Tambahkan konfigurasi throttling berdasarkan ukuran file
    MAX_CONCURRENT_CONVERSIONS = 3  # Maksimum 3 konversi berjalan bersamaan
    MAX_FILE_SIZE_FOR_INSTANT_PROCESSING = 50 * 1024 * 1024  # 50MB
    LARGE_FILE_PROCESSING_DELAY = 300  # Delay 5 menit untuk file besar
