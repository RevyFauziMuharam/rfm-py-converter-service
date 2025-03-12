import os
import sys
from rq import Worker, Queue, Connection
from redis import Redis
from app import create_app

app = create_app()
app.app_context().push()

# Konfigurasi Redis dan RQ
redis_conn = Redis.from_url(app.config['REDIS_URL'])

# Pekerja bisa dijalankan dengan:
# python worker.py
if __name__ == '__main__':
    with Connection(redis_conn):
        worker = Worker(map(Queue, ['default', 'high', 'low']))
        worker.work()