ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY envs /app/envs
COPY inference.py /app/inference.py

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir openenv-core uvicorn fastapi pydantic requests pyyaml huggingface_hub openai

ENV PYTHONPATH=/app

CMD ["python", "-m", "uvicorn", "envs.ledgershield_env.server.app:app", "--host", "0.0.0.0", "--port", "8000"]