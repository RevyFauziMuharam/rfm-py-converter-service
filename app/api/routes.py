import os
import uuid
from flask import request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
from app.api import api_bp
from app.api.schemas import (
    ConversionRequestSchema,
    URLConversionRequestSchema,
    ConversionResponseSchema,
    ConversionStatusResponseSchema
)
from app.services.converter import MP4ToMP3Converter
from app.services.splitter import MP3Splitter
from app.utils.file_utils import allowed_file, get_file_info
from app.utils.logger import get_logger
from app.tasks import add_to_conversion_queue, get_queue_status

logger = get_logger(__name__)


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'ok'})


@api_bp.route('/conversion/url', methods=['POST'])
def convert_from_url():
    """
    API endpoint untuk memulai konversi dari URL

    Expects:
    - url: URL MP4 yang akan dikonversi (wajib)
    - filename: Nama file untuk output (opsional)
    - chunk_size: Ukuran potongan dalam MB (opsional, default: 25)
    - bitrate: Bitrate audio (opsional, default: 192k)
    """
    # Validasi request JSON
    if not request.is_json:
        return jsonify({'error': 'Request harus dalam format JSON'}), 400

    # Parse JSON data
    schema = URLConversionRequestSchema()
    try:
        data = schema.load(request.json)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    # Generate ID unik untuk job ini
    job_id = str(uuid.uuid4())

    # Log permintaan
    logger.info(f"URL conversion request received: {data['url'][:100]}... - job_id: {job_id}")

    # Tambahkan ke antrian konversi
    is_processing = add_to_conversion_queue(
        job_id=job_id,
        url=data['url'],
        base_filename=data.get('filename'),
        chunk_size_mb=data.get('chunk_size', current_app.config['DEFAULT_CHUNK_SIZE_MB']),
        bitrate=data.get('bitrate', '192k')
    )

    # Return job information
    response_data = {
        'job_id': job_id,
        'url': data['url'],
        'status': 'processing',
        'is_queued': not is_processing
    }

    # Tambahkan info antrian jika dijadwalkan
    if not is_processing:
        queue_info = get_queue_status(job_id)
        response_data['queue_position'] = queue_info['position']
        response_data['queue_length'] = queue_info['queue_length']

    return ConversionResponseSchema().dump(response_data), 202


@api_bp.route('/conversion/file', methods=['POST'])
def convert_file():
    """
    API endpoint untuk submit job konversi

    Expects:
    - file: File MP4 (wajib)
    - chunk_size: Ukuran potongan dalam MB (opsional, default: 25)
    - bitrate: Bitrate audio (opsional, default: 192k)
    """
    # Check if file was included in request
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada bagian file dalam request'}), 400

    file = request.files['file']

    # Check if a file was actually selected
    if file.filename == '':
        return jsonify({'error': 'Tidak ada file yang dipilih'}), 400

    # Check if file type is allowed
    if not allowed_file(file.filename):
        return jsonify({'error': 'Tipe file tidak diizinkan, harus MP4'}), 400

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

    # Add to conversion queue
    is_processing = add_to_conversion_queue(
        job_id=job_id,
        file_path=upload_path,
        base_filename=base_filename,
        chunk_size_mb=data.get('chunk_size', current_app.config['DEFAULT_CHUNK_SIZE_MB']),
        bitrate=data.get('bitrate', '192k')
    )

    # Return job information
    response_data = {
        'job_id': job_id,
        'filename': filename,
        'file_size': file_info['size'],
        'status': 'processing',
        'is_queued': not is_processing
    }

    # Add queue info if queued
    if not is_processing:
        queue_info = get_queue_status(job_id)
        response_data['queue_position'] = queue_info['position']
        response_data['queue_length'] = queue_info['queue_length']

    return ConversionResponseSchema().dump(response_data), 202


@api_bp.route('/conversion/<job_id>', methods=['GET'])
def conversion_status(job_id):
    """
    Get the status of a conversion job

    Args:
        job_id: The unique job identifier
    """
    # Check if in queue first
    queue_info = get_queue_status(job_id)
    if queue_info.get('status') == 'queued' and queue_info.get('position') > 0:
        return jsonify({
            'job_id': job_id,
            'status': 'queued',
            'queue_position': queue_info['position'],
            'queue_length': queue_info['queue_length'],
            'files': []
        }), 200

    # Check if still in active processing
    if queue_info.get('status') == 'processing':
        return jsonify({
            'job_id': job_id,
            'status': 'processing',
            'files': []
        }), 200

    # Check if result directory exists for this job
    result_dir = os.path.join(current_app.config['RESULT_FOLDER'], job_id)

    if not os.path.exists(result_dir):
        # Check if job is still in progress (upload file exists)
        upload_files = [f for f in os.listdir(current_app.config['UPLOAD_FOLDER'])
                        if f.startswith(job_id)]

        temp_files = []
        if os.path.exists(current_app.config['TEMP_FOLDER']):
            temp_files = [f for f in os.listdir(current_app.config['TEMP_FOLDER'])
                          if f.startswith(job_id)]

        if not upload_files and not temp_files:
            return jsonify({'error': 'Job tidak ditemukan'}), 404

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

    # Check if any MP3 files exist in the result directory
    mp3_files = [f for f in os.listdir(result_dir)
                 if f.endswith('.mp3') and f != "error.txt"]

    # If no MP3 files exist yet, job is still processing
    if not mp3_files:
        return jsonify({
            'job_id': job_id,
            'status': 'processing',
            'files': []
        }), 200

    # Job is completed, get the files
    file_info = []

    for filename in mp3_files:
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
        return jsonify({'error': 'Job tidak ditemukan'}), 404

    # Return the file
    return send_from_directory(directory, filename, as_attachment=True)