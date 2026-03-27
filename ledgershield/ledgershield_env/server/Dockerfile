ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

WORKDIR /app

# Combine apt-get commands and use line continuations
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

# Use line continuations for pip installs to ensure they run as one layer
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir openenv-core uvicorn && \
    pip install --no-cache-dir -r envs/ledgershield_env/server/requirements.txt

ENV PYTHONPATH=/app

# Fix Healthcheck syntax to properly execute the curl command
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the FastAPI server
CMD ["uvicorn", "envs.ledgershield_env.server.app:app", "--host", "0.0.0.0", "--port", "8000"]