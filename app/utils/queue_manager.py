import time
import threading
from flask import current_app
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QueueManager:
    def __init__(self):
        self.active_jobs = 0
        self.lock = threading.Lock()
        self.waiting_jobs = []

    def add_job(self, job_id, file_size, process_func, *args, **kwargs):
        """
        Tambahkan job ke antrian
        """
        with self.lock:
            # Cek apakah masih ada slot untuk konversi
            if self.active_jobs < current_app.config['MAX_CONCURRENT_CONVERSIONS']:
                # Jika file kecil atau antrian kosong, proses langsung
                if file_size < current_app.config['MAX_FILE_SIZE_FOR_INSTANT_PROCESSING'] or not self.waiting_jobs:
                    self.active_jobs += 1
                    threading.Thread(target=self._process_job,
                                     args=(job_id, process_func) + args,
                                     kwargs=kwargs).start()
                    return True

            # Tambahkan ke antrian untuk diproses nanti
            self.waiting_jobs.append({
                'job_id': job_id,
                'func': process_func,
                'args': args,
                'kwargs': kwargs,
                'added_time': time.time()
            })
            logger.info(f"Job {job_id} added to queue. Position: {len(self.waiting_jobs)}")
            return False

    def _process_job(self, job_id, process_func, *args, **kwargs):
        """
        Proses job dan jalankan job berikutnya dari antrian setelah selesai
        """
        try:
            logger.info(f"Processing job {job_id}")
            process_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}")
        finally:
            with self.lock:
                self.active_jobs -= 1
                # Cek apakah ada job berikutnya di antrian
                if self.waiting_jobs and self.active_jobs < current_app.config['MAX_CONCURRENT_CONVERSIONS']:
                    next_job = self.waiting_jobs.pop(0)
                    self.active_jobs += 1
                    threading.Thread(target=self._process_job,
                                     args=(next_job['job_id'], next_job['func']) + next_job['args'],
                                     kwargs=next_job['kwargs']).start()
                    logger.info(f"Started next job {next_job['job_id']} from queue")

    def get_queue_position(self, job_id):
        """
        Dapatkan posisi job dalam antrian
        """
        with self.lock:
            for i, job in enumerate(self.waiting_jobs):
                if job['job_id'] == job_id:
                    return i + 1
            return 0  # 0 berarti tidak dalam antrian (mungkin sudah aktif atau selesai)

    def get_active_count(self):
        """
        Dapatkan jumlah job yang sedang aktif
        """
        with self.lock:
            return self.active_jobs

    def get_queue_length(self):
        """
        Dapatkan panjang antrian
        """
        with self.lock:
            return len(self.waiting_jobs)


# Buat instance QueueManager
queue_manager = QueueManager()