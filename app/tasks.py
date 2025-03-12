import os
import shutil
import time
import threading
from flask import current_app
from app.services.converter import MP4ToMP3Converter
from app.services.splitter import MP3Splitter
from app.utils.logger import get_logger

# Setup logger
logger = get_logger("tasks")


# Queue manager untuk mengelola jumlah konversi bersamaan
class ConversionQueueManager:
    def __init__(self, max_concurrent=3):
        self.max_concurrent = max_concurrent
        self.active_jobs = 0
        self.queue = []
        self.lock = threading.Lock()

    def add_job(self, job_id, file_path, base_filename, chunk_size_mb, bitrate):
        """Tambahkan job ke antrian dan proses jika memungkinkan"""
        with self.lock:
            # Cek apakah bisa langsung diproses
            if self.active_jobs < self.max_concurrent:
                self.active_jobs += 1
                logger.info(f"Starting job {job_id} immediately (active: {self.active_jobs})")
                thread = threading.Thread(
                    target=self._process_job_with_context,
                    args=(job_id, file_path, base_filename, chunk_size_mb, bitrate)
                )
                thread.daemon = True
                thread.start()
                return True
            else:
                # Tambahkan ke antrian
                self.queue.append({
                    'job_id': job_id,
                    'file_path': file_path,
                    'base_filename': base_filename,
                    'chunk_size_mb': chunk_size_mb,
                    'bitrate': bitrate,
                    'added_time': time.time()
                })
                logger.info(f"Job {job_id} added to queue. Position: {len(self.queue)}")
                return False

    def _process_job_with_context(self, job_id, file_path, base_filename, chunk_size_mb, bitrate):
        """Proses job dengan Flask app context dan manajemen antrian"""
        try:
            # Panggil fungsi proses konversi
            process_conversion(job_id, file_path, base_filename, chunk_size_mb, bitrate)
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
                            next_job['file_path'],
                            next_job['base_filename'],
                            next_job['chunk_size_mb'],
                            next_job['bitrate']
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

            # Job tidak dalam antrian, mungkin sedang aktif atau sudah selesai
            return {'status': 'unknown', 'position': 0, 'queue_length': len(self.queue)}


# Inisialisasi queue manager
queue_manager = ConversionQueueManager(max_concurrent=3)


def add_to_conversion_queue(job_id, file_path, base_filename, chunk_size_mb, bitrate):
    """
    Fungsi untuk menambahkan job konversi ke antrian

    Args:
        job_id (str): ID unik untuk pekerjaan konversi
        file_path (str): Path ke file MP4
        base_filename (str): Nama file dasar untuk output
        chunk_size_mb (int): Ukuran potongan dalam MB
        bitrate (str): Bitrate untuk konversi audio

    Returns:
        bool: True jika diproses langsung, False jika masuk antrian
    """
    return queue_manager.add_job(job_id, file_path, base_filename, chunk_size_mb, bitrate)


def get_queue_status(job_id):
    """
    Dapatkan status job dalam antrian

    Args:
        job_id (str): ID pekerjaan

    Returns:
        dict: Informasi status antrian
    """
    return queue_manager.get_queue_status(job_id)


def process_conversion(job_id, file_path, base_filename, chunk_size_mb=25, bitrate="192k"):
    """
    Proses konversi MP4 ke MP3 dan potong hasilnya

    Args:
        job_id (str): ID unik untuk pekerjaan konversi
        file_path (str): Path ke file MP4
        base_filename (str): Nama file dasar untuk output
        chunk_size_mb (int): Ukuran potongan dalam MB
        bitrate (str): Bitrate untuk konversi audio
    """
    # Import flask.current_app di sini agar bisa diakses dari thread
    from flask import current_app

    logger.info(f"Starting conversion job {job_id}")

    # Define output directories
    temp_dir = os.path.join(current_app.config['TEMP_FOLDER'], job_id)
    result_dir = os.path.join(current_app.config['RESULT_FOLDER'], job_id)

    # Create directories
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(result_dir, exist_ok=True)

    try:
        uploaded_file = file_path
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