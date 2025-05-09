#!/bin/bash
set -e

# Create DB tables if they don't exist
python -c "from app import app; from database.models import db; app.app_context().push(); db.create_all()"

if [ "$1" = "web" ]; then
    # Run web server
    echo "Starting Flask web server..."
    gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 8 --timeout 120 wsgi:app
elif [ "$1" = "worker" ]; then
    # Run celery worker
    echo "Starting Celery worker..."
    celery -A tasks.celery_config.celery_app worker -l info -Q video,image
elif [ "$1" = "flower" ]; then
    # Run flower
    echo "Starting Flower monitoring..."
    celery -A tasks.celery_config.celery_app flower --port=5555 --address=0.0.0.0
else
    exec "$@"
fi