#!/usr/bin/env python
import os
from app import create_app
from celery import Celery

# Create Flask app
flask_app = create_app()

# Initialize Celery
celery = Celery(__name__)
celery.conf.update(flask_app.config)

class ContextTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with flask_app.app_context():
            return self.run(*args, **kwargs)

celery.Task = ContextTask

# Import tasks to register them with this celery instance
from app.tasks import process_conversion