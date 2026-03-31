FROM python:3.11-slim

WORKDIR /app

COPY . /app/ledgershield_env

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
      fastapi \
      uvicorn \
      pydantic \
      requests \
      pyyaml \
      httpx

ENV PYTHONPATH=/app

CMD ["python", "-m", "uvicorn", "ledgershield_env.server.app:app", "--host", "0.0.0.0", "--port", "8000"]