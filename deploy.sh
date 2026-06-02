#!/bin/bash
# SecureHub — production deploy script
# Run this on your server after git pull.
# Usage: ./deploy.sh [--full]   (--full rebuilds images from scratch)
set -euo pipefail

COMPOSE="docker compose --env-file backend/.env.production -f docker-compose.prod.yml"

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
$COMPOSE exec -T web python manage.py migrate --noinput

echo "▶  Production configuration checks..."
$COMPOSE exec -T web python manage.py check --deploy

echo "▶  Collecting static files..."
$COMPOSE exec -T web python manage.py collectstatic --noinput --clear

echo "▶  Restarting web workers to pick up code changes..."
$COMPOSE restart web celery-worker celery-webhook celery-beat

echo "▶  Waiting for health check..."
for i in 1 2 3 4 5 6 7 8 9 10; do
    if $COMPOSE exec -T web curl -sf http://127.0.0.1:8000/healthz/ >/dev/null; then
        echo "✅  /healthz/ OK"
        break
    fi
    if [[ "$i" -eq 10 ]]; then
        echo "error: /healthz/ did not return 200 after deploy" >&2
        $COMPOSE logs --tail=50 web
        exit 1
    fi
    sleep 3
done

echo ""
echo "✅  Deploy complete. Service status:"
$COMPOSE ps
