#!/bin/sh
# Xcity Fal Gateway startup script
# Railway Start Command (if any) gets passed as args — we ignore them
# and always run uvicorn directly.
echo "[start] PORT=${PORT:-8080}"
echo "[start] cwd=$(pwd)"
echo "[start] python=$(which python3)"
echo "[start] uvicorn=$(which uvicorn)"
python3 -c "import gateway; print('[start] gateway module ok')" || echo "[start] gateway module MISSING"
exec uvicorn gateway.main:app --host 0.0.0.0 --port "${PORT:-8080}"
