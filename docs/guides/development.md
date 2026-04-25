---
title: "Development"
description: "Local setup, the test suite, CI expectations, repo/file map, and extension guidance for contributors."
icon: "code"
sidebarTitle: "Development"
---

> Source: `docs/development.md` (consolidated)

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

The repo includes [`../.github/workflows/ci.yml`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/.github/workflows/ci.yml), which currently runs:

- pytest on Python 3.11 and 3.12
- Docker build + container smoke test
- `openenv.yaml` metadata validation

Pytest configuration is centralized in [`../pyproject.toml`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/pyproject.toml) under `[tool.pytest.ini_options]`:

- `asyncio_mode = "strict"` with `asyncio_default_fixture_loop_scope = "function"`
- custom `tests` marker
- deprecation-warning filters for `websockets.legacy`

If you change APIs, packaging, or runtime behavior, assume CI should keep passing without special local context.

## Repo Map

### Root files

| Path | What it is for |
|---|---|
| [`../README.md`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/README.md) | top-level benchmark overview and quick start |
| [`../Dockerfile`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/Dockerfile) | container image definition for server deployment |
| [`../pyproject.toml`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/pyproject.toml) | package metadata, dependencies, pytest config |
| [`../requirements.txt`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/requirements.txt) | pinned runtime dependencies |
| [`../uv.lock`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/uv.lock) | lockfile for reproducible dependency installs |
| [`../openenv.yaml`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/openenv.yaml) | OpenEnv metadata, novelty claims, published benchmark numbers |
| [`../__init__.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/__init__.py) | package marker |
| [`../client.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/client.py) | thin HTTP client wrapper for the environment |
| [`../ledgershield_env.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/ledgershield_env.py) | compatibility re-export module for legacy imports |
| [`../models.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/models.py) | shared dataclasses, Pydantic reward model, typed internal returns |
| [`../openenv_compat.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/openenv_compat.py) | adapter around `openenv-core` with local fallback server/client |
| [`../inference.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/inference.py) | submission-safe agent with `ModelCapabilityProfile` tiers, evidence grounding, and strict stdout contract |
| [`../inference_improved.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/inference_improved.py) | experimental improved agent entrypoint |
| [`../inference_llm_powered.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/inference_llm_powered.py) | richer LLM-powered agent used for debugging and comparisons |
| [`../llm_utils.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/llm_utils.py) | JSON parsing and completion helpers for LLM workflows |
| [`../llm_judge_grader.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/llm_judge_grader.py) | optional LLM-as-judge grading experiments |
| [`../compare_models_live.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/compare_models_live.py) | live multi-model comparison with capability profiles, monotonic strength checks, certificate metrics, and institutional-loss metrics |
| [`../sync_benchmark_metadata.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/sync_benchmark_metadata.py) | refreshes README/docs/openenv metadata from current artifacts and runtime defaults |
| [`../compare_all_models.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/compare_all_models.py) | broader multi-model sweep helper with `--models`, `--output`, `--timeout`, and a `0.85`-aligned pass threshold |
| [`../benchmark_report.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/benchmark_report.py) | public benchmark, generated-holdout, blind-control, sleeper-vigilance, ControlBench, certificate-required, human-baseline, and two-agent report generation |
| [`../generate_branch_comparison_report.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/generate_branch_comparison_report.py) | legacy reporting helper for saved branch comparison JSONs |
| [`../generate_comparison_report.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/generate_comparison_report.py) | legacy reporting helper for multi-model JSON summaries |
| [`../generate_final_report.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/generate_final_report.py) | legacy reporting helper for final comparison JSONs |
| [`../generate_sota_report.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/generate_sota_report.py) | legacy reporting helper for SOTA comparison JSONs |
| [`../task_c_guardrails.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/task_c_guardrails.py) | Task C sanitization, composite signal detection, and constructive PAY evidence |
| [`../task_d_guardrails.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/task_d_guardrails.py) | Task D sanitization, composite signal detection, and constructive PAY evidence |
| [`../test_scoring.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/test_scoring.py) | local baseline scoring simulation helper |
| [`../validate_grader.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/validate_grader.py) | end-to-end grader and environment validation script |
| [`../validate_agent_grading.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/validate_agent_grading.py) | score-separation validation helper |
| [`../validate-submission.sh`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/validate-submission.sh) | pre-submission validator for Docker, server health, and stdout contract |
| [`../live_model_comparison.json`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/live_model_comparison.json) | saved live comparison summary artifact |

### `server/`

| Path | What it is for |
|---|---|
| [`../server/__init__.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/__init__.py) | package marker |
| [`../server/app.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/app.py) | FastAPI app builder and endpoint registration |
| [`../server/environment.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/environment.py) | main environment loop, reward shaping, truncation logic, rendering |
| [`../server/world_state.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/world_state.py) | hidden/public state, artifacts, readiness, pressure resistance |
| [`../server/tools.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/tools.py) | investigation tool implementations, email-thread payload construction, domain alignment inference |
| [`../server/transition_engine.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/transition_engine.py) | intervention handling and signal extraction |
| [`../server/grading.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/grading.py) | task-specific grading rubrics |
| [`../server/decision_certificate.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/decision_certificate.py) | Decision Certificate Graph builder/verifier |
| [`../server/institutional_game.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/institutional_game.py) | persistent AP-week memory, loss surface, calibration gate, and sleeper-vendor state |
| [`../server/decision_falsifier.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/decision_falsifier.py) | deterministic terminal-decision falsifier |
| [`../server/control_statechart.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/control_statechart.py) | statechart-style control boundary and prompt-injection-aware runtime safety harness |
| [`../server/trust_graph.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/trust_graph.py) | TrustGraph projection for payment decisions |
| [`../server/trajectory_grading.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/trajectory_grading.py) | trajectory-aware scoring components |
| [`../server/outcome_simulator.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/outcome_simulator.py) | downstream operational/fraud outcome simulation |
| [`../server/risk_rules.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/risk_rules.py) | risk bucket logic and heuristic submission-risk assessment |
| [`../server/pressure_events.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/pressure_events.py) | adversarial pressure-event templates and scoring |
| [`../server/vendor_simulator.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/vendor_simulator.py) | callback vendor-response simulation |
| [`../server/data_loader.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/data_loader.py) | fixture loading, indexing, and generated-case injection |
| [`../server/case_factory.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/case_factory.py) | challenge, procedural holdout ecosystems, benign twins, and ControlBench AP-quarter generation |
| [`../server/attack_library.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/attack_library.py) | 16 adversarial AP fraud attack templates |
| [`../server/schema.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/schema.py) | canonical field/action/reason-code constants and normalizers |
| [`../server/currency_engine.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/currency_engine.py) | multi-currency realism utilities |
| [`../server/compliance_engine.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/compliance_engine.py) | SOX-style internal-control evaluation |
| [`../server/curriculum.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/curriculum.py) | dynamic difficulty adaptation |
| [`../server/dual_agent_mode.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/dual_agent_mode.py) | watchdog-mode dual-agent novelty module |
| [`../server/sprt_engine.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/sprt_engine.py) | sequential hypothesis testing state, likelihood tables, stopping rules |
| [`../server/voi_engine.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/voi_engine.py) | Value-of-Information ranking and action valuation |
| [`../server/proper_scoring.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/proper_scoring.py) | strategy-proof probability scoring utilities |
| [`../server/causal_model.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/causal_model.py) | SCM templates, d-separation oracle, counterfactual helpers |
| [`../server/causal_grader.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/causal_grader.py) | causal sufficiency grading and adjustment |
| [`../server/reward_machine.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/reward_machine.py) | task-family reward machine state |
| [`../server/information_design.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/information_design.py) | Markov persuasion / information-design heuristics |
| [`../server/adversarial_designer.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/adversarial_designer.py) | regret-driven adversarial case analysis |
| [`../server/categorical_composition.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/categorical_composition.py) | compositional task-family semantics |
| [`../server/rl_export.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/rl_export.py) | 37-dimensional RL / Decision Transformer export utilities |

### `server/fixtures/`

| Path | What it stores |
|---|---|
| [`../server/fixtures/cases.json`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/fixtures/cases.json) | the 21 curated benchmark cases |
| [`../server/fixtures/vendors.json`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/fixtures/vendors.json) | vendor master data |
| [`../server/fixtures/vendor_history.json`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/fixtures/vendor_history.json) | historical vendor changes and fraud history |
| [`../server/fixtures/po_records.json`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/fixtures/po_records.json) | purchase-order records |
| [`../server/fixtures/receipts.json`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/fixtures/receipts.json) | goods-receipt records |
| [`../server/fixtures/ledger_index.json`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/fixtures/ledger_index.json) | ledger/payment history used for duplicate detection |
| [`../server/fixtures/email_threads.json`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/fixtures/email_threads.json) | structured email-thread records |
| [`../server/fixtures/policy_rules.json`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/fixtures/policy_rules.json) | policy rules used by `lookup_policy` |

### `tests/`

| Path | What it validates |
|---|---|
| [`../tests/conftest.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/conftest.py) | shared fixtures and suite-wide pytest marker setup |
| [`../tests/test_api_smoke.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/test_api_smoke.py) | API endpoint smoke coverage including ControlBench and human-baseline summary endpoints |
| [`../tests/test_benchmark_report.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/test_benchmark_report.py) | public/holdout/blind/sleeper/ControlBench/certificate-required/human-baseline reporting behavior |
| [`../tests/test_compare_all_models.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/test_compare_all_models.py) | score parsing helpers in broad model sweeps |
| [`../tests/test_compare_models_live.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/test_compare_models_live.py) | live comparison stats, capability profiles, and rendering helpers |
| [`../tests/test_compliance_engine.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/test_compliance_engine.py) | SOX compliance evaluation |
| [`../tests/test_currency_engine.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/test_currency_engine.py) | FX/IBAN/SWIFT/aging-report utilities |
| [`../tests/test_curriculum.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/test_curriculum.py) | curriculum tiering and case selection |
| [`../tests/test_decision_certificate.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/test_decision_certificate.py) | certificate graph verification |
| [`../tests/test_grading.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/test_grading.py) | degenerate evidence cap and grading edge cases |
| [`../tests/test_inference_contract.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/test_inference_contract.py) | required stdout contract for `inference.py` |
| [`../tests/test_inference_llm_powered.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/test_inference_llm_powered.py) | derived thread reasoning in LLM-powered inference |
| [`../tests/test_inference_runtime.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/test_inference_runtime.py) | model capability profiles and runtime heuristics |
| [`../tests/test_institutional_game.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/test_institutional_game.py) | persistent AP-week memory and loss updates |
| [`../tests/test_controlbench.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/test_controlbench.py) | ControlBench sequence generation, procedural holdouts, control-boundary enforcement, TrustGraph persistence, and sleeper-vendor behavior |
| [`../tests/test_ledgershield_env.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/test_ledgershield_env.py) | environment transitions, scoring, and holdout generation |
| [`../tests/test_schema_reason_codes.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/test_schema_reason_codes.py) | reason-code normalization and aliasing |
| [`../tests/test_task_c_guardrails.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/test_task_c_guardrails.py) | Task C submission guardrails and PAY evidence |
| [`../tests/test_task_d_guardrails.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/tests/test_task_d_guardrails.py) | Task D submission guardrails and PAY evidence |

### `docs/`

| Path | What it covers |
|---|---|
| [Documentation Hub](/overview/documentation-hub) | docs landing page |
| [Documentation Index](/overview/documentation-index) | benchmark overview |
| [Tasks](/benchmark/tasks) | task contracts and scoring |
| [API Reference](/api-reference) | REST API reference |
| [Architecture](/architecture/overview) | architecture deep dive |
| [Development](/guides/development) | this file |
| [Deployment](/guides/deployment) | deployment and runtime configuration |

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

1. Implement the tool in [`../server/tools.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/tools.py).
2. Add the action name to [`../server/schema.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/schema.py).
3. Add cost handling and dispatch in [`../server/environment.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/environment.py).
4. Add or update signal extraction in [`../server/transition_engine.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/transition_engine.py) if needed.
5. Add tests and update docs.

### Adding a new case

1. Add it to [`../server/fixtures/cases.json`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/fixtures/cases.json).
2. Ensure any needed vendor/PO/receipt/email/ledger fixtures exist.
3. Confirm case IDs are unique.
4. Update [`./tasks.md`](/benchmark/tasks) if the public case catalog changed.
5. Add regression coverage.

### Adding a new attack pattern

1. Extend [`../server/attack_library.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/attack_library.py).
2. Make sure the resulting reason codes and fraud flags are canonical.
3. Add tests that prove the attack is reachable and meaningful.

## Practical Notes

- The repo uses a mix of benchmark runtime code and historical helper scripts. Prefer editing the core runtime paths first.
- Some top-level report helpers are legacy utilities for saved JSON artifacts rather than part of the main runtime.
- After rerunning `compare_models_live.py`, run `python sync_benchmark_metadata.py` so the published summaries stay aligned with the current artifact snapshot.
- Keep docs and tests in sync with any public contract changes.

---
