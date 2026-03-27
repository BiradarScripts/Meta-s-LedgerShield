# Use a standard, reliable Python image
ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

WORKDIR /app

# Install system dependencies needed for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire project into the container
COPY . /app

# Install the core requirements and your project dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir openenv-core uvicorn pydantic && \
    pip install --no-cache-dir -r envs/ledgershield_env/server/requirements.txt

# Set the Python path so it can find your modules
ENV PYTHONPATH=/app/envs

# Healthcheck to let Docker know when the API is ready
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the server using the path that matched your successful terminal test
CMD ["python", "-m", "uvicorn", "ledgershield_env.server.app:app", "--host", "0.0.0.0", "--port", "8000"]