#!/bin/bash
# SecureHub — PostgreSQL backup (run on the host via cron).
#
# Example cron (daily at 02:15):
#   15 2 * * * cd /opt/securehub && ./scripts/backup_postgres.sh >> /var/log/securehub-backup.log 2>&1
#
# Environment:
#   BACKUP_DIR   — output directory (default: ./backups)
#   RETAIN_DAYS  — delete dumps older than N days (default: 14)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE="docker compose --env-file backend/.env.production -f docker-compose.prod.yml"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
RETAIN_DAYS="${RETAIN_DAYS:-14}"

if [[ ! -f backend/.env.production ]]; then
  echo "error: backend/.env.production not found" >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a
source backend/.env.production
set +a

DB_USER="${DJANGO_DB_USER:-securehub}"
DB_NAME="${DJANGO_DB_NAME:-alarmhub}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${BACKUP_DIR}/postgres_${STAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "▶  Backing up ${DB_NAME} to ${OUT_FILE}..."
$COMPOSE exec -T db pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$OUT_FILE"

if [[ ! -s "$OUT_FILE" ]]; then
  echo "error: backup file is empty" >&2
  rm -f "$OUT_FILE"
  exit 1
fi

echo "✅  Backup complete ($(du -h "$OUT_FILE" | cut -f1))"

if [[ "$RETAIN_DAYS" -gt 0 ]]; then
  find "$BACKUP_DIR" -name 'postgres_*.sql.gz' -type f -mtime +"$RETAIN_DAYS" -delete
  echo "▶  Pruned dumps older than ${RETAIN_DAYS} days"
fi
