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
[![CI](https://img.shields.io/badge/ci-github_actions-success.svg)](./.github/workflows/ci.yml)
[![OpenEnv](https://img.shields.io/badge/OpenEnv-compatible-green.svg)](./openenv.yaml)

LedgerShield is a stateful, adversarial benchmark for AI agents operating inside enterprise accounts-payable workflows. Instead of asking a model to classify one document, LedgerShield asks it to investigate, unlock hidden evidence, choose controls, withstand pressure, and submit a proof-carrying decision under budget and step limits.

## Why This Matters

Real-world payment fraud is expensive and operationally messy. In the FBI IC3 2023 report, business email compromise (BEC) generated **21,489 complaints and more than $2.9 billion in reported losses**, while total cybercrime losses exceeded **$12.5 billion**. LedgerShield turns that risk surface into an agent benchmark focused on safe decision-making, evidence quality, and control discipline instead of one-shot classification.

Sources:

- [FBI IC3 2023 Internet Crime Report](https://www.ic3.gov/annualreport/reports/2023_ic3report.pdf)
- [OpenEnv metadata for this benchmark](./openenv.yaml)

## What Judges Care About

LedgerShield is built to score well on real-world utility, environment design, task quality, engineering quality, and novelty because the implementation now includes:

| Dimension | What is implemented |
|---|---|
| Real-world utility | Multi-currency invoices, IBAN/SWIFT validation, SOX control modeling, AP inbox triage, campaign fraud, aging-report support |
| Environment design | Stronger PBRS reward shaping, milestone rewards, information-gain bonus, `terminated` vs `truncated`, text `render()`, formal `action_space()` and `observation_space()` |
| Task and grader quality | 21 curated benchmark cases, semantic counterfactual scoring, stricter degenerate-submission penalties, generated holdout suites, contrastive benign twins |
| Code quality | Comprehensive docstrings, shared pytest fixtures, dedicated tests for grading/currency/compliance/curriculum, GitHub Actions CI, narrower exception handling, typed internal return contracts |
| Creativity and novelty | Dec-POMDP watchdog mode, dynamic curriculum adaptation, campaign-level fraud reasoning, 16 attack types across identity/document/process/APT categories |

## Benchmark At A Glance

| Item | Value |
|---|---:|
| Public benchmark cases | 21 curated base cases |
| Task families | 5 (`task_a` through `task_e`) |
| Attack types | 16 |
| Default loader behavior | 21 benchmark cases + 24 generated challenge variants = 45 loaded cases |
| Optional generated suites | challenge variants, holdout variants, contrastive benign twins |
| Formal model | finite-horizon POMDP |
| Server runtime | FastAPI / OpenEnv-compatible |

### Task coverage

| Task | Count | Focus |
|---|---:|---|
| Task A | 4 | proof-carrying invoice extraction, multilingual and multi-currency artifacts |
| Task B | 5 | three-way match, receipt gaps, quantity/tax discrepancies |
| Task C | 4 | duplicate detection, cross-vendor fraud, approval-threshold evasion |
| Task D | 6 | AP inbox/BEC triage, workflow override, CEO fraud, benign vendor updates |
| Task E | 2 | coordinated campaigns and supply-chain-compromise APT scenarios |

## What The Agent Must Actually Do

LedgerShield episodes are partially observable. Agents start with visible documents and must use tools and interventions to discover the rest.

Investigation tools:

- `zoom`, `get_doc_crop`, `ocr`
- `lookup_vendor`, `lookup_vendor_history`, `lookup_policy`
- `lookup_po`, `lookup_receipt`, `search_ledger`
- `inspect_email_thread`, `compare_bank_account`

Interventions:

- `request_callback_verification`
- `freeze_vendor_profile`
- `request_bank_change_approval_chain`
- `request_po_reconciliation`
- `request_additional_receipt_evidence`
- `route_to_procurement`
- `route_to_security`
- `flag_duplicate_cluster_review`
- `create_human_handoff`

Final action:

- `submit_decision`

The submission is not just a label. Strong agents are expected to return structured decisions with grounded `reason_codes`, `policy_checks`, `evidence_map`, and task-specific fields like duplicates, campaign signals, discrepancies, or extracted invoice fields.

## Upgrade Snapshot

The recent benchmark upgrade work is now reflected in the codebase:

| Phase | Highlights |
|---|---|
| Phase 1: Real-world utility | `server/currency_engine.py`, `server/compliance_engine.py`, richer payment artifacts, aging-report support |
| Phase 2: Task and grader quality | 21 curated cases, semantic counterfactual grading, tighter degenerate penalties, generated holdouts |
| Phase 3: Environment design | `SHAPING_SCALE=0.35`, `INFO_GAIN_BONUS=0.08`, milestone rewards, Gymnasium-style truncation semantics, text rendering, formal spaces |
| Phase 4: Code quality | docstrings across core modules, `tests/conftest.py`, CI workflow, `TypedDict` internal returns |
| Phase 5: Creativity and novelty | Dec-POMDP watchdog mode, curriculum adaptation, 16-attack library, exploration bonus integrated into `step()` |

## Benchmarking Story

LedgerShield is not just a server. It includes a full evaluation stack:

- `benchmark_report.py` scores the public benchmark, generated holdout suites, and contrastive adversarial/benign pairs.
- `compare_models_live.py` runs live head-to-head evaluations and writes per-case debug traces.
- `live_model_comparison_debug/` stores action traces, planning traces, score breakdowns, and system state snapshots for diagnosis.
- `/leaderboard` and `/benchmark-report` expose report artifacts through the API when generated.

### Latest local live comparison

The latest local `compare_models_live.py` snapshot in this workspace was generated on **April 8, 2026** from the full 21-case public benchmark using:

```bash
python compare_models_live.py \
  --models gpt-3.5-turbo,gpt-4o,gpt-5.4 \
  --output live_model_comparison.json
```

| Model | Tier | Capability | Average Score | Success Rate | Min | Max | API Calls |
|---|---|---:|---:|---:|---:|---:|---:|
| `gpt-3.5-turbo` | `standard` | 3.2 | 0.7658 | 42.9% | 0.13 | 0.99 | 64 |
| `gpt-4o` | `strong` | 4.6 | 0.9267 | 100.0% | 0.87 | 0.99 | 63 |
| `gpt-5.4` | `elite` | 5.4 | 0.9276 | 100.0% | 0.87 | 0.99 | 34 |

Capability ordering check: `PASS`

Failed cases for the weakest model:

- `CASE-B-003`
- `CASE-C-001`
- `CASE-C-002`
- `CASE-C-003`
- `CASE-D-001`
- `CASE-D-002`
- `CASE-D-003`
- `CASE-D-004`
- `CASE-D-005`
- `CASE-D-006`
- `CASE-E-001`
- `CASE-E-002`

Published benchmark metadata in [`openenv.yaml`](./openenv.yaml) already records meaningful public-vs-holdout separation:

| Agent | Public mean | Holdout mean | Holdout consistent pass rate |
|---|---:|---:|---:|
| Deterministic baseline | 0.9674 | 0.6649 | 0.6190 |
| Published external LLM agent | not listed | 0.3847 | 0.2222 |

That gap is deliberate: the benchmark is meant to look easy on clean public cases and much harder on generated holdouts, adversarial variants, and expert Task E scenarios.

## Quick Start

### 1. Install

```bash
git clone https://github.com/BiradarScripts/Meta-s-LedgerShield.git
cd Meta-s-LedgerShield

python -m venv .venv
source .venv/bin/activate

pip install -e .
pip install -r requirements.txt
```

### 2. Start the environment server

```bash
python -m server.app
```

The API comes up on `http://127.0.0.1:8000` by default.

### 3. Run the submission-safe agent

```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-5.4"
export HF_TOKEN="your_token"
export ENV_URL="http://127.0.0.1:8000"

python inference.py
```

### 4. Generate a benchmark report

```bash
python benchmark_report.py --format markdown
```

### 5. Run live model comparisons

```bash
export OPENAI_API_KEY="your_api_key"
export API_BASE_URL="https://api.openai.com/v1"
export ENV_URL="http://127.0.0.1:8000"

python compare_models_live.py \
  --models gpt-3.5-turbo,gpt-4o,gpt-5.4 \
  --output live_model_comparison.json
```

### 6. Validate locally

```bash
python -m pytest tests/ -q
bash validate-submission.sh
```

If `openenv` is installed in your environment, you can also run:

```bash
openenv validate
```

## Documentation

| Document | What it covers |
|---|---|
| [`docs/README.md`](./docs/README.md) | docs landing page and reading paths |
| [`docs/index.md`](./docs/index.md) | benchmark overview, quick start, and core concepts |
| [`docs/tasks.md`](./docs/tasks.md) | task families, outputs, scoring, and case catalog |
| [`docs/api-reference.md`](./docs/api-reference.md) | REST endpoints, payloads, response envelopes, and action contracts |
| [`docs/architecture.md`](./docs/architecture.md) | system design, hidden state, reward flow, grading, and evaluation pipeline |
| [`docs/development.md`](./docs/development.md) | setup, tests, CI, and detailed repo/file map |
| [`docs/deployment.md`](./docs/deployment.md) | local, Docker, HF Space, and environment configuration guidance |

Recommended reading paths:

- Benchmark judge or first-time reader: [`docs/index.md`](./docs/index.md) -> [`docs/tasks.md`](./docs/tasks.md) -> [`docs/architecture.md`](./docs/architecture.md)
- Agent builder: [`docs/tasks.md`](./docs/tasks.md) -> [`docs/api-reference.md`](./docs/api-reference.md) -> [`docs/development.md`](./docs/development.md)
- Contributor: [`docs/development.md`](./docs/development.md) -> [`docs/architecture.md`](./docs/architecture.md)
- Operator: [`docs/deployment.md`](./docs/deployment.md) -> [`docs/api-reference.md`](./docs/api-reference.md)

## Repository Structure

### Top level

```text
Meta_final/
├── README.md
├── docs/
├── server/
├── tests/
├── inference.py
├── inference_llm_powered.py
├── benchmark_report.py
├── compare_models_live.py
├── compare_all_models.py
├── openenv.yaml
├── Dockerfile
└── validate-submission.sh
```

### Important files at a glance

| Path | Purpose |
|---|---|
| `server/environment.py` | main OpenEnv environment loop, reward shaping, truncation semantics, rendering |
| `server/world_state.py` | hidden/public state, artifact scheduling, campaign context, pressure resistance |
| `server/grading.py` | task rubrics, semantic counterfactual scoring, degenerate penalties |
| `server/trajectory_grading.py` | investigation, intervention, calibration, efficiency, and outcome scoring |
| `server/attack_library.py` | 16 adversarial attack templates |
| `server/case_factory.py` | challenge, holdout, and benign-twin generation |
| `server/currency_engine.py` | FX conversion, IBAN/SWIFT checks, currency mismatch detection, aging reports |
| `server/compliance_engine.py` | SOX-style AP control evaluation |
| `server/curriculum.py` | dynamic difficulty adaptation |
| `server/dual_agent_mode.py` | Dec-POMDP watchdog/auditor mode |
| `benchmark_report.py` | public benchmark + holdout + contrastive reporting |
| `compare_models_live.py` | live multi-model evaluation with debug artifacts |
| `inference.py` | submission-safe agent entrypoint with strict stdout contract |
| `task_c_guardrails.py` / `task_d_guardrails.py` | grounded output sanitizers for high-risk tasks |
| `.github/workflows/ci.yml` | pytest, Docker build, and metadata validation in CI |

For the full file-by-file map, see [`docs/development.md`](./docs/development.md).

## Current Engineering Status

- Core environment upgrades from Phases 1 through 5 are implemented in code.
- The repo includes 21 curated benchmark cases and generated challenge/holdout tooling.
- CI is present via GitHub Actions.
- The test suite includes API smoke, grading, environment, inference, compliance, currency, curriculum, and guardrail coverage.
- The environment remains submission-compatible through `inference.py`.

## Safety Note

LedgerShield is a benchmark and simulation environment. It models payment-integrity risk and enterprise controls, but it is not a production fraud platform and should not be used to approve or block real payments without independent controls, audit, and governance.
