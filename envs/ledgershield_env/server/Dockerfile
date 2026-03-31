ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# THE FIX: We copy the files into a proper package directory
# This allows 'from ..models' to successfully go up one level!
COPY . /app/ledgershield_env/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir openenv-core uvicorn pydantic fastapi requests pyyaml huggingface_hub openai

ENV PYTHONPATH=/app

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# THE FIX: We boot the app using the full package path
CMD ["python", "-m", "uvicorn", "ledgershield_env.server.app:app", "--host", "0.0.0.0", "--port", "8000"]