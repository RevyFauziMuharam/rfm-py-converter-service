import os
import uuid
import threading
from flask import request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
from app.api import api_bp
from app.api.schemas import (
    ConversionRequestSchema,
    ConversionResponseSchema,
    ConversionStatusResponseSchema
)
from app.services.converter import MP4ToMP3Converter
from app.services.splitter import MP3Splitter
from app.utils.file_utils import allowed_file, get_file_info
from app.utils.logger import get_logger
from app.tasks import process_conversion
from app import limiter

logger = get_logger(__name__)


# Fungsi untuk menjalankan proses di background dengan thread
def process_in_background(app, job_id, file_path, base_filename, chunk_size_mb, bitrate):
    def run_task():
        with app.app_context():
            process_conversion(job_id, file_path, base_filename, chunk_size_mb, bitrate)

    thread = threading.Thread(target=run_task)
    thread.daemon = True
    thread.start()
    return thread


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'ok'})


@api_bp.route('/conversion', methods=['POST'])
@limiter.limit("10 per hour")  # Batasi 10 konversi per jam per IP
def convert_file():
    """
    API endpoint to submit a new conversion job

    Expects a file upload with field name 'file' and optional parameters:
    - chunk_size: Size of chunks in MB (default: 25)
    - bitrate: Audio bitrate for MP3 (default: 192k)
    """
    # Check if file was included in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']

    # Check if a file was actually selected
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Check if file type is allowed
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed, must be MP4'}), 400

    # Parse form data
    schema = ConversionRequestSchema()
    try:
        data = schema.load(request.form)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    # Generate a unique ID for this job
    job_id = str(uuid.uuid4())

    # Save the uploaded file
    filename = secure_filename(file.filename)
    base_filename = os.path.splitext(filename)[0]
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
    file.save(upload_path)

    logger.info(f"File uploaded: {filename}, job_id: {job_id}")

    # Get file info
    file_info = get_file_info(upload_path)

    # Start processing in background
    # Untuk versi dengan Celery, uncomment baris berikut:
    # from celery_worker import celery
    # celery.send_task('celery_worker.process_conversion', args=[
    #     job_id, upload_path, base_filename,
    #     data.get('chunk_size', current_app.config['DEFAULT_CHUNK_SIZE_MB']),
    #     data.get('bitrate', '192k')
    # ])

    # Untuk versi tanpa Celery (lebih sederhana), gunakan ini:
    process_in_background(
        current_app._get_current_object(),  # Penting: gunakan _get_current_object()
        job_id,
        upload_path,
        base_filename,
        data.get('chunk_size', current_app.config['DEFAULT_CHUNK_SIZE_MB']),
        data.get('bitrate', '192k')
    )

    # Return job information
    response_data = {
        'job_id': job_id,
        'filename': filename,
        'file_size': file_info['size'],
        'status': 'processing'
    }

    return ConversionResponseSchema().dump(response_data), 202


@api_bp.route('/conversion/<job_id>', methods=['GET'])
def conversion_status(job_id):
    """
    Get the status of a conversion job

    Args:
        job_id: The unique job identifier
    """
    # Check if result directory exists for this job
    result_dir = os.path.join(current_app.config['RESULT_FOLDER'], job_id)

    if not os.path.exists(result_dir):
        # Check if job is still in progress (upload file exists)
        upload_files = [f for f in os.listdir(current_app.config['UPLOAD_FOLDER'])
                        if f.startswith(job_id)]

        if not upload_files:
            return jsonify({'error': 'Job not found'}), 404

        return jsonify({
            'job_id': job_id,
            'status': 'processing',
            'files': []
        }), 200

    # Check if there was an error
    error_file = os.path.join(result_dir, "error.txt")
    if os.path.exists(error_file):
        with open(error_file, 'r') as f:
            error_message = f.read()

        return jsonify({
            'job_id': job_id,
            'status': 'failed',
            'error': error_message,
            'files': []
        }), 200

    # Job is completed, get the files
    files = os.listdir(result_dir)
    file_info = []

    for filename in files:
        file_path = os.path.join(result_dir, filename)
        info = get_file_info(file_path)
        file_info.append({
            'filename': filename,
            'size': info['size'],
            'download_url': f"/api/download/{job_id}/{filename}"
        })

    response_data = {
        'job_id': job_id,
        'status': 'completed',
        'files': file_info
    }

    return ConversionStatusResponseSchema().dump(response_data), 200


@api_bp.route('/download/<job_id>/<filename>', methods=['GET'])
def download_file(job_id, filename):
    """
    Download a converted file

    Args:
        job_id: The unique job identifier
        filename: The name of the file to download
    """
    directory = os.path.join(current_app.config['RESULT_FOLDER'], job_id)

    if not os.path.exists(directory):
        return jsonify({'error': 'Job not found'}), 404

    # Return the file
    return send_from_directory(directory, filename, as_attachment=True)