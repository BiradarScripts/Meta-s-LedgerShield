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

LedgerShield is a stateful, adversarial payment-integrity benchmark for AI agents operating in enterprise accounts payable. Agents do not just classify a document. They must investigate, unlock evidence, choose interventions, and submit proof-carrying decisions under budget and time pressure.

## Why LedgerShield Exists

Real AP fraud is not a single-turn OCR or classification problem. Strong agents need to:

- inspect invoices, emails, vendor history, ledger state, POs, and receipts
- decide which tools to use next under a limited step budget
- request out-of-band controls such as callback verification
- ground fraud claims in specific evidence spans
- avoid both unsafe payment release and unnecessary operational escalation

LedgerShield is built to measure that full loop.

## What Makes This Benchmark Different

- Stateful environment: each case has hidden risk signals, pending events, and artifact unlocks.
- Proof-carrying outputs: decisions are scored together with `reason_codes`, `policy_checks`, `evidence_map`, and intervention quality.
- Trajectory-aware grading: the benchmark scores investigation coverage, intervention quality, calibration, efficiency, callback interpretation, and downstream outcome.
- Adversarial pressure: spoofed follow-ups, callback discouragement, threshold evasion, and coordinated invoice campaigns are modeled explicitly.
- Model separation by design: stronger models win by planning better investigations and producing better grounded submissions, not by luck on a single label.

## Current Benchmark Status

The repo now has two aligned agent entrypoints:

- [`inference.py`](./inference.py): the submission-safe agent you should ship.
- [`inference_llm_powered.py`](./inference_llm_powered.py): the instrumented comparison/debug harness used by the live model-comparison scripts.

They now share the same core behavior:

- model-driven investigation planning
- model-driven intervention planning
- grounded sanitization of outputs without hardcoding gold answers
- stronger separation on Task D and Task E

Example live comparison from the current code snapshot:

| Model | Average Score | Pass@1 (`0.85`) | Failed Cases |
|------|---------------:|----------------:|--------------|
| `gpt-3.5-turbo` | `0.8051` | `58.3%` | `CASE-B-003`, `CASE-D-001`, `CASE-D-003`, `CASE-D-004`, `CASE-E-001` |
| `gpt-4o` | `0.9145` | `75.0%` | `CASE-D-003`, `CASE-D-004`, `CASE-E-001` |
| `gpt-5.4` | `0.9482` | `100.0%` | none |

That separation is visible because weaker models now miss investigation steps, artifact collection, campaign signals, and grounded evidence more often than stronger models.

## Task Suite

LedgerShield ships with 5 task families across 12 benchmark cases.

| Task | Focus | Cases | Typical Failure Mode |
|------|-------|-------|----------------------|
| `Task A` | Proof-carrying extraction | 2 | bad field extraction or weak evidence grounding |
| `Task B` | Three-way match decisioning | 3 | missed PO / receipt retrieval, wrong HOLD vs PAY |
| `Task C` | Duplicate and fraud triage | 2 | missing duplicate or bank-override signals |
| `Task D` | AP inbox incident triage | 4 | incomplete investigation, weak evidence map, missing callback / approval-chain artifacts |
| `Task E` | Coordinated campaign fraud | 1 | missing campaign signals, poor cross-invoice reasoning, weak evidence grounding |

## Architecture

LedgerShield is organized around four layers:

1. Environment and state transition

- [`server/environment.py`](./server/environment.py) runs the OpenEnv-compatible episode loop.
- [`server/transition_engine.py`](./server/transition_engine.py) handles interventions and artifact scheduling.
- [`server/world_state.py`](./server/world_state.py) defines hidden risk, required actions, and required artifacts.

2. Tools and observations

- OCR, email inspection, vendor-history lookup, bank comparison, ledger search, PO lookup, and receipt lookup are exposed through the environment tool layer.

3. Grading

- [`server/grading.py`](./server/grading.py) scores each submission.
- [`server/trajectory_grading.py`](./server/trajectory_grading.py) scores investigation coverage, intervention quality, calibration, efficiency, callback interpretation, and resolution state.

4. Agents

- [`inference.py`](./inference.py) is the final submission file.
- [`inference_llm_powered.py`](./inference_llm_powered.py) is the comparison/debug agent with rich per-case traces.

## Quick Start

### Prerequisites

- Python 3.11+
- Docker optional
- an OpenAI-compatible API endpoint for live model evaluation

### Install

```bash
git clone https://github.com/BiradarScripts/Meta-s-LedgerShield.git
cd Meta-s-LedgerShield

python -m venv .venv
source .venv/bin/activate

pip install -e .
pip install -r requirements.txt
```

### Start the environment

```bash
python -m server.app
```

### Run the submission agent

```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-5.4"
export HF_TOKEN="your_api_token"
export ENV_URL="http://127.0.0.1:8000"

python inference.py
```

## Submission Contract

The final hackathon submission file is [`inference.py`](./inference.py). It follows the expected contract:

- required env vars in the file: `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN`
- optional env var: `LOCAL_IMAGE_NAME`
- defaults are set only for `API_BASE_URL` and `MODEL_NAME`
- all LLM calls use `from openai import OpenAI`
- stdout emits only these structured line types:

```text
[START] task=<task_name> env=<benchmark> model=<model_name>
[STEP] step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
[END] success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
```

Important detail:

- the `[END] score=` field is formatted as a strict open-interval value `(0,1)`, not `0.00` and not `1.00`
- signed zero is normalized away in stdout formatting, so `-0.00` is never emitted
- rewards remain 2-decimal values exactly as required by the benchmark parser

## Evaluation Workflows

### Deterministic local replay

Use this to test the end-to-end environment without needing external API calls.

```bash
python -m pytest -q
```

Or run a focused local replay:

```bash
python - <<'PY'
from server.data_loader import load_all
import inference
print(inference.run_local_baseline(["CASE-D-001", "CASE-D-003", "CASE-D-004", "CASE-E-001"], db=load_all(), emit_logs=False))
PY
```

### Live head-to-head comparison

The live comparison harness uses [`inference_llm_powered.py`](./inference_llm_powered.py) because it also saves detailed case traces for debugging.

```bash
export OPENAI_API_KEY="your_api_key"
export API_BASE_URL="https://api.openai.com/v1"
export ENV_URL="http://127.0.0.1:8000"

python compare_models_live.py \
  --models gpt-3.5-turbo,gpt-4o,gpt-5.4 \
  --output live_model_comparison.json
```

Outputs:

- [`live_model_comparison.json`](./live_model_comparison.json): aggregate metrics
- `live_model_comparison_debug/<model>/<case>.json`: planning trace, action trace, final submission, and score breakdown

### Broad model sweep

```bash
python compare_all_models.py
```

### Benchmark report generation

```bash
python benchmark_report.py --format markdown
```

## Why Weaker Models Fail

The current traces show three recurring weak-model failure modes.

### 1. Under-investigation on hard fraud cases

Weaker models often stop after a partial read of the email thread and never execute the full fraud investigation plan.

Common misses:

- skipping `compare_bank_account`
- skipping one or more `search_ledger` actions
- skipping `lookup_vendor_history`
- skipping `request_callback_verification`
- skipping `request_bank_change_approval_chain`

Example from current traces:

- `gpt-3.5-turbo` on `CASE-D-001`, `CASE-D-003`, and `CASE-D-004` selected only a tiny fraction of the available investigation graph
- this collapses `investigation_score`, `callback_interpretation_score`, and `resolution_state_score`

### 2. Weak proof-carrying evidence

Some lower-tier outputs identify the right fraud direction but fail to provide usable grounded evidence.

Typical problems:

- missing `evidence_map` entirely
- incomplete `evidence_map` for chosen `reason_codes`
- doc-level references without page / bbox / token span grounding
- descriptive natural-language evidence objects instead of benchmark-native token references

This is why a model can have:

- `decision_score = 1.0`
- `reason_score` reasonably high
- but still fail because `evidence_score` stays low

### 3. Missing campaign reasoning

On Task E, weak models often catch “something is wrong” but still fail the coordinated-campaign part.

They miss:

- `campaign_signals`
- cross-invoice evidence grounding
- linked bank-account reasoning
- coordinated timing reasoning
- the intervention set needed to fully secure the case

That is exactly what happened in the current `gpt-3.5-turbo` Task E trace: correct top-level escalation, but no campaign signals, weak policy alignment, and poor evidence score.

## Why Stronger Models Win

`gpt-5.4` passes because it does three things more consistently:

- it chooses a fuller investigation set before submitting
- it unlocks the right artifacts before the episode ends
- it emits better benchmark-native grounded evidence for the reasons it claims

In the current passing traces, `gpt-5.4` reliably:

- requests callback verification
- requests bank-change approval-chain evidence when relevant
- requests duplicate-cluster review when threshold evasion or duplicate risk is present
- routes to security and freezes vendor state when needed
- returns token-grounded `evidence_map` entries for the final `reason_codes`

## Repository Layout

```text
Meta-s-LedgerShield/
├── server/                       # environment, tools, grading, world state
├── docs/                         # extended documentation
├── tests/                        # unit and contract tests
├── inference.py                  # final submission agent
├── inference_llm_powered.py      # instrumented live-comparison agent
├── compare_models_live.py        # targeted live model comparison
├── compare_all_models.py         # broad model sweep
├── benchmark_report.py           # benchmark reporting
├── task_c_guardrails.py          # task C grounding / sanitization
├── task_d_guardrails.py          # task D grounding / sanitization
├── ledgershield_env.py           # client wrapper for the environment
├── pyproject.toml
└── Dockerfile
```

## Environment Variables

### Submission agent

| Variable | Purpose | Default |
|----------|---------|---------|
| `API_BASE_URL` | OpenAI-compatible API endpoint used by `inference.py` | `https://api.openai.com/v1` |
| `MODEL_NAME` | model used by `inference.py` | `gpt-5.4` |
| `HF_TOKEN` | API token used by `inference.py` | none |
| `LOCAL_IMAGE_NAME` | optional local Docker image name | none |
| `ENV_URL` | environment server URL | `http://localhost:8000` |

### Comparison scripts

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | credential used by live comparison scripts |
| `API_BASE_URL` | API base URL for live model comparisons |
| `ENV_URL` | environment server URL |

## Testing

Run the full suite:

```bash
python -m pytest -q
```

Focused contract and guardrail validation:

```bash
python -m pytest \
  tests/test_inference_contract.py \
  tests/test_task_c_guardrails.py \
  tests/test_task_d_guardrails.py \
  tests/test_compare_models_live.py \
  tests/test_compare_all_models.py -q
```

## Documentation

Additional docs live in [`docs/`](./docs):

- [`docs/index.md`](./docs/index.md)
- [`docs/architecture.md`](./docs/architecture.md)
- [`docs/api-reference.md`](./docs/api-reference.md)
- [`docs/tasks.md`](./docs/tasks.md)
- [`docs/development.md`](./docs/development.md)
- [`docs/deployment.md`](./docs/deployment.md)

## Status

Current verified status on this workspace snapshot:

- submission contract preserved in [`inference.py`](./inference.py)
- benchmark separation restored across weak, mid, and strong models
- hard fraud cases locally replay above the public pass threshold
- full test suite passing

## Acknowledgments

Built for the Meta OpenEnv hackathon setting and designed as a realistic AP fraud-evaluation environment for agentic systems research.

## Safety Note

LedgerShield is a benchmark and simulation environment. It does not process real payments and should not be used as a production fraud-control system without independent validation, controls, and governance.
