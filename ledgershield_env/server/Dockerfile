ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

# The path here is fixed!
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir openenv-core uvicorn && \
    pip install --no-cache-dir -r ledgershield_env/server/requirements.txt

ENV PYTHONPATH=/app

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# The uvicorn path here is also fixed!
CMD ["uvicorn", "ledgershield_env.server.app:app", "--host", "0.0.0.0", "--port", "8000"]