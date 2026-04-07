---
title: LedgerShield
emoji: "🛡️"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
pinned: false
tags:
  - openenv
  - fastapi
  - docker
  - agents
  - finance
  - enterprise-risk
---

# LedgerShield

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![OpenEnv](https://img.shields.io/badge/OpenEnv-compatible-green.svg)]()

**LedgerShield** is a stateful, adversarial enterprise payment-integrity environment for training and evaluating AI agents in realistic high-stakes financial operations.

## Overview

LedgerShield simulates an accounts-payable control tower where AI agents must:

- **Investigate** multimodal payment cases under uncertainty
- **Unlock evidence** through targeted interventions
- **Apply controls** like callback verification and security routing
- **Submit decisions** with proof-carrying evidence (`PAY`, `HOLD`, `NEEDS_REVIEW`, `ESCALATE_FRAUD`)

Unlike static document benchmarks, LedgerShield models the complete operational loop with partial observability, budget constraints, and adversarial pressure events.

## Problem Framing

Business Email Compromise and AP payment fraud caused more than `$2.9 billion` in reported losses in `2023` alone, according to the [FBI Internet Crime Complaint Center (IC3) 2023 Internet Crime Report](https://www.ic3.gov/AnnualReport/Reports/2023_ic3report.pdf). That makes enterprise payment integrity one of the highest-stakes operational domains for AI agent evaluation.

LedgerShield is designed around the control failures that matter in that setting:

- spoofed vendor communications and bank-change pressure
- partial observability across invoices, emails, ledgers, and vendor history
- out-of-band verification such as callback checks to trusted numbers
- decision quality measured by downstream operational and fraud outcomes, not just classification accuracy

## Key Features

| Feature | Description |
|---------|-------------|
| **Stateful Environment** | POMDP-based with hidden risk signals and revealed artifacts |
| **Multi-Modal Evidence** | Invoices, emails, vendor records, POs, receipts, ledger history |
| **Intervention System** | 9 enterprise interventions that unlock additional evidence |
| **Adversarial Cases** | Replayable attack patterns including spoofing and threshold evasion |
| **Trajectory Grading** | Scores investigation quality, calibration, and downstream outcomes |
| **OpenEnv Compatible** | Standard `reset()`, `step()`, `state()` API with FastAPI runtime |

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (optional)
- Hugging Face API token (optional for deterministic smoke tests, required for real external LLM evaluation)

### Installation

```bash
# Clone the repository
git clone https://github.com/BiradarScripts/Meta-s-LedgerShield.git
cd Meta-s-LedgerShield

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
pip install -r requirements.txt
```

### Run the Environment

```bash
# Start the server
python -m server.app

# In another terminal, run the baseline agent
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="openai/gpt-4.1-mini"
export HF_TOKEN="your_token_here"
export ENV_URL="http://127.0.0.1:8000"

python inference.py
```

### Run stochastic pass^k evaluation

```bash
python inference.py \
  --env-url http://127.0.0.1:8000 \
  --model openai/gpt-4.1-mini \
  --temperature 0.6 \
  --passK 3
```

Set `HF_TOKEN` to run this with a real external LLM agent. Without a token, `inference.py` intentionally falls back to the deterministic policy so local smoke tests still work.

### Generate leaderboard and benchmark artifacts

```bash
python benchmark_report.py \
  --format markdown \
  --pass-k 3 \
  --temperature 0.6
```

Use `benchmark_report.py` for holdout reporting and leaderboard publication. It stays deterministic without credentials, and it upgrades to a real `llm-agent` evaluation automatically when `HF_TOKEN` is available.

### Docker Deployment

```bash
# Build and run
docker build -t ledgershield .
docker run -p 8000:8000 ledgershield
```

## Documentation

Comprehensive documentation is available in the [`docs/`](./docs) directory:

- **[Overview & Getting Started](./docs/index.md)** - Project overview and quickstart
- **[Architecture](./docs/architecture.md)** - System design, data flow, and component interactions
- **[API Reference](./docs/api-reference.md)** - Complete API documentation
- **[Task Reference](./docs/tasks.md)** - Detailed task descriptions and scoring
- **[Development Guide](./docs/development.md)** - Setup, testing, and development guidelines
- **[Deployment Guide](./docs/deployment.md)** - Production deployment instructions

## Task Suite

LedgerShield includes 5 task families across 12 curated benchmark cases:

| Task | Focus | Cases | Difficulty |
|------|-------|-------|------------|
| **Task A** | Proof-carrying field extraction | 2 | Easy-Medium |
| **Task B** | Three-way match decisioning | 3 | Easy-Medium |
| **Task C** | Duplicate and fraud triage | 2 | Medium-Hard |
| **Task D** | AP inbox incident triage | 4 | Hard |
| **Task E** | Campaign-level threshold evasion | 1 | Expert |

See [Task Reference](./docs/tasks.md) for complete details.

## Benchmark Results

Verified baseline performance on the 12-case public benchmark suite:

| Metric | Value |
|--------|-------|
| **Mean Score** | 0.9674 |
| **Pass@1 (0.85 threshold)** | 100% |
| **Task A Average** | 0.9900 |
| **Task D Average** | 0.9588 |
| **Task E Average** | 0.9817 |

Deterministic holdout reporting on the current codebase:

| Metric | Value |
|--------|-------|
| **Public Mean** | 0.9674 |
| **Public pass^1 consistent @ 0.85** | 1.0000 |
| **Generated Holdout Mean** | 0.6649 |
| **Generated Holdout pass^1 consistent @ 0.85** | 0.6190 |
| **Contrastive Joint Mean** | 0.6639 |

Published leaderboard snapshot:

| Model | Type | Temp | pass^k | Holdout Mean | Holdout pass^k consistent | Task E Expert Mean | Provenance |
|-------|------|------:|-------:|-------------:|--------------------------:|-------------------:|------------|
| `openai/gpt-4.1-mini` | `deterministic-policy` | 0.0 | 1 | 0.6649 | 0.6190 | 0.9817 | generated locally from `benchmark_report.py` |
| `openai/gpt-4.1-mini` | `llm-agent` | 0.6 | 3 | 0.3847 | 0.2222 | 0.2891 | published external run in `artifacts/leaderboard.json` |

This split is deliberate and mirrors the reliability framing used by [τ-bench](https://arxiv.org/abs/2406.12045): the deterministic baseline stays reproducible without credentials, while the stochastic row demonstrates remaining headroom for real external agents under repeated-trial `pass^k` evaluation.

Full results are available through [benchmark_report.py](./benchmark_report.py), [`artifacts/benchmark_report_latest.json`](./artifacts/benchmark_report_latest.json), and [`artifacts/leaderboard.json`](./artifacts/leaderboard.json).

## Project Structure

```
Meta-s-LedgerShield/
├── server/                 # FastAPI application and environment
│   ├── app.py             # FastAPI entrypoint
│   ├── environment.py     # Core environment implementation
│   ├── grading.py         # Task-specific scoring
│   ├── tools.py           # Investigation tools
│   ├── fixtures/          # Test data and cases
│   └── ...
├── docs/                   # Documentation
├── models.py              # Pydantic data models
├── inference.py           # Baseline agent implementation
├── benchmark_report.py    # Benchmark reporting tool
├── tests/                 # Test suite
├── Dockerfile             # Container configuration
├── pyproject.toml         # Package configuration
└── openenv.yaml          # OpenEnv runtime metadata
```

## API Endpoints

```
POST /reset              # Initialize a new episode
POST /step               # Execute an action
GET  /state              # Get current environment state
GET  /health             # Health check
GET  /leaderboard        # Latest benchmark results
GET  /benchmark-report   # Full benchmark report
```

See [API Reference](./docs/api-reference.md) for detailed endpoint documentation.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_BASE_URL` | LLM API base URL | `https://router.huggingface.co/v1` |
| `MODEL_NAME` | Model identifier | `openai/gpt-4.1-mini` |
| `HF_TOKEN` | Hugging Face API token for real external LLM runs | Optional |
| `ENV_URL` | Environment server URL | `http://127.0.0.1:8000` |
| `PORT` | Server port | `8000` |

## Testing

```bash
# Run all tests
python -m pytest -q

# Run specific test file
python -m pytest tests/test_ledgershield_env.py -v

# Validate the environment
openenv validate

# Run grader validation
python validate_grader.py
```

## Acknowledgments

Built for the [Meta OpenEnv Hackathon](https://facebook.com).

## Support

- 📖 [Documentation](./docs)
- 🐛 [Issue Tracker](https://github.com/BiradarScripts/Meta-s-LedgerShield/issues)

---

**Note**: This environment is designed for research and benchmarking purposes. It simulates financial operations but does not process real financial transactions.
