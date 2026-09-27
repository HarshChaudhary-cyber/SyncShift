# Backend container for the FastAPI SyncShift service.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Local OCR and legacy Word text extraction for timetable uploads.
RUN apt-get update && apt-get install -y --no-install-recommends antiword tesseract-ocr && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip && \
    python -m pip install -r /tmp/requirements.txt

COPY backend /app

# Run migrations then start the server.
# entrypoint.sh executes "alembic upgrade head" before uvicorn so that a fresh
# volume is initialised and an existing volume is safely migrated on every start.
COPY backend/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 8000

CMD ["/entrypoint.sh"]
