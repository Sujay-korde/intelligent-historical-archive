FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (build-essential, libpq-dev for postgres, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY backend backend
COPY storage storage
COPY processing processing
COPY ai ai
COPY ingestion ingestion
COPY database database
COPY alembic.ini alembic.ini

# Expose port
EXPOSE 8000

# Run uvicorn
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
