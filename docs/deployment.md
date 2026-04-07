# Deployment Guide

Guide for deploying LedgerShield in various environments.

## Table of Contents

- [Local Deployment](#local-deployment)
- [Docker Deployment](#docker-deployment)
- [Hugging Face Spaces](#hugging-face-spaces)
- [Production Deployment](#production-deployment)
- [Environment Variables](#environment-variables)
- [Monitoring and Logging](#monitoring-and-logging)
- [Troubleshooting](#troubleshooting)

## Local Deployment

### Quick Start

```bash
# 1. Clone repository
git clone https://github.com/BiradarScripts/Meta-s-LedgerShield.git
cd Meta-s-LedgerShield

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -e .
pip install -r requirements.txt

# 4. Run server
python -m server.app
```

The server will start on `http://localhost:8000`.

### Systemd Service (Linux)

Create a systemd service for production use:

```ini
# /etc/systemd/system/ledgershield.service
[Unit]
Description=LedgerShield Environment Server
After=network.target

[Service]
Type=simple
User=ledgershield
WorkingDirectory=/opt/ledgershield
Environment=PYTHONPATH=/opt/ledgershield
Environment=PORT=8000
Environment=HOST=0.0.0.0
ExecStart=/opt/ledgershield/.venv/bin/python -m server.app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ledgershield
sudo systemctl start ledgershield
sudo systemctl status ledgershield
```

### PM2 (Node.js Process Manager)

```json
// ecosystem.config.js
module.exports = {
  apps: [{
    name: 'ledgershield',
    cwd: '/opt/ledgershield',
    script: '.venv/bin/python',
    args: '-m server.app',
    env: {
      PYTHONPATH: '/opt/ledgershield',
      PORT: 8000,
      HOST: '0.0.0.0'
    },
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G'
  }]
}
```

Start with PM2:

```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

## Docker Deployment

### Build Image

```bash
docker build -t ledgershield:latest .
```

### Run Container

```bash
docker run -d \
  --name ledgershield \
  -p 8000:8000 \
  --restart unless-stopped \
  ledgershield:latest
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  ledgershield:
    build: .
    container_name: ledgershield
    ports:
      - "8000:8000"
    environment:
      - PORT=8000
      - HOST=0.0.0.0
      - LEDGERSHIELD_INCLUDE_HOLDOUT=0
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

Deploy:

```bash
docker-compose up -d
```

### Multi-Stage Build (Optimized)

```dockerfile
# Dockerfile.optimized
FROM python:3.11-slim as builder

WORKDIR /app
RUN pip install --user --no-cache-dir \
    fastapi uvicorn pydantic requests pyyaml httpx

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ledgershield
  labels:
    app: ledgershield
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ledgershield
  template:
    metadata:
      labels:
        app: ledgershield
    spec:
      containers:
      - name: ledgershield
        image: ledgershield:latest
        ports:
        - containerPort: 8000
        env:
        - name: PORT
          value: "8000"
        - name: HOST
          value: "0.0.0.0"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: ledgershield-service
spec:
  selector:
    app: ledgershield
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: ClusterIP
```

Apply:

```bash
kubectl apply -f k8s-deployment.yaml
```

## Hugging Face Spaces

### Setup

1. **Create a new Space** on Hugging Face:
   - Select "Docker" as SDK
   - Name it (e.g., "ledgershield")

2. **Clone the Space**:

```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/ledgershield
```

3. **Push the code**:

```bash
cd Meta-s-LedgerShield
# Copy all files to the Space repo
cp -r * /path/to/ledgershield/
cd /path/to/ledgershield
git add .
git commit -m "Initial commit"
git push
```

4. **Configure Secrets** in Space Settings:
   - `API_BASE_URL`: `https://router.huggingface.co/v1`
   - `MODEL_NAME`: `openai/gpt-4.1-mini`
   - `HF_TOKEN`: Your Hugging Face token

5. **Add OpenEnv tag** to Space metadata

### Space Configuration

Ensure `openenv.yaml` is in the root:

```yaml
spec_version: 1
name: ledgershield
type: space
runtime: fastapi
app: server.app:app
port: 8000
metadata:
  formal_model: pomdp
  horizon: finite
  observation: partial
```

### README Frontmatter

```markdown
---
title: LedgerShield
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
pinned: false
tags:
  - openenv
  - fastapi
  - agents
  - finance
---
```

## Production Deployment

### Reverse Proxy (Nginx)

```nginx
# /etc/nginx/sites-available/ledgershield
server {
    listen 80;
    server_name ledgershield.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

Enable:

```bash
sudo ln -s /etc/nginx/sites-available/ledgershield /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL/TLS (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d ledgershield.example.com
```

### Load Balancing

For multiple instances:

```nginx
upstream ledgershield {
    least_conn;
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    location / {
        proxy_pass http://ledgershield;
        # ... proxy settings
    }
}
```

## Environment Variables

### Required Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PORT` | Server port | `8000` | No |
| `HOST` | Bind address | `0.0.0.0` | No |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LEDGERSHIELD_DEBUG` | Enable debug mode | `0` |
| `LEDGERSHIELD_INCLUDE_HOLDOUT` | Include holdout cases | `0` |
| `LEDGERSHIELD_HOLDOUT_SEED` | Holdout generation seed | `31415` |
| `LEDGERSHIELD_HOLDOUT_VARIANTS` | Variants per holdout case | `1` |
| `LEDGERSHIELD_INCLUDE_CHALLENGE` | Include challenge variants | `0` |
| `LEDGERSHIELD_CHALLENGE_SEED` | Challenge generation seed | `42` |
| `LEDGERSHIELD_INCLUDE_TWINS` | Include benign twins | `0` |

### Client Variables (for inference.py)

| Variable | Description | Required |
|----------|-------------|----------|
| `API_BASE_URL` | LLM API base URL | Yes |
| `MODEL_NAME` | Model identifier | Yes |
| `HF_TOKEN` | Hugging Face token | Yes |
| `OPENAI_API_KEY` | OpenAI API key (fallback) | No |
| `ENV_URL` | Environment server URL | Yes |

### Example .env File

```bash
# Server configuration
PORT=8000
HOST=0.0.0.0

# Debug mode
LEDGERSHIELD_DEBUG=0

# Case generation
LEDGERSHIELD_INCLUDE_HOLDOUT=0
LEDGERSHIELD_INCLUDE_CHALLENGE=0

# Client configuration (for inference)
API_BASE_URL=https://router.huggingface.co/v1
MODEL_NAME=openai/gpt-4.1-mini
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx
ENV_URL=http://localhost:8000
```

## Monitoring and Logging

### Structured Logging

```python
# server/logging_config.py
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    logHandler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s'
    )
    logHandler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.addHandler(logHandler)
    logger.setLevel(logging.INFO)
```

### Health Checks

```python
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "cases_loaded": len(env.db["cases"]),
        "active_episodes": active_count
    }
```

### Metrics (Prometheus)

```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
REQUEST_COUNT = Counter('ledgershield_requests_total', 'Total requests')
REQUEST_LATENCY = Histogram('ledgershield_request_duration_seconds', 'Request latency')
EPISODE_COUNT = Counter('ledgershield_episodes_total', 'Total episodes')

@app.get("/metrics")
def metrics():
    return generate_latest()
```

### Log Aggregation

Send logs to centralized system:

```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  ledgershield:
    logging:
      driver: "fluentd"
      options:
        fluentd-address: localhost:24224
        tag: docker.ledgershield
```

## Troubleshooting

### Server Won't Start

**Check logs:**

```bash
# Docker
docker logs ledgershield

# Systemd
sudo journalctl -u ledgershield -f

# Manual
python -m server.app 2>&1 | tee server.log
```

**Common causes:**
- Port already in use: Change `PORT` environment variable
- Missing dependencies: Run `pip install -e .`
- Permission errors: Check file permissions

### High Memory Usage

**Solutions:**
- Reduce concurrent episodes
- Enable garbage collection
- Use process pool instead of threads

```python
# Limit memory
import resource
resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, -1))  # 2GB
```

### Slow Response Times

**Check:**
- CPU usage: `htop`
- Disk I/O: `iostat`
- Network latency: `ping`

**Optimizations:**
- Use connection pooling
- Enable response caching
- Add load balancer

### Case Not Found

```bash
# Verify fixtures are loaded
python -c "from server.data_loader import load_all; db = load_all(); print(len(db['cases']), 'cases loaded')"
```

### API Errors

**Enable debug mode:**

```bash
export LEDGERSHIELD_DEBUG=1
python -m server.app
```

**Test endpoints:**

```bash
# Health check
curl http://localhost:8000/health

# Reset episode
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"case_id": "CASE-A-001"}'
```

## Security Considerations

### Network Security

- Use firewall rules to restrict access
- Deploy behind reverse proxy with SSL
- Use VPN for internal deployments

### Application Security

```python
# Rate limiting
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/reset")
@limiter.limit("10/minute")
def reset(request: Request, ...):
    ...
```

### Data Security

- No sensitive data in fixtures (use synthetic data)
- No logging of PII
- Encrypt environment variables

## Backup and Recovery

### Backup Fixtures

```bash
# Create backup
tar -czf ledgershield-backup-$(date +%Y%m%d).tar.gz server/fixtures/

# Restore
tar -xzf ledgershield-backup-20260407.tar.gz
```

### Database Backup (if using external DB)

```bash
# MongoDB example
mongodump --db ledgershield --out /backup/

# Restore
mongorestore --db ledgershield /backup/ledgershield/
```

## Scaling

### Horizontal Scaling

Deploy multiple instances behind load balancer:

```
Load Balancer
    ├── Instance 1 (Port 8000)
    ├── Instance 2 (Port 8001)
    └── Instance 3 (Port 8002)
```

### Vertical Scaling

Increase resources:

```yaml
# docker-compose.yml
services:
  ledgershield:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
```

## Maintenance

### Regular Tasks

- Update dependencies monthly
- Review logs weekly
- Monitor disk space
- Check SSL certificate expiration

### Updates

```bash
# Update code
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart ledgershield
```

## Support

For deployment issues:

1. Check [Troubleshooting](#troubleshooting) section
2. Review server logs
3. Search [GitHub Issues](https://github.com/BiradarScripts/Meta-s-LedgerShield/issues)
4. Create new issue with deployment details
