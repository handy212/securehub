#!/bin/sh
set -e

# Wait for Postgres to be ready
echo "Waiting for database..."
until python -c "
import os, psycopg
try:
    psycopg.connect(
        host=os.getenv('DJANGO_DB_HOST', 'db'),
        port=os.getenv('DJANGO_DB_PORT', '5432'),
        dbname=os.getenv('DJANGO_DB_NAME', 'alarmhub'),
        user=os.getenv('DJANGO_DB_USER', 'postgres'),
        password=os.getenv('DJANGO_DB_PASSWORD', ''),
    ).close()
except Exception:
    exit(1)
"; do
    echo "  Postgres unavailable — sleeping 2s"
    sleep 2
done
echo "Database is up."

case "$1" in
    gunicorn)
        python manage.py migrate --noinput
        exec gunicorn config.wsgi:application \
            --bind 0.0.0.0:8000 \
            --workers "${GUNICORN_WORKERS:-3}" \
            --timeout "${GUNICORN_TIMEOUT:-120}" \
            --access-logfile - \
            --error-logfile - \
            --log-level info
        ;;
    celery-worker)
        exec celery -A config worker \
            --loglevel=info \
            --queues="${CELERY_QUEUES:-celery}" \
            --concurrency="${CELERY_CONCURRENCY:-2}" \
            --prefetch-multiplier="${CELERY_WORKER_PREFETCH_MULTIPLIER:-1}"
        ;;
    celery-webhook)
        exec celery -A config worker \
            --loglevel=info \
            --queues=webhook \
            --hostname="webhook@%h" \
            --concurrency="${CELERY_WEBHOOK_CONCURRENCY:-2}" \
            --prefetch-multiplier=1
        ;;
    celery-beat)
        exec celery -A config beat \
            --loglevel=info \
            --schedule="${CELERY_BEAT_SCHEDULE_FILE:-/tmp/celerybeat-schedule}"
        ;;
    *)
        exec "$@"
        ;;
esac
