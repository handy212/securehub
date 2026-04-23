#!/bin/bash
# SecureHub — production deploy script
# Run this on your server after git pull.
# Usage: ./deploy.sh [--full]   (--full rebuilds images from scratch)
set -euo pipefail

COMPOSE="docker compose -f docker-compose.prod.yml"

echo "▶  Pulling latest code..."
git pull --ff-only

echo "▶  Building images..."
if [[ "${1:-}" == "--full" ]]; then
    $COMPOSE build --no-cache
else
    $COMPOSE build
fi

echo "▶  Starting / updating services..."
$COMPOSE up -d --remove-orphans

echo "▶  Running migrations..."
$COMPOSE exec web python manage.py migrate --noinput

echo "▶  Collecting static files..."
$COMPOSE exec web python manage.py collectstatic --noinput --clear

echo "▶  Restarting web workers to pick up code changes..."
$COMPOSE restart web celery-worker celery-beat

echo ""
echo "✅  Deploy complete. Checking service health..."
$COMPOSE ps
