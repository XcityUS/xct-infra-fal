FROM python:3.11-slim

WORKDIR /app

# Install system deps if needed (none for now)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy gateway code
COPY gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gateway/pyproject.toml /app/
COPY gateway/src /app/src

# Install the local package (so `gateway` module resolves)
RUN pip install -e /app

# Railway provides PORT env var; default to 8080
ENV PORT=8080
EXPOSE 8080

CMD uvicorn gateway.main:app --host 0.0.0.0 --port ${PORT}
