ARG BASE_IMAGE=openenv-base:latest
FROM ${BASE_IMAGE}

COPY envs/ledgershield_env/server/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY envs/ledgershield_env/ /app/envs/ledgershield_env/

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "envs.ledgershield_env.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
