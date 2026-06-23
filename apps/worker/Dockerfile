FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir -e .

CMD ["celery", "-A", "adrar_worker.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
