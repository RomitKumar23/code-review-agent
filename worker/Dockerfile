FROM python:3.12-slim

WORKDIR /app

# Install dependencies (shared with api)
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy api source (worker imports from it)
COPY api/ ./api/

# Copy worker source
COPY worker/ ./worker/

# Set API_PATH so tasks.py knows where to find api modules
ENV API_PATH=/app/api

WORKDIR /app/worker
CMD ["celery", "-A", "tasks", "worker", "--loglevel=info", "--concurrency=2"]
