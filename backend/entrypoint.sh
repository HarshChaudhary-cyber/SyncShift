#!/bin/sh
# Docker container entrypoint for the SyncShift backend.
#
# Runs Alembic migrations before starting Uvicorn so that a fresh volume
# (empty database) is automatically initialised, and an existing database is
# safely brought up to the current head revision without manual intervention.
#
# Behaviour:
#   • Fresh database  → "alembic upgrade head" creates all tables + stamps head.
#   • Existing database at head  → no-op (idempotent).
#   • Existing database behind head  → applies pending migrations in order.
#   • Migration failure  → script exits non-zero; the container restarts (if
#     restart: unless-stopped) and retries rather than starting with a broken schema.

set -e

echo "[entrypoint] Running Alembic migrations..."
alembic upgrade head
echo "[entrypoint] Migrations complete. Starting Uvicorn..."

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
