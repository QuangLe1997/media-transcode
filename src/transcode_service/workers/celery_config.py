import os
from celery import Celery
from ..core.config import get_config

# Initialize configuration
config = get_config()


def make_celery(app_name=__name__):
    # Create Celery app
    celery = Celery(
        app_name,
        broker=config.CELERY_BROKER_URL,
        backend=config.CELERY_RESULT_BACKEND
    )

    # Configure Celery
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        worker_pool="solo",
        task_time_limit=3600,  # 1 hour
        worker_max_tasks_per_child=100,
        worker_prefetch_multiplier=1,
    )

    # # Include tasks
    # celery.conf.task_routes = {
    #     'tasks.video_tasks.*': {'queue': 'video'},
    #     'tasks.image_tasks.*': {'queue': 'image'},
    # }

    return celery


# Create Celery app
celery_app = make_celery()