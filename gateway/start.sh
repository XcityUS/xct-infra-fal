#!/bin/sh
# Xcity Fal Gateway startup script
# Railway Start Command (if any) gets passed as args — we ignore them
# and always run uvicorn directly.
exec uvicorn gateway.main:app --host 0.0.0.0 --port "${PORT:-8080}"
