import os
import requests
from urllib.parse import urlparse, unquote
import tempfile
import shutil
from flask import current_app
from app.utils.logger import get_logger

logger = get_logger(__name__)


class URLDownloader:
    """Service untuk mendownload file dari URL"""

    def __init__(self, chunk_size=8192, timeout=30):
        """
        Initialize downloader

        Args:
            chunk_size (int): Ukuran chunk untuk streaming download
            timeout (int): Timeout request dalam detik
        """
        self.chunk_size = chunk_size
        self.timeout = timeout

    def download(self, url, output_folder, filename=None):
        """
        Download file dari URL ke output_folder

        Args:
            url (str): URL file yang akan didownload
            output_folder (str): Folder untuk menyimpan file
            filename (str, optional): Nama file output. Jika None, akan menggunakan nama file dari URL.

        Returns:
            str: Path ke file yang didownload

        Raises:
            ValueError: Jika URL tidak valid atau masalah downloading
        """
        # Validasi URL
        if not self._is_valid_url(url):
            logger.error(f"URL tidak valid: {url}")
            raise ValueError(f"URL tidak valid: {url}")

        # Pastikan folder output ada
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Tentukan nama file output
        output_filename = filename or self._get_filename_from_url(url)
        output_path = os.path.join(output_folder, output_filename)

        # Download file dengan streaming untuk menangani file besar
        try:
            logger.info(f"Mulai download dari: {url}")
            response = requests.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()  # Raise exception untuk status code error

            # Dapatkan ukuran total file jika tersedia
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            # Download dengan streaming ke file sementara
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:  # filter chunk kosong
                        temp_file.write(chunk)
                        downloaded += len(chunk)

                        # Log progress untuk file besar
                        if total_size > 0 and downloaded % (5 * 1024 * 1024) == 0:  # Log setiap 5MB
                            progress = (downloaded / total_size) * 100
                            logger.info(
                                f"Download progress: {progress:.1f}% ({downloaded / (1024 * 1024):.1f}MB/{total_size / (1024 * 1024):.1f}MB)")

            # Pindahkan file sementara ke lokasi tujuan
            shutil.move(temp_file.name, output_path)
            logger.info(f"Download selesai: {output_path} ({os.path.getsize(output_path) / (1024 * 1024):.2f}MB)")

            return output_path

        except requests.RequestException as e:
            logger.error(f"Error downloading file: {str(e)}")
            # Hapus file sementara jika ada
            if 'temp_file' in locals() and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            raise ValueError(f"Gagal mendownload file: {str(e)}")

    def _is_valid_url(self, url):
        """Validasi format URL"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def _get_filename_from_url(self, url):
        """Ekstrak nama file dari URL"""
        parsed_url = urlparse(url)
        path = unquote(parsed_url.path)
        filename = os.path.basename(path)

        # Jika tidak ada filename atau extension, gunakan nama default
        if not filename or not os.path.splitext(filename)[1]:
            filename = "downloaded_video.mp4"

        return filename

    def validate_file_type(self, file_path):
        """
        Validasi tipe file yang didownload

        Args:
            file_path (str): Path ke file

        Returns:
            bool: True jika file valid

        Raises:
            ValueError: Jika file bukan MP4
        """
        # Cek ekstensi file
        ext = os.path.splitext(file_path)[1].lower()
        if ext != '.mp4':
            logger.error(f"File bukan MP4: {file_path} (ekstensi: {ext})")
            # Hapus file yang tidak valid
            if os.path.exists(file_path):
                os.remove(file_path)
            raise ValueError(f"File bukan MP4. Hanya file MP4 yang didukung.")

        # Cek ukuran file
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            logger.error(f"File kosong: {file_path}")
            os.remove(file_path)
            raise ValueError("File yang didownload kosong")

        # Validasi tambahan bisa ditambahkan di sini, seperti memeriksa header file

        return True