#!/bin/sh
set -e

# Verify database connection and apply migrations when starting the API application
if [ "$1" = "uvicorn" ]; then
    echo "[entrypoint] Checking database readiness..."
    python - <<'EOF'
import sys
import time
from app.core.config import settings
from sqlalchemy import create_engine, text

TOTAL_DEADLINE_SECONDS = 30.0
CONNECT_TIMEOUT_SECONDS = 2.0
SLEEP_INTERVAL_SECONDS = 1.0

deadline = time.monotonic() + TOTAL_DEADLINE_SECONDS
ready = False

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    connect_args={"connect_timeout": int(CONNECT_TIMEOUT_SECONDS)},
)

while time.monotonic() < deadline:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        ready = True
        break
    except Exception:
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(SLEEP_INTERVAL_SECONDS, remaining))

if ready:
    print("[entrypoint] Database connection verified.")
    sys.exit(0)
else:
    print(
        "[entrypoint] Database readiness check failed: database unreachable within 30s deadline.",
        file=sys.stderr,
    )
    sys.exit(1)
EOF

    echo "[entrypoint] Running database migrations..."
    alembic upgrade head
    echo "[entrypoint] Database migrations applied successfully."
fi

echo "[entrypoint] Executing application command: $@"
exec "$@"
