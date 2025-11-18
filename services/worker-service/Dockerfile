FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
COPY ../../shared /app/shared
COPY ../swing-engine /app/swing-engine
COPY ../sr-engine /app/sr-engine
COPY ../fib-entry-engine /app/fib-entry-engine
COPY ../confluence-engine /app/confluence-engine
COPY ../risk-engine /app/risk-engine
COPY ../storage-service /app/storage-service

# Run Celery worker
CMD ["celery", "-A", "main", "worker", "--loglevel=info"]

