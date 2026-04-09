# Development Guide

This guide is for contributors working inside the LedgerShield repo. It covers setup, validation, CI expectations, and a detailed file map so it is easy to find the right place to make changes.

## Local Setup

### Prerequisites

- Python 3.11 or 3.12
- `git`
- Docker if you want container smoke tests
- an OpenAI-compatible endpoint only if you plan to run the LLM-powered comparison scripts

### Install

```bash
git clone https://github.com/BiradarScripts/Meta-s-LedgerShield.git
cd Meta-s-LedgerShield

python -m venv .venv
source .venv/bin/activate

pip install -e .
pip install -r requirements.txt
```

### Start the server

```bash
python -m server.app
```

### Run the test suite

```bash
python -m pytest tests/ -q
```

Useful focused runs:

```bash
python -m pytest tests/test_ledgershield_env.py -q
python -m pytest tests/test_grading.py tests/test_task_c_guardrails.py tests/test_task_d_guardrails.py -q
python -m pytest tests/test_currency_engine.py tests/test_compliance_engine.py tests/test_curriculum.py -q
```

### Validate packaging and submission workflow

```bash
bash validate-submission.sh
docker build -t ledgershield:dev .
```

If `openenv` is installed:

```bash
openenv validate
```

## CI Expectations

The repo includes [`../.github/workflows/ci.yml`](../.github/workflows/ci.yml), which currently runs:

- pytest on Python 3.11 and 3.12
- Docker build + container smoke test
- `openenv.yaml` metadata validation

Pytest configuration is centralized in [`../pyproject.toml`](../pyproject.toml) under `[tool.pytest.ini_options]`:

- `asyncio_mode = "strict"` with `asyncio_default_fixture_loop_scope = "function"`
- custom `tests` marker
- deprecation-warning filters for `websockets.legacy`

If you change APIs, packaging, or runtime behavior, assume CI should keep passing without special local context.

## Repo Map

### Root files

| Path | What it is for |
|---|---|
| [`../README.md`](../README.md) | top-level benchmark overview and quick start |
| [`../Dockerfile`](../Dockerfile) | container image definition for server deployment |
| [`../pyproject.toml`](../pyproject.toml) | package metadata, dependencies, pytest config |
| [`../requirements.txt`](../requirements.txt) | pinned runtime dependencies |
| [`../uv.lock`](../uv.lock) | lockfile for reproducible dependency installs |
| [`../openenv.yaml`](../openenv.yaml) | OpenEnv metadata, novelty claims, published benchmark numbers |
| [`../__init__.py`](../__init__.py) | package marker |
| [`../client.py`](../client.py) | thin HTTP client wrapper for the environment |
| [`../ledgershield_env.py`](../ledgershield_env.py) | compatibility re-export module for legacy imports |
| [`../models.py`](../models.py) | shared dataclasses, Pydantic reward model, typed internal returns |
| [`../openenv_compat.py`](../openenv_compat.py) | adapter around `openenv-core` with local fallback server/client |
| [`../inference.py`](../inference.py) | submission-safe agent with `ModelCapabilityProfile` tiers, evidence grounding, and strict stdout contract |
| [`../inference_improved.py`](../inference_improved.py) | experimental improved agent entrypoint |
| [`../inference_llm_powered.py`](../inference_llm_powered.py) | richer LLM-powered agent used for debugging and comparisons |
| [`../llm_utils.py`](../llm_utils.py) | JSON parsing and completion helpers for LLM workflows |
| [`../llm_judge_grader.py`](../llm_judge_grader.py) | optional LLM-as-judge grading experiments |
| [`../compare_models_live.py`](../compare_models_live.py) | live multi-model comparison with capability profiles and monotonic strength checks |
| [`../sync_benchmark_metadata.py`](../sync_benchmark_metadata.py) | refreshes README/docs/openenv metadata from current artifacts and runtime defaults |
| [`../compare_all_models.py`](../compare_all_models.py) | broader multi-model sweep helper with `--models`, `--output`, `--timeout`, and a `0.85`-aligned pass threshold |
| [`../benchmark_report.py`](../benchmark_report.py) | public benchmark, holdout, and contrastive report generation |
| [`../generate_branch_comparison_report.py`](../generate_branch_comparison_report.py) | legacy reporting helper for saved branch comparison JSONs |
| [`../generate_comparison_report.py`](../generate_comparison_report.py) | legacy reporting helper for multi-model JSON summaries |
| [`../generate_final_report.py`](../generate_final_report.py) | legacy reporting helper for final comparison JSONs |
| [`../generate_sota_report.py`](../generate_sota_report.py) | legacy reporting helper for SOTA comparison JSONs |
| [`../task_c_guardrails.py`](../task_c_guardrails.py) | Task C sanitization, composite signal detection, and constructive PAY evidence |
| [`../task_d_guardrails.py`](../task_d_guardrails.py) | Task D sanitization, composite signal detection, and constructive PAY evidence |
| [`../test_scoring.py`](../test_scoring.py) | local baseline scoring simulation helper |
| [`../validate_grader.py`](../validate_grader.py) | end-to-end grader and environment validation script |
| [`../validate_agent_grading.py`](../validate_agent_grading.py) | score-separation validation helper |
| [`../validate-submission.sh`](../validate-submission.sh) | pre-submission validator for Docker, server health, and stdout contract |
| [`../live_model_comparison.json`](../live_model_comparison.json) | saved live comparison summary artifact |

### `server/`

| Path | What it is for |
|---|---|
| [`../server/__init__.py`](../server/__init__.py) | package marker |
| [`../server/app.py`](../server/app.py) | FastAPI app builder and endpoint registration |
| [`../server/environment.py`](../server/environment.py) | main environment loop, reward shaping, truncation logic, rendering |
| [`../server/world_state.py`](../server/world_state.py) | hidden/public state, artifacts, readiness, pressure resistance |
| [`../server/tools.py`](../server/tools.py) | investigation tool implementations, email-thread payload construction, domain alignment inference |
| [`../server/transition_engine.py`](../server/transition_engine.py) | intervention handling and signal extraction |
| [`../server/grading.py`](../server/grading.py) | task-specific grading rubrics |
| [`../server/trajectory_grading.py`](../server/trajectory_grading.py) | trajectory-aware scoring components |
| [`../server/outcome_simulator.py`](../server/outcome_simulator.py) | downstream operational/fraud outcome simulation |
| [`../server/risk_rules.py`](../server/risk_rules.py) | risk bucket logic and heuristic submission-risk assessment |
| [`../server/pressure_events.py`](../server/pressure_events.py) | adversarial pressure-event templates and scoring |
| [`../server/vendor_simulator.py`](../server/vendor_simulator.py) | callback vendor-response simulation |
| [`../server/data_loader.py`](../server/data_loader.py) | fixture loading, indexing, and generated-case injection |
| [`../server/case_factory.py`](../server/case_factory.py) | challenge/holdout/benign-twin generation |
| [`../server/attack_library.py`](../server/attack_library.py) | 16 adversarial AP fraud attack templates |
| [`../server/schema.py`](../server/schema.py) | canonical field/action/reason-code constants and normalizers |
| [`../server/currency_engine.py`](../server/currency_engine.py) | multi-currency realism utilities |
| [`../server/compliance_engine.py`](../server/compliance_engine.py) | SOX-style internal-control evaluation |
| [`../server/curriculum.py`](../server/curriculum.py) | dynamic difficulty adaptation |
| [`../server/dual_agent_mode.py`](../server/dual_agent_mode.py) | watchdog-mode dual-agent novelty module |

### `server/fixtures/`

| Path | What it stores |
|---|---|
| [`../server/fixtures/cases.json`](../server/fixtures/cases.json) | the 21 curated benchmark cases |
| [`../server/fixtures/vendors.json`](../server/fixtures/vendors.json) | vendor master data |
| [`../server/fixtures/vendor_history.json`](../server/fixtures/vendor_history.json) | historical vendor changes and fraud history |
| [`../server/fixtures/po_records.json`](../server/fixtures/po_records.json) | purchase-order records |
| [`../server/fixtures/receipts.json`](../server/fixtures/receipts.json) | goods-receipt records |
| [`../server/fixtures/ledger_index.json`](../server/fixtures/ledger_index.json) | ledger/payment history used for duplicate detection |
| [`../server/fixtures/email_threads.json`](../server/fixtures/email_threads.json) | structured email-thread records |
| [`../server/fixtures/policy_rules.json`](../server/fixtures/policy_rules.json) | policy rules used by `lookup_policy` |

### `tests/`

| Path | What it validates |
|---|---|
| [`../tests/conftest.py`](../tests/conftest.py) | shared fixtures and suite-wide pytest marker setup |
| [`../tests/test_api_smoke.py`](../tests/test_api_smoke.py) | API endpoint smoke coverage |
| [`../tests/test_benchmark_report.py`](../tests/test_benchmark_report.py) | public/holdout/contrastive reporting behavior |
| [`../tests/test_compare_all_models.py`](../tests/test_compare_all_models.py) | score parsing helpers in broad model sweeps |
| [`../tests/test_compare_models_live.py`](../tests/test_compare_models_live.py) | live comparison stats, capability profiles, and rendering helpers |
| [`../tests/test_compliance_engine.py`](../tests/test_compliance_engine.py) | SOX compliance evaluation |
| [`../tests/test_currency_engine.py`](../tests/test_currency_engine.py) | FX/IBAN/SWIFT/aging-report utilities |
| [`../tests/test_curriculum.py`](../tests/test_curriculum.py) | curriculum tiering and case selection |
| [`../tests/test_grading.py`](../tests/test_grading.py) | degenerate evidence cap and grading edge cases |
| [`../tests/test_inference_contract.py`](../tests/test_inference_contract.py) | required stdout contract for `inference.py` |
| [`../tests/test_inference_llm_powered.py`](../tests/test_inference_llm_powered.py) | derived thread reasoning in LLM-powered inference |
| [`../tests/test_inference_runtime.py`](../tests/test_inference_runtime.py) | model capability profiles and runtime heuristics |
| [`../tests/test_ledgershield_env.py`](../tests/test_ledgershield_env.py) | environment transitions, scoring, and holdout generation |
| [`../tests/test_schema_reason_codes.py`](../tests/test_schema_reason_codes.py) | reason-code normalization and aliasing |
| [`../tests/test_task_c_guardrails.py`](../tests/test_task_c_guardrails.py) | Task C submission guardrails and PAY evidence |
| [`../tests/test_task_d_guardrails.py`](../tests/test_task_d_guardrails.py) | Task D submission guardrails and PAY evidence |

### `docs/`

| Path | What it covers |
|---|---|
| [`../docs/README.md`](../docs/README.md) | docs landing page |
| [`../docs/index.md`](../docs/index.md) | benchmark overview |
| [`../docs/tasks.md`](../docs/tasks.md) | task contracts and scoring |
| [`../docs/api-reference.md`](../docs/api-reference.md) | REST API reference |
| [`../docs/architecture.md`](../docs/architecture.md) | architecture deep dive |
| [`../docs/development.md`](../docs/development.md) | this file |
| [`../docs/deployment.md`](../docs/deployment.md) | deployment and runtime configuration |

## Common Workflows

### Changing the environment

Touch at least these files:

- `server/environment.py`
- `server/world_state.py`
- relevant tests in `tests/test_ledgershield_env.py`
- docs in `docs/api-reference.md` or `docs/architecture.md` if the contract changed

### Changing grading

Touch at least these files:

- `server/grading.py`
- `server/trajectory_grading.py`
- any new utility modules such as `server/compliance_engine.py`
- tests in `tests/test_grading.py` and task-specific regression tests

### Adding benchmark realism

Typical landing spots:

- `server/currency_engine.py`
- `server/compliance_engine.py`
- `server/attack_library.py`
- `server/case_factory.py`
- `server/fixtures/cases.json`

### Updating inference behavior

Touch at least these files:

- `inference.py`
- `inference_llm_powered.py` if comparison/debug behavior must stay aligned
- `task_c_guardrails.py` / `task_d_guardrails.py` if structured output rules changed
- `tests/test_inference_contract.py` and relevant inference tests

## Extension Guidance

### Adding a new tool

1. Implement the tool in [`../server/tools.py`](../server/tools.py).
2. Add the action name to [`../server/schema.py`](../server/schema.py).
3. Add cost handling and dispatch in [`../server/environment.py`](../server/environment.py).
4. Add or update signal extraction in [`../server/transition_engine.py`](../server/transition_engine.py) if needed.
5. Add tests and update docs.

### Adding a new case

1. Add it to [`../server/fixtures/cases.json`](../server/fixtures/cases.json).
2. Ensure any needed vendor/PO/receipt/email/ledger fixtures exist.
3. Confirm case IDs are unique.
4. Update [`./tasks.md`](./tasks.md) if the public case catalog changed.
5. Add regression coverage.

### Adding a new attack pattern

1. Extend [`../server/attack_library.py`](../server/attack_library.py).
2. Make sure the resulting reason codes and fraud flags are canonical.
3. Add tests that prove the attack is reachable and meaningful.

## Practical Notes

- The repo uses a mix of benchmark runtime code and historical helper scripts. Prefer editing the core runtime paths first.
- Some top-level report helpers are legacy utilities for saved JSON artifacts rather than part of the main runtime.
- After rerunning `compare_models_live.py`, run `python sync_benchmark_metadata.py` so the published summaries stay aligned with the current artifact snapshot.
- Keep docs and tests in sync with any public contract changes.
