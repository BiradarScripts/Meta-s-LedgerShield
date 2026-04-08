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

## Documentation Hub

The root README is the fastest way to orient yourself, but the full docs set lives in [`docs/`](./docs/) and is now linked explicitly here.

| Document | Audience | What it covers |
|----------|----------|----------------|
| [`docs/README.md`](./docs/README.md) | everyone | docs landing page, reading paths, and navigation |
| [`docs/index.md`](./docs/index.md) | first-time readers | benchmark overview, concepts, and quick start |
| [`docs/tasks.md`](./docs/tasks.md) | benchmark users | task families, expected outputs, scoring, and strategies |
| [`docs/api-reference.md`](./docs/api-reference.md) | integrators | REST endpoints, request/response shapes, and API usage |
| [`docs/architecture.md`](./docs/architecture.md) | developers and researchers | system design, data flow, state model, and component responsibilities |
| [`docs/development.md`](./docs/development.md) | contributors | setup, tests, repo structure, and extension workflow |
| [`docs/deployment.md`](./docs/deployment.md) | operators | local, Docker, and production deployment guidance |

Recommended reading paths:

- New participant: [`docs/index.md`](./docs/index.md) -> [`docs/tasks.md`](./docs/tasks.md) -> [`docs/api-reference.md`](./docs/api-reference.md)
- Researcher studying model behavior: [`docs/index.md`](./docs/index.md) -> [`docs/architecture.md`](./docs/architecture.md) -> [`docs/tasks.md`](./docs/tasks.md)
- Contributor extending the benchmark: [`docs/development.md`](./docs/development.md) -> [`docs/architecture.md`](./docs/architecture.md) -> [`docs/api-reference.md`](./docs/api-reference.md)
- Operator deploying the environment: [`docs/deployment.md`](./docs/deployment.md) -> [`docs/api-reference.md`](./docs/api-reference.md)

## Why LedgerShield Exists

Real AP fraud is not a single-turn OCR or classification problem. Strong agents need to:

- inspect invoices, emails, vendor history, ledger state, purchase orders, and receipts
- decide which tools to use next under a limited step budget
- request out-of-band controls such as callback verification and approval-chain evidence
- ground fraud claims in specific evidence spans instead of vague explanations
- avoid both unsafe payment release and unnecessary operational escalation

LedgerShield is built to measure that full loop rather than a narrow one-shot decision.

## What Makes This Benchmark Different

- Stateful environment: each case has hidden risk signals, pending events, and artifact unlocks.
- Proof-carrying outputs: decisions are scored together with `reason_codes`, `policy_checks`, `evidence_map`, and intervention quality.
- Trajectory-aware grading: the benchmark scores investigation coverage, intervention quality, calibration, efficiency, callback interpretation, and downstream outcome.
- Adversarial pressure: spoofed follow-ups, callback discouragement, approval-threshold evasion, and coordinated invoice campaigns are modeled explicitly.
- Multi-hop reasoning: strong performance requires joining evidence across documents, tools, and delayed artifacts.
- Model separation by design: better models win by planning better investigations and producing better grounded submissions, not by luck on a single label.

## Benchmark In One Minute

Each episode begins with partial observability:

- some documents are visible immediately
- some artifacts are hidden and must be unlocked through interventions
- the environment enforces a budget and maximum step count
- the grader measures both what the agent concluded and how it got there

The agent loop is:

1. reset the environment onto a specific case
2. inspect visible artifacts and choose tools
3. reveal risk signals and hidden artifacts
4. request interventions when the situation warrants them
5. submit a structured final decision with grounded evidence

That design lets LedgerShield measure operational competence, not just document reading.

## Current Benchmark Status

The repo has two aligned agent entrypoints:

- [`inference.py`](./inference.py): the submission-safe agent you should ship
- [`inference_llm_powered.py`](./inference_llm_powered.py): the instrumented comparison and debug harness used by the live comparison scripts

They now share the same high-level behavior:

- model-driven investigation planning
- model-driven intervention planning
- grounded sanitization of outputs without per-case gold-answer injection
- stronger separation on hard fraud and campaign cases

Current live comparison snapshot from [`live_model_comparison.json`](./live_model_comparison.json):

| Model | Average Score | Pass@1 (`0.85`) | Min Score | Failed Cases |
|------|---------------:|----------------:|----------:|--------------|
| `gpt-3.5-turbo` | `0.8051` | `58.3%` | `0.4402` | `CASE-B-003`, `CASE-D-001`, `CASE-D-003`, `CASE-D-004`, `CASE-E-001` |
| `gpt-4o` | `0.9145` | `75.0%` | `0.8016` | `CASE-D-003`, `CASE-D-004`, `CASE-E-001` |
| `gpt-5.4` | `0.9482` | `100.0%` | `0.8644` | none |

Why that separation appears now:

- weaker models under-investigate hard cases
- mid-tier models often choose the right direction but leave evidence or intervention points on the table
- stronger models more reliably reveal the right artifacts and submit benchmark-native grounded outputs

## Task Suite

LedgerShield ships with 5 task families across 12 curated benchmark cases.

| Task | Focus | Cases | What the agent must prove |
|------|-------|-------|---------------------------|
| `Task A` | Proof-carrying extraction | 2 | fields, line items, and token-grounded evidence |
| `Task B` | Three-way match decisioning | 3 | safe PAY/HOLD choices with PO and receipt support |
| `Task C` | Duplicate and fraud triage | 2 | duplicate detection, bank validation, and escalation logic |
| `Task D` | AP inbox incident triage | 4 | email analysis, spoof detection, callback reasoning, and incident containment |
| `Task E` | Coordinated campaign fraud | 1 | cross-invoice reasoning, campaign signals, and linked intervention strategy |

For detailed task-by-task guidance, scoring shapes, and example outputs, read [`docs/tasks.md`](./docs/tasks.md).

## Architecture

LedgerShield is organized around four interacting layers.

### 1. Environment and state transition

- [`server/environment.py`](./server/environment.py) runs the OpenEnv-compatible episode loop.
- [`server/transition_engine.py`](./server/transition_engine.py) handles interventions, delayed artifacts, and state mutation.
- [`server/world_state.py`](./server/world_state.py) defines hidden risk, required actions, required artifacts, and campaign structure.

### 2. Tools and observations

The tool layer exposes:

- OCR and zoom-based document inspection
- vendor and policy lookups
- purchase-order and receipt retrieval
- ledger search for duplicate and near-duplicate activity
- bank-account comparison
- email-thread inspection and follow-up controls

### 3. Grading

- [`server/grading.py`](./server/grading.py) scores task-specific outputs.
- [`server/trajectory_grading.py`](./server/trajectory_grading.py) scores how the agent investigated, intervened, calibrated confidence, and resolved risk.
- [`server/outcome_simulator.py`](./server/outcome_simulator.py) models downstream enterprise impact.

### 4. Agents

- [`inference.py`](./inference.py) is the final submission file and preserves the hackathon submission contract.
- [`inference_llm_powered.py`](./inference_llm_powered.py) is the richer comparison/debug agent that saves planning traces and score breakdowns.

For a fuller systems walkthrough, read [`docs/architecture.md`](./docs/architecture.md).

## Repository Map

The root contains both benchmark infrastructure and agent implementations. The most important files and directories are:

```text
Meta-s-LedgerShield/
├── server/                       # environment, tools, grading, fixtures, and state logic
├── docs/                         # long-form documentation
├── tests/                        # unit, contract, and regression tests
├── inference.py                  # final submission agent
├── inference_llm_powered.py      # comparison/debug agent
├── compare_models_live.py        # targeted live comparison runner
├── compare_all_models.py         # broader multi-model sweep
├── benchmark_report.py           # summary report generator
├── task_c_guardrails.py          # Task C grounded output sanitization
├── task_d_guardrails.py          # Task D grounded output sanitization
├── ledgershield_env.py           # thin environment client wrapper
├── models.py                     # shared dataclasses and payload types
├── validate-submission.sh        # local submission validation helper
├── pyproject.toml                # package configuration
├── requirements.txt              # dependencies
├── Dockerfile                    # container build
└── openenv.yaml                  # OpenEnv metadata
```

## Quick Start

### Prerequisites

- Python 3.11+
- an OpenAI-compatible API endpoint for live model evaluation
- Docker if you want to run the environment in a container

### Install

```bash
git clone https://github.com/BiradarScripts/Meta-s-LedgerShield.git
cd Meta-s-LedgerShield

python -m venv .venv
source .venv/bin/activate

pip install -e .
pip install -r requirements.txt
```

### Start the environment server

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

### Run a live head-to-head comparison

```bash
export OPENAI_API_KEY="your_api_key"
export API_BASE_URL="https://api.openai.com/v1"
export ENV_URL="http://127.0.0.1:8000"

python compare_models_live.py \
  --models gpt-3.5-turbo,gpt-4o,gpt-5.4 \
  --output live_model_comparison.json
```

## Submission Contract

The final hackathon submission file is [`inference.py`](./inference.py). It is intentionally kept compatible with the expected evaluator contract.

Required environment variables present in the file:

- `API_BASE_URL`
- `MODEL_NAME`
- `HF_TOKEN`

Optional environment variable:

- `LOCAL_IMAGE_NAME`

Important contract details:

- defaults are set only for `API_BASE_URL` and `MODEL_NAME`
- all LLM calls use `from openai import OpenAI`
- stdout emits only these structured line types:

```text
[START] task=<task_name> env=<benchmark> model=<model_name>
[STEP] step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
[END] success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
```

Formatting guarantees:

- one `START` line at episode begin
- one `STEP` line immediately after each environment step
- one `END` line even on exception paths
- `done` and `success` are lowercase booleans
- `error` is raw text or `null`
- rewards are formatted to two decimals
- the final `[END] score=` is forced into the strict open interval `(0,1)` for evaluator compliance
- signed zero is normalized away, so `-0.00` is not emitted

If you are validating a submission workflow, also see [`validate-submission.sh`](./validate-submission.sh).

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

## Evaluation Workflows

### Deterministic local replay

Use this to validate the environment and local baseline behavior without external API calls.

```bash
python -m pytest -q
```

Focused local replay:

```bash
python - <<'PY'
from server.data_loader import load_all
import inference
print(inference.run_local_baseline(["CASE-D-001", "CASE-D-003", "CASE-D-004", "CASE-E-001"], db=load_all(), emit_logs=False))
PY
```

### Live comparison with traces

The comparison harness uses [`inference_llm_powered.py`](./inference_llm_powered.py) because it records extra debug artifacts such as model planning traces and score breakdowns.

```bash
python compare_models_live.py \
  --models gpt-3.5-turbo,gpt-4o,gpt-5.4 \
  --output live_model_comparison.json
```

Outputs:

- [`live_model_comparison.json`](./live_model_comparison.json): aggregate metrics
- `live_model_comparison_debug/<model>/<case>.json`: planning trace, action trace, final submission, system state, and score breakdown

### Broad model sweep

```bash
python compare_all_models.py
```

### Benchmark report generation

```bash
python benchmark_report.py --format markdown
```

## Debugging Failed Cases

When a model underperforms, inspect the per-case debug traces first.

Useful fields in each trace file:

- `planning_trace`: what the model intended to do
- `action_trace`: what was actually executed
- `final_submission`: the structured output sent to the grader
- `score_breakdown`: exactly where points were lost
- `system_state`: artifacts, revealed signals, and other environment context

Typical failure diagnosis workflow:

1. compare `failed_cases` in [`live_model_comparison.json`](./live_model_comparison.json)
2. open the matching file in `live_model_comparison_debug/<model>/<case>.json`
3. check whether the model skipped required actions, missed artifacts, or submitted weak evidence
4. compare against a stronger model on the same case to see where trajectories diverged

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

### 2. Weak proof-carrying evidence

Some lower-tier outputs identify the right fraud direction but fail to provide usable grounded evidence.

Typical problems:

- missing `evidence_map` entirely
- incomplete `evidence_map` for chosen `reason_codes`
- document-level references without page, bounding box, and token-span grounding
- descriptive natural-language evidence instead of benchmark-native evidence objects

### 3. Missing campaign reasoning

On Task E, weaker models often catch that something is wrong but still fail the coordinated-campaign part.

They miss:

- `campaign_signals`
- cross-invoice evidence grounding
- linked bank-account reasoning
- coordinated timing reasoning
- the intervention set needed to fully secure the case

## Why Stronger Models Win

`gpt-5.4` passes the current suite because it does three things more consistently:

- it chooses a fuller investigation set before submitting
- it unlocks the right artifacts before the episode ends
- it emits better benchmark-native grounded evidence for the reasons it claims

In the strongest current traces, the high-performing model reliably:

- requests callback verification
- requests bank-change approval-chain evidence when relevant
- requests duplicate-cluster review when threshold evasion or duplicate risk is present
- routes to security and freezes vendor state when needed
- returns token-grounded `evidence_map` entries for the final `reason_codes`

## Testing And Validation

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

OpenEnv and submission checks:

```bash
openenv validate
bash validate-submission.sh
```

## Extending LedgerShield

If you want to extend the benchmark:

- read [`docs/development.md`](./docs/development.md) for the contributor workflow
- read [`docs/architecture.md`](./docs/architecture.md) before changing hidden-state or grading logic
- read [`docs/tasks.md`](./docs/tasks.md) before adding a new task family or altering output contracts
- update or add tests in [`tests/`](./tests/) whenever tools, grading, or agent output schemas change

Common extension points:

- new tools in [`server/tools.py`](./server/tools.py)
- new hidden-world mechanics in [`server/world_state.py`](./server/world_state.py)
- new grading dimensions in [`server/grading.py`](./server/grading.py)
- new agent policies in [`inference.py`](./inference.py) or [`inference_llm_powered.py`](./inference_llm_powered.py)

## Documentation Index

If you are browsing the repo from GitHub, these are the best entrypoints:

- Start here: [`README.md`](./README.md)
- Docs landing page: [`docs/README.md`](./docs/README.md)
- Overview and quick start: [`docs/index.md`](./docs/index.md)
- Architecture deep dive: [`docs/architecture.md`](./docs/architecture.md)
- API reference: [`docs/api-reference.md`](./docs/api-reference.md)
- Task reference: [`docs/tasks.md`](./docs/tasks.md)
- Development guide: [`docs/development.md`](./docs/development.md)
- Deployment guide: [`docs/deployment.md`](./docs/deployment.md)

## Status

Current verified status on this workspace snapshot:

- submission contract preserved in [`inference.py`](./inference.py)
- benchmark separation restored across weak, mid, and strong models
- live comparison artifacts are saved for case-by-case diagnosis
- hard fraud cases locally replay above the public pass threshold
- test suite passing on the current code snapshot

## Safety Note

LedgerShield is a benchmark and simulation environment. It does not process real payments and should not be used as a production fraud-control system without independent validation, controls, and governance.
