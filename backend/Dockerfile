FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps for psycopg (binary wheel) and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --timeout 120 --retries 10 -r requirements.txt

COPY . .

# Collect static files at build time (needs a placeholder SECRET_KEY)
RUN DJANGO_SECRET_KEY=build-placeholder \
    DJANGO_DEBUG=False \
    DJANGO_USE_SQLITE=False \
    python manage.py collectstatic --noinput

EXPOSE 8000

# entrypoint handles migrations then hands off to gunicorn / celery
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn"]
