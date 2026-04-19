# Deployment Guide

This guide explains how to run LedgerShield locally, in Docker, or as a Docker-backed Hugging Face Space, and documents the runtime environment variables that control benchmark behavior.

## Deployment Modes

### Local Python process

Best for development and testing.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements.txt
python -m server.app
```

Default bind:

- host: `0.0.0.0`
- port: `8000`

Health check:

```bash
curl http://127.0.0.1:8000/health
```

### Docker

The repo ships with a ready-to-build [`../Dockerfile`](../Dockerfile).

Build:

```bash
docker build -t ledgershield:latest .
```

Run:

```bash
docker run --rm -p 8000:8000 ledgershield:latest
```

Smoke test:

```bash
curl http://127.0.0.1:8000/health
```

### Hugging Face Spaces

The root `README.md` includes Docker Space front matter, and `openenv.yaml` describes the benchmark metadata. For a Docker Space deployment:

1. create a new Hugging Face Space using the Docker SDK
2. push this repo contents to the Space
3. ensure the Space exposes port `8000`
4. verify `/health`, `/reset`, and `/step`

### CI-backed validation

GitHub Actions already validates:

- Python test runs
- Docker build and container smoke test
- `openenv.yaml` integrity

See [`../.github/workflows/ci.yml`](../.github/workflows/ci.yml).

## Runtime Environment Variables

### Server bind settings

| Variable | Default | Meaning |
|---|---|---|
| `HOST` | `0.0.0.0` | bind host used by `server.app:main` |
| `PORT` | `8000` | bind port used by `server.app:main` |

### Case-loader controls

These are read by [`../server/data_loader.py`](../server/data_loader.py).

| Variable | Default | Meaning |
|---|---|---|
| `LEDGERSHIELD_INCLUDE_CHALLENGE` | `true` | include generated challenge variants in the loaded case pool |
| `LEDGERSHIELD_CHALLENGE_VARIANTS` | `2` | number of generated challenge variants per hard case |
| `LEDGERSHIELD_CHALLENGE_SEED` | `2026` | RNG seed for challenge generation |
| `LEDGERSHIELD_INCLUDE_HOLDOUT` | `false` | include generated holdout cases in the loaded case pool |
| `LEDGERSHIELD_HOLDOUT_VARIANTS` | `1` | holdout variants per hard case |
| `LEDGERSHIELD_HOLDOUT_SEED` | `31415` | RNG seed for holdout generation |
| `LEDGERSHIELD_INCLUDE_TWINS` | `false` | include benign contrastive twins in the loaded case pool |
| `LEDGERSHIELD_TRACK_MODE` | `blind` | use `instrumented` to expose SPRT, VoI tool rankings, and reward-machine progress for diagnostics |

### Agent-side variables

Common variables used by `inference.py` and related scripts:

| Variable | Typical use |
|---|---|
| `API_BASE_URL` | OpenAI-compatible API endpoint |
| `MODEL_NAME` | model name for inference (determines `ModelCapabilityProfile` tier) |
| `HF_TOKEN` | token used by the submission-safe agent |
| `OPENAI_API_KEY` | credential for live comparison scripts |
| `ENV_URL` | environment server base URL |
| `LOCAL_IMAGE_NAME` | optional Docker image name for local environment use |
| `LEDGERSHIELD_DEBUG` | set to `1` to enable stderr output from the inference agent (default: stderr suppressed) |
| `LEDGERSHIELD_DEBUG_ARTIFACT_DIR` | directory for per-case live-comparison traces, including certificate and institutional metrics |

## Operational Checks

### Basic API checks

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/
```

### Reset a known case

```bash
curl -X POST http://127.0.0.1:8000/reset \
  -H 'Content-Type: application/json' \
  -d '{"case_id":"CASE-A-001"}'
```

### Run benchmark report generation locally

```bash
python benchmark_report.py --format markdown
```

Generated artifacts land under `artifacts/` when written.

## Recommended Deployment Profiles

### Minimal benchmark server

Use this when you only need the curated benchmark and generated challenge variants:

```bash
HOST=0.0.0.0 PORT=8000 python -m server.app
```

### Public benchmark only

Disable generated challenge variants:

```bash
LEDGERSHIELD_INCLUDE_CHALLENGE=0 python -m server.app
```

### Holdout-enabled evaluation server

```bash
LEDGERSHIELD_INCLUDE_HOLDOUT=1 \
LEDGERSHIELD_HOLDOUT_VARIANTS=1 \
python -m server.app
```

### Calibration-heavy server with twins

```bash
LEDGERSHIELD_INCLUDE_TWINS=1 python -m server.app
```

### Blind-track evaluation server

Hide benchmark-side decision scaffolding while preserving hidden grader state:

```bash
LEDGERSHIELD_TRACK_MODE=blind python -m server.app
```

## Production Notes

LedgerShield is still a benchmark, not a payment system. For production-like hosting:

- terminate TLS outside the app
- health-check `/health`
- treat the service as stateless and restartable
- version-control `openenv.yaml` and benchmark artifacts
- avoid mixing benchmark servers with live finance systems

## Troubleshooting

### Server starts but endpoints fail

Check:

- port `8000` is not already in use
- dependencies from `requirements.txt` are installed
- you are running from the repo root so fixture paths resolve correctly

### Docker container builds but health check fails

Check:

- `curl http://localhost:8000/health`
- container logs for import/path issues
- whether your host already has something bound to `8000`

### Unexpected case counts

Remember that the loader includes challenge variants by default. If you expect only the curated 21-case benchmark, set:

```bash
LEDGERSHIELD_INCLUDE_CHALLENGE=0
```

### Missing benchmark report endpoint data

`/benchmark-report` and `/leaderboard` only return rich artifacts after report generation. Run:

```bash
python benchmark_report.py --format json
```
