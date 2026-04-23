#!/bin/bash

# --- Configuration ---
VENV_PATH="./.venv"
LOG_DIR="./logs"

# --- Functions ---

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🛑 Shutting down all services..."
    # Kill all child processes of this script
    # 1. Kill the entire process group (including grandchildren like Django reloader)
    # We use a trap on EXIT to ensure this always runs.
    
    # Pre-emptive strike on known service names as a fallback
    pkill -f "manage.py runserver" 2>/dev/null
    pkill -f "celery -A config" 2>/dev/null
    pkill -f "ngrok http" 2>/dev/null
    
    # 2. Final cleanup of the process group
    # Note: kill -TERM -$$ kills the parent shell too, so it's the final action.
    trap - SIGINT SIGTERM EXIT # Prevent infinite recursion
    kill -TERM -$$ 2>/dev/null
    echo "✅ Done. Logs are available in $LOG_DIR"
    exit 0
}

# Trap Ctrl+C (SIGINT) and SIGTERM
trap cleanup SIGINT SIGTERM

# --- Initialization ---

echo "🚀 Starting SecureHub services in Unified Log Mode..."
mkdir -p "$LOG_DIR"

# Activate virtual environment if it exists
if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
fi

# --- Start Services (Redirecting to Logs) ---

echo "📡 Starting Django server..."
python manage.py runserver 0.0.0.0:8000 > "$LOG_DIR/django.log" 2>&1 &

echo "👷 Starting Celery worker..."
celery -A config worker -l info > "$LOG_DIR/worker.log" 2>&1 &

echo "⏱️  Starting Celery beat..."
celery -A config beat -l info > "$LOG_DIR/beat.log" 2>&1 &

echo "🌐 Starting ngrok..."
ngrok http 8000 > "$LOG_DIR/ngrok.log" 2>&1 &

# Give them a moment to start
sleep 3

echo "⚓ Registering webhook..."
python manage.py register_webhook > "$LOG_DIR/webhook.log" 2>&1 &

echo "----------------------------------------------------"
echo "All services are running in the background."
echo "Showing live unified logs below (Ctrl+C to stop all)"
echo "----------------------------------------------------"

# Follow all logs with prefixes (if tail supports it)
# We use a custom tail execution or just tail -f
tail -f "$LOG_DIR/django.log" \
        "$LOG_DIR/worker.log" \
        "$LOG_DIR/beat.log" \
        "$LOG_DIR/ngrok.log" \
        "$LOG_DIR/webhook.log"
