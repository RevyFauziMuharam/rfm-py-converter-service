import os
import shutil
import time
import threading
from flask import current_app, Flask

from app.services.converter import MP4ToMP3Converter
from app.services.downloader import URLDownloader
from app.services.splitter import MP3Splitter
# Setup logger
from app.utils.logger import get_logger

logger = get_logger("tasks")

# Variabel global untuk menyimpan instance Flask app
_app = None


def set_app(app):
    """Set aplikasi Flask yang akan digunakan oleh thread"""
    global _app
    _app = app


# Queue manager untuk mengelola jumlah konversi bersamaan
class ConversionQueueManager:
    def __init__(self, max_concurrent=3):
        self.max_concurrent = max_concurrent
        self.active_jobs = 0
        self.queue = []
        self.lock = threading.Lock()

    def add_job(self, job_id, url=None, file_path=None, base_filename=None, chunk_size_mb=25, bitrate="192k"):
        """Tambahkan job ke antrian dan proses jika memungkinkan"""
        with self.lock:
            # Cek apakah bisa langsung diproses
            if self.active_jobs < self.max_concurrent:
                self.active_jobs += 1
                logger.info(f"Starting job {job_id} immediately (active: {self.active_jobs})")
                thread = threading.Thread(
                    target=self._process_job_with_context,
                    args=(job_id, url, file_path, base_filename, chunk_size_mb, bitrate)
                )
                thread.daemon = True
                thread.start()
                return True
            else:
                # Tambahkan ke antrian
                self.queue.append({
                    'job_id': job_id,
                    'url': url,
                    'file_path': file_path,
                    'base_filename': base_filename,
                    'chunk_size_mb': chunk_size_mb,
                    'bitrate': bitrate,
                    'added_time': time.time()
                })
                logger.info(f"Job {job_id} added to queue. Position: {len(self.queue)}")
                return False

    def _process_job_with_context(self, job_id, url=None, file_path=None, base_filename=None, chunk_size_mb=25,
                                  bitrate="192k"):
        """Proses job dengan Flask app context dan manajemen antrian"""
        global _app

        try:
            # Pastikan app tersedia
            if not _app:
                logger.error(f"Flask app not available for job {job_id}")
                raise RuntimeError("Flask app not set. Call set_app() first.")

            # Gunakan app context
            with _app.app_context():
                # Panggil fungsi proses konversi
                if url:
                    process_url_conversion(job_id, url, base_filename, chunk_size_mb, bitrate)
                elif file_path:
                    process_conversion(job_id, file_path, base_filename, chunk_size_mb, bitrate)
                else:
                    raise ValueError("Perlu URL atau file_path untuk memproses job")
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}")
        finally:
            # Proses job berikutnya dalam antrian jika ada
            with self.lock:
                self.active_jobs -= 1
                logger.info(f"Job {job_id} completed. Active jobs: {self.active_jobs}")

                if self.queue:
                    next_job = self.queue.pop(0)
                    self.active_jobs += 1
                    logger.info(f"Starting next job {next_job['job_id']} from queue")
                    thread = threading.Thread(
                        target=self._process_job_with_context,
                        args=(
                            next_job['job_id'],
                            next_job.get('url'),
                            next_job.get('file_path'),
                            next_job.get('base_filename'),
                            next_job.get('chunk_size_mb', 25),
                            next_job.get('bitrate', "192k")
                        )
                    )
                    thread.daemon = True
                    thread.start()

    def get_queue_status(self, job_id):
        """Dapatkan status job dalam antrian"""
        with self.lock:
            # Cek jika job sedang dalam antrian
            for i, job in enumerate(self.queue):
                if job['job_id'] == job_id:
                    return {'status': 'queued', 'position': i + 1, 'queue_length': len(self.queue)}

            # Periksa direktori temporary untuk melihat apakah job sedang diproses
            try:
                from flask import current_app
                temp_dir = os.path.join(current_app.config['TEMP_FOLDER'], job_id)
                if os.path.exists(temp_dir):
                    return {'status': 'processing', 'position': 0, 'queue_length': len(self.queue)}

                download_dir = os.path.join(current_app.config['TEMP_FOLDER'], f"{job_id}_download")
                if os.path.exists(download_dir):
                    return {'status': 'processing', 'position': 0, 'queue_length': len(self.queue)}
            except Exception as e:
                logger.error(f"Error checking job directories: {str(e)}")

            # Job tidak dalam antrian dan tidak sedang diproses, mungkin sudah selesai atau tidak ada
            return {'status': 'unknown', 'position': 0, 'queue_length': len(self.queue)}


# Inisialisasi queue manager
queue_manager = ConversionQueueManager(max_concurrent=3)


def add_to_conversion_queue(job_id, url=None, file_path=None, base_filename=None, chunk_size_mb=25, bitrate="192k"):
    """
    Fungsi untuk menambahkan job konversi ke antrian

    Args:
        job_id (str): ID unik untuk pekerjaan konversi
        url (str, optional): URL MP4 untuk didownload
        file_path (str, optional): Path ke file MP4 (jika sudah diupload)
        base_filename (str, optional): Nama file dasar untuk output
        chunk_size_mb (int): Ukuran potongan dalam MB
        bitrate (str): Bitrate untuk konversi audio

    Returns:
        bool: True jika diproses langsung, False jika masuk antrian
    """
    return queue_manager.add_job(job_id, url, file_path, base_filename, chunk_size_mb, bitrate)


def get_queue_status(job_id):
    """
    Dapatkan status job dalam antrian

    Args:
        job_id (str): ID pekerjaan

    Returns:
        dict: Informasi status antrian
    """
    return queue_manager.get_queue_status(job_id)


def process_url_conversion(job_id, url, base_filename=None, chunk_size_mb=25, bitrate="192k"):
    """
    Proses konversi MP4 dari URL ke MP3 dan potong hasilnya

    Args:
        job_id (str): ID unik untuk pekerjaan konversi
        url (str): URL file MP4 untuk didownload
        base_filename (str, optional): Nama file dasar untuk output
        chunk_size_mb (int): Ukuran potongan dalam MB
        bitrate (str): Bitrate untuk konversi audio
    """

    logger.info(f"Starting URL conversion job {job_id} for URL: {url}")

    # Define output directories
    temp_dir = os.path.join(current_app.config['TEMP_FOLDER'], job_id)
    result_dir = os.path.join(current_app.config['RESULT_FOLDER'], job_id)
    download_dir = os.path.join(current_app.config['TEMP_FOLDER'], f"{job_id}_download")

    # Create directories
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(result_dir, exist_ok=True)
    os.makedirs(download_dir, exist_ok=True)

    downloaded_file = None

    try:
        # Step 1: Download MP4 file
        logger.info(f"Downloading MP4 from URL: {url}")
        downloader = URLDownloader()
        downloaded_file = downloader.download(url, download_dir)

        # Validate downloaded file
        downloader.validate_file_type(downloaded_file)

        # Extract base filename if not provided
        if not base_filename:
            base_filename = os.path.splitext(os.path.basename(downloaded_file))[0]

        # Step 2: Convert MP4 to MP3
        logger.info(f"Converting MP4 to MP3: {downloaded_file}")
        converter = MP4ToMP3Converter(bitrate=bitrate)
        mp3_path = converter.convert(downloaded_file, temp_dir)

        # Step 3: Split MP3 into chunks
        logger.info(f"Splitting MP3 into {chunk_size_mb}MB chunks: {mp3_path}")
        splitter = MP3Splitter(max_size_mb=chunk_size_mb)
        output_files = splitter.split(mp3_path, result_dir, base_filename)

        # Log results
        logger.info(f"Conversion job {job_id} completed successfully")
        logger.info(f"Generated {len(output_files)} files:")
        for file_path in output_files:
            file_size = os.path.getsize(file_path) / (1024 * 1024)
            logger.info(f" - {os.path.basename(file_path)} ({file_size:.2f} MB)")

        # Cleanup: Delete downloaded file and temp dirs
        cleanup(job_id, downloaded_file, temp_dir, download_dir)

        return {
            'job_id': job_id,
            'status': 'completed',
            'files': len(output_files)
        }

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}")

        # Cleanup on failure
        cleanup(job_id, downloaded_file, temp_dir, download_dir)

        # Create error file in result directory
        error_file = os.path.join(result_dir, "error.txt")
        with open(error_file, 'w') as f:
            f.write(f"Conversion failed: {str(e)}")

        return {
            'job_id': job_id,
            'status': 'failed',
            'error': str(e)
        }


def process_conversion(job_id, file_path, base_filename=None, chunk_size_mb=25, bitrate="192k"):
    """
    Proses konversi MP4 ke MP3 dan potong hasilnya (untuk file yang sudah diupload)

    Args:
        job_id (str): ID unik untuk pekerjaan konversi
        file_path (str): Path ke file MP4
        base_filename (str, optional): Nama file dasar untuk output
        chunk_size_mb (int): Ukuran potongan dalam MB
        bitrate (str): Bitrate untuk konversi audio
    """
    logger.info(f"Starting conversion job {job_id} for file: {file_path}")

    # Define output directories
    temp_dir = os.path.join(current_app.config['TEMP_FOLDER'], job_id)
    result_dir = os.path.join(current_app.config['RESULT_FOLDER'], job_id)

    # Create directories
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(result_dir, exist_ok=True)

    try:
        uploaded_file = file_path
        # Extract base filename if not provided
        if not base_filename:
            base_filename = os.path.splitext(os.path.basename(file_path))[0]

        # Step 1: Convert MP4 to MP3
        logger.info(f"Converting MP4 to MP3: {file_path}")
        converter = MP4ToMP3Converter(bitrate=bitrate)
        mp3_path = converter.convert(file_path, temp_dir)

        # Step 2: Split MP3 into chunks
        logger.info(f"Splitting MP3 into {chunk_size_mb}MB chunks: {mp3_path}")
        splitter = MP3Splitter(max_size_mb=chunk_size_mb)
        output_files = splitter.split(mp3_path, result_dir, base_filename)

        # Log results
        logger.info(f"Conversion job {job_id} completed successfully")
        logger.info(f"Generated {len(output_files)} files:")
        for file_path in output_files:
            file_size = os.path.getsize(file_path) / (1024 * 1024)
            logger.info(f" - {os.path.basename(file_path)} ({file_size:.2f} MB)")

        # Cleanup: Delete the uploaded file
        logger.info(f"Cleaning up: {uploaded_file}")
        if os.path.exists(uploaded_file):
            os.remove(uploaded_file)

        # Cleanup: Delete temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)

        return {
            'job_id': job_id,
            'status': 'completed',
            'files': len(output_files)
        }

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}")

        # Cleanup on failure
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

        # Create error file in result directory
        error_file = os.path.join(result_dir, "error.txt")
        with open(error_file, 'w') as f:
            f.write(f"Conversion failed: {str(e)}")

        return {
            'job_id': job_id,
            'status': 'failed',
            'error': str(e)
        }


def cleanup(job_id, downloaded_file=None, temp_dir=None, download_dir=None):
    """
    Membersihkan file dan direktori sementara

    Args:
        job_id (str): ID pekerjaan
        downloaded_file (str, optional): Path ke file yang didownload
        temp_dir (str, optional): Direktori temporer
        download_dir (str, optional): Direktori download
    """
    # Hapus file yang didownload
    if downloaded_file and os.path.exists(downloaded_file):
        logger.info(f"Deleting downloaded file: {downloaded_file}")
        try:
            os.remove(downloaded_file)
        except Exception as e:
            logger.warning(f"Failed to delete downloaded file: {str(e)}")

    # Hapus direktori temporer
    for directory in [temp_dir, download_dir]:
        if directory and os.path.exists(directory):
            logger.info(f"Deleting temporary directory: {directory}")
            try:
                shutil.rmtree(directory, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to delete temporary directory: {str(e)}")