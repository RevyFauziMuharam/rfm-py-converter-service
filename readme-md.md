# MP4 to MP3 Converter API

API untuk mengkonversi file MP4 ke MP3 dan memotongnya menjadi bagian-bagian dengan ukuran maksimum yang ditentukan.

## Fitur

- Konversi file MP4 ke format MP3
- Pemotongan file MP3 menjadi beberapa bagian dengan ukuran maksimum yang ditentukan
- REST API untuk interaksi dengan layanan
- Pemrosesan asynchronous dengan Celery
- Pelacakan status konversi
- Download hasil konversi

## Persyaratan Sistem

- Python 3.7 atau lebih baru
- FFmpeg
- Redis (untuk Celery)

## Instalasi

### Menggunakan Docker (Disarankan)

1. Clone repository
   ```bash
   git clone https://github.com/username/mp4-to-mp3-converter-api.git
   cd mp4-to-mp3-converter-api
   ```

2. Salin file konfigurasi
   ```bash
   cp .env.example .env
   ```

3. Jalankan dengan Docker Compose
   ```bash
   docker-compose up -d
   ```

### Instalasi Manual

1. Clone repository
   ```bash
   git clone https://github.com/username/mp4-to-mp3-converter-api.git
   cd mp4-to-mp3-converter-api
   ```

2. Buat virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # atau
   venv\Scripts\activate     # Windows
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Salin file konfigurasi
   ```bash
   cp .env.example .env
   ```

5. Jalankan Redis
   ```bash
   # Jika menggunakan Docker
   docker run -d -p 6379:6379 redis:alpine
   ```

6. Jalankan Celery worker
   ```bash
   celery -A celery_worker.celery worker --loglevel=info
   ```

7. Jalankan aplikasi Flask
   ```bash
   flask run
   ```

## Penggunaan API

### Mengkonversi file MP4 ke MP3

**Request:**
```
POST /api/conversion
```

Form-data:
- `file`: File MP4 (wajib)
- `chunk_size`: Ukuran maksimum per bagian dalam MB (opsional, default: 25)
- `bitrate`: Bitrate audio (opsional, default: 192k)

**Response:**
```json
{
  "job_id": "7e9d5e3e-9f1a-4b8c-8f9c-8f9c8f9c8f9c",
  "filename": "example.mp4",
  "file_size": 10485760,
  "status": "processing"
}
```

### Memeriksa status konversi

**Request:**
```
GET /api/conversion/{job_id}
```

**Response:**
```json
{
  "job_id": "7e9d5e3e-9f1a-4b8c-8f9c-8f9c8f9c8f9c",
  "status": "completed",
  "files": [
    {
      "filename": "example_part1.mp3",
      "size": 20971520,
      "download_url": "/api/download/7e9d5e3e-9f1a-4b8c-8f9c-8f9c8f9c8f9c/example_part1.mp3"
    },
    {
      "filename": "example_part2.mp3",
      "size": 15728640,
      "download_url": "/api/download/7e9d5e3e-9f1a-4b8c-8f9c-8f9c8f9c8f9c/example_part2.mp3"
    }
  ]
}
```

### Mengunduh file hasil konversi

**Request:**
```
GET /api/download/{job_id}/{filename}
```

**Response:**
File MP3 untuk diunduh.

## Dokumentasi Lebih Lanjut

Untuk informasi lebih detail tentang konfigurasi dan penggunaan lanjutan, silakan lihat dokumentasi di direktori `docs/`.

## Lisensi

[MIT License](LICENSE)
