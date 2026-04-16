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

# LedgerShield 🛡️

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![CI](https://img.shields.io/badge/ci-github_actions-success.svg)](./.github/workflows/ci.yml)
[![OpenEnv](https://img.shields.io/badge/OpenEnv-compatible-green.svg)](./openenv.yaml)

LedgerShield is a stateful, adversarial benchmark for AI agents operating inside enterprise accounts-payable workflows. Instead of asking a model to classify one document, LedgerShield asks it to investigate, unlock hidden evidence, choose controls, withstand pressure, and submit a proof-carrying decision under budget and step limits.

LedgerShield now formalizes that loop as an **Adversarial Sequential Hypothesis Testing Game (ASHTG)** and extends it into an institutional-intelligence benchmark. The benchmark exposes a sequential hypothesis-testing layer, Value-of-Information tool ranking, proper probability scoring, causal sufficiency grading, a Stackelberg-style watchdog audit policy, persistent AP-week memory, institutional loss accounting, and machine-verifiable decision certificates on top of the existing AP workflow simulation.

> **📖 Documentation hub:** See [`docs/README.md`](./docs/README.md) for a guided tour of all documentation, reading paths by role, and a map of what lives where.

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
| Environment design | ASHTG sequential hypothesis testing, Value-of-Information tool ranking, reward-machine progress, `terminated` vs `truncated`, text `render()`, formal `action_space()` and `observation_space()` |
| Task and grader quality | 21 curated benchmark cases, causal sufficiency grading, proper scoring over latent hypotheses, semantic counterfactual scoring, stricter degenerate-submission penalties, generated holdout suites, contrastive benign twins |
| Code quality | Comprehensive docstrings, shared pytest fixtures, dedicated tests for grading/currency/compliance/curriculum/certificates/institutional memory, GitHub Actions CI, narrower exception handling, typed internal return contracts |
| Creativity and novelty | ASHTG formalism, Stackelberg watchdog mode, dynamic curriculum adaptation, campaign-level fraud reasoning, persistent institutional memory, executable decision certificates, 16 attack types across identity/document/process/APT categories |

## Benchmark At A Glance

| Item | Value |
|---|---:|
| Public benchmark cases | 21 curated base cases |
| Task families | 5 (`task_a` through `task_e`) |
| Attack types | 16 |
| Default loader behavior | 21 benchmark cases + 24 generated challenge variants = 45 loaded cases |
| Optional generated suites | challenge variants, holdout variants, contrastive benign twins |
| Formal model | ASHTG with SPRT belief state and VoI action ranking |
| Institutional track | persistent AP-week memory, capacity, attacker belief, and loss ledger |
| Certificate track | Decision Certificate Graph verifier for proof-carrying payment decisions |
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

The submission is not just a label. Strong agents are expected to return structured decisions with grounded `reason_codes`, `policy_checks`, `evidence_map`, `decision_certificate`, and task-specific fields like duplicates, campaign signals, discrepancies, or extracted invoice fields.

The final payload can also include `predicted_probabilities`, a calibrated probability distribution over latent hypotheses such as `safe`, `bank_fraud`, `duplicate_billing`, or `campaign_fraud`. If this field is omitted, LedgerShield derives a backward-compatible default from `decision`, `confidence`, and the current SPRT posterior.

The final payload can also include a `decision_certificate`: a typed Decision Certificate Graph with artifact, observation, hypothesis, policy, intervention, decision, and counterfactual nodes. The verifier checks support paths, reference grounding, contradiction handling, stability, and minimality. Legacy submissions get a synthesized diagnostic certificate; agent-authored certificates can receive a small auditability adjustment.

### Agent capability tiers

The inference agent (`inference.py`) uses a `ModelCapabilityProfile` that adapts behavior to model strength:

<!-- sync:readme-capability-table:start -->
| Tier | Capability score | Plan mode | Repair level | Budget bonus |
|---|---|---|---|---|
| Elite | >= 5.0 | `llm` | `partial` | +2 investigation, +2 intervention |
| Strong | >= 4.5 | `hybrid` | `partial` | +1 investigation, +1 intervention |
| Standard | < 4.5 | `llm` | `none` | baseline |
<!-- sync:readme-capability-table:end -->

The capability profile only adjusts planning depth and budget. It does not hard-snap stronger models onto a deterministic grounded policy. In the code, `llm` is the internal label for the LLM-first planning path.

### Smart signal derivation

The agent and server now share improved signal-extraction logic:

- **Domain alignment inference** — sender domains are compared against vendor-approved domains using token overlap, not just exact match. This catches spoofs like `ceo@acme-corp.com` vs approved `acme.com`.
- **Composite risk flags** — `bank_override_attempt` now requires `bank_change_language` *and* a risk amplifier (domain mismatch, callback discouragement, policy override, or urgency). Isolated bank language no longer triggers false fraud flags.
- **PAY evidence** — safe PAY decisions now carry constructive evidence (verified bank, verified sender, cleared duplicates) instead of empty evidence maps. This avoids degenerate-evidence penalties on benign cases.

## Upgrade Snapshot

The benchmark upgrade work is reflected in the codebase across five phases:

| Phase | Highlights |
|---|---|
| Phase 1: Real-world utility | `server/currency_engine.py`, `server/compliance_engine.py`, richer payment artifacts, aging-report support |
| Phase 2: Task and grader quality | 21 curated cases, semantic counterfactual grading, tighter degenerate penalties, generated holdouts |
| Phase 3: Environment design | `SHAPING_SCALE=0.35`, `INFO_GAIN_BONUS=0.08`, milestone rewards, Gymnasium-style truncation semantics, text rendering, formal spaces |
| Phase 4: Code quality | docstrings across core modules, `tests/conftest.py`, CI workflow, `TypedDict` internal returns |
| Phase 5: Creativity and novelty | Dec-POMDP watchdog mode, curriculum adaptation, 16-attack library, exploration bonus integrated into `step()` |
| Phase 6: ASHTG | `server/sprt_engine.py`, `server/voi_engine.py`, `server/proper_scoring.py`, `server/causal_model.py`, `server/causal_grader.py`, `server/reward_machine.py`, `server/rl_export.py` |
| Phase 7: Institutional intelligence | `server/institutional_game.py`, `server/decision_certificate.py`, blind/instrumented tracks, `/institutional-memory`, `/institutional-reset`, certificate and institutional metrics in live comparisons |

## ASHTG Mathematical Framework

LedgerShield formalizes fraud investigation as an **Adversarial Sequential Hypothesis Testing Game (ASHTG)** — a theoretically grounded framework that unifies five distinct mathematical traditions never previously combined in a single evaluation environment.

> **📖 Full theoretical treatment with 30 citations**: [`docs/ashtg-theory.md`](./docs/ashtg-theory.md)

### The Five Mathematical Pillars

| Pillar | Theory | Source File | Key Property |
|---|---|---|---|
| Sequential Investigation | **Wald's SPRT** (1945) — optimal stopping | `server/sprt_engine.py` | Terminates at provably minimum number of steps |
| Causal Grading | **Pearl's SCM** (2009) — 3-level causality | `server/causal_model.py` + `causal_grader.py` | Grades do-calculus interventions and counterfactuals |
| Value of Information Rewards | **Howard's VoI** (1966) + **Lindley** (1956) | `server/voi_engine.py` | Rewards derived from information economics, not hand-tuned |
| Strategy-proof Grading | **Gneiting-Raftery Proper Scoring** (2007) | `server/proper_scoring.py` | Mathematically proven: misreporting belief cannot improve score |
| Watchdog Audit Policy | **Tambe Stackelberg SSE** (2011) | `server/dual_agent_mode.py` | Watchdog commits to optimal mixed audit strategy |

And five additional innovations:

| Innovation | Theory | Source File |
|---|---|---|
| Bayesian Information Design | **Kamenica-Gentzkow** (2011) | `server/information_design.py` |
| Adversarial PCG | **PAIRED / Regret-based UED** (2021) | `server/adversarial_designer.py` |
| Temporal Progress Tracking | **LTLf Reward Machines** (2018) | `server/reward_machine.py` |
| Algebraic Task Composition | **Categorical MDP Pushouts** (2022) | `server/categorical_composition.py` |
| RL Training Export | **Decision Transformer** (2021) | `server/rl_export.py` |

### Why This Is Novel

Every other benchmarking environment uses **hand-tuned rewards**. LedgerShield computes rewards from the **Value of Information**:

```
VoI(tool) = E[max_a U(a, θ) | posterior after tool] - max_a E[U(a, θ)] - cost(tool)
```

Every other environment lets agents game it by expressing false confidence. LedgerShield uses **strictly proper scoring rules** — provably strategy-proof functions where the agent's dominant strategy is always to report their true beliefs.

Every other environment uses heuristic investigation metrics. LedgerShield formalizes the investigation as a **Sequential Probability Ratio Test** with Wald's optimal stopping boundaries:

```
Upper boundary A = log((1-β)/α) ≈ 2.89    [Type I error ≤ α = 5%]
Lower boundary B = log(β/(1-α)) ≈ -2.25   [Type II error ≤ β = 10%]
```

The agent receives `sprt_state` at every step with live `posterior_probabilities`, `belief_entropy`, `distance_to_boundary`, and an `optimal_stopping_reached` flag — giving agents the signal to investigate exactly as long as they need to, and no longer.

### Categorical MDP Composition

Task families are formally defined via **categorical pushouts**. Task E = Task D ⊔ CampaignDetection — the colimit of two MDPComponents. This gives a rigorous algebraic foundation for why Task E is strictly harder, and exposes the `mdp_component` field in every `reset()` observation:

```json
"mdp_component": {
  "component_name": "BaseInvestigation+DocumentExtraction+ThreeWayMatch+DuplicateDetection+IdentityVerification+CampaignDetection",
  "action_space": ["compare_bank_account", "inspect_email_thread", "route_to_security", ...],
  "temporal_spec": "(F submit_decision) and (F ocr) and ... and (F route_to_security)"
}
```

### RL Export — 37-Dimensional State Vector

At every `step()`, `info["rl_data_plane"]["state_vector"]` contains a 37-dimensional float vector encoding SPRT belief state, VoI frontier, reward machine progress, watchdog suspicion, and calibration history — enabling offline RL training from episode traces.

### Recent patch-level changes

| Change | Where | Why |
|---|---|---|
| `DEGENERATE_EVIDENCE_CAP` applied correctly | `server/grading.py` | Bug fix: empty evidence now correctly receives cap value instead of collapsing to `0.0` |
| Model capability profiles and tiered agent behavior | `inference.py` | Agent adapts investigation/repair strategy based on model tier (elite/strong/standard) |
| Composite `bank_override_attempt` signal | `server/tools.py`, `task_c_guardrails.py`, `task_d_guardrails.py` | Bank override flag now requires bank-change language *plus* a risk amplifier — reduces false positives |
| Domain alignment via token overlap | `server/tools.py`, `inference.py` | Catches spoofs where sender domain shares tokens with vendor name but is not an exact match |
| Constructive PAY evidence maps | `task_c_guardrails.py`, `task_d_guardrails.py` | Safe PAY decisions carry verified-bank / cleared-duplicates evidence instead of empty maps |
| Per-model capability profiles in live comparison | `compare_models_live.py` | Records model tier, capability score, and monotonic strength checks alongside scores |
| `pytest` config in `pyproject.toml` | `pyproject.toml` | Asyncio mode, markers, deprecation-warning filters |

## Benchmarking Story

LedgerShield is not just a server. It includes a full evaluation stack:

- `benchmark_report.py` scores the public benchmark, generated holdout suites, and contrastive adversarial/benign pairs.
- `compare_models_live.py` runs live head-to-head evaluations with per-model capability profiles and writes per-case debug traces including monotonic strength ordering checks.
- `live_model_comparison_debug/` stores action traces, planning traces, score breakdowns, and system state snapshots for diagnosis.
- `/leaderboard` and `/benchmark-report` expose report artifacts through the API when generated.

### Latest local live comparison

Live comparison numbers should be treated as generated artifacts, not hardcoded documentation. Run:

```bash
python compare_models_live.py \
  --models gpt-3.5-turbo,gpt-4o,gpt-5.4 \
  --output live_model_comparison.json
```

Then inspect:

- `live_model_comparison.json` for summary metrics, per-case scores, model profiles, and ordering checks
- `live_model_comparison_debug/<model>/` for per-case traces, submissions, and score breakdowns

<!-- sync:readme-live-comparison:start -->
## Live Comparison Snapshot

Generated on **April 10, 2026 (IST)** from `live_model_comparison.json`.

| Model | Tier | Capability | Average Score | Success Rate | Min Score | Max Score | API Calls |
|---|---|---:|---:|---:|---:|---:|---:|
| `gpt-3.5-turbo` | standard | 3.2 | 0.6965 | 38.1% | 0.06 | 0.99 | 63 |
| `gpt-4o` | strong | 4.6 | 0.8947 | 90.5% | 0.56 | 0.99 | 64 |
| `gpt-5.4` | elite | 5.4 | 0.9177 | 95.2% | 0.58 | 0.99 | 64 |

- Audit metrics are not present in this historical artifact. Rerun `compare_models_live.py` with the current code to populate certificate and institutional-loss columns.

- Capability ordering is monotonic across the compared models: `true`.
- Current frontier gap (`gpt-5.4` vs `gpt-4o`): `+0.0229` average score and `+4.8%` success rate.
- Refresh after rerunning the live comparison artifact:
```bash
python compare_models_live.py \
  --models gpt-3.5-turbo,gpt-4o,gpt-5.4 \
  --output live_model_comparison.json
python sync_benchmark_metadata.py
```
<!-- sync:readme-live-comparison:end -->

The repo keeps the generated artifact and full trace folder so readers can verify the claim instead of trusting a hand-written summary.

Published benchmark metadata in [`openenv.yaml`](./openenv.yaml) records meaningful public-vs-holdout separation for the packaged baseline report. That report is distinct from `live_model_comparison.json`, which tracks external live-model runs:

<!-- sync:readme-benchmark-summary:start -->
| Agent | Public mean | Holdout mean | Holdout consistent pass rate |
|---|---:|---:|---:|
| ledgershield/deterministic-baseline (deterministic-policy) | 0.9018 | 0.7124 | 0.2222 |
<!-- sync:readme-benchmark-summary:end -->

That gap is deliberate: the benchmark looks easy on clean public cases and much harder on generated holdouts, adversarial variants, and expert Task E scenarios.

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

python sync_benchmark_metadata.py
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
| [`docs/ashtg-theory.md`](./docs/ashtg-theory.md) | **30-citation ASHTG theoretical framework** — SPRT, VoI, Proper Scoring, SCM, Stackelberg, Reward Machines, Categorical MDP |

Recommended reading paths:

- Benchmark judge or first-time reader: [`docs/index.md`](./docs/index.md) -> [`docs/tasks.md`](./docs/tasks.md) -> [`docs/architecture.md`](./docs/architecture.md)
- Agent builder: [`docs/tasks.md`](./docs/tasks.md) -> [`docs/api-reference.md`](./docs/api-reference.md) -> [`docs/development.md`](./docs/development.md)
- Contributor: [`docs/development.md`](./docs/development.md) -> [`docs/architecture.md`](./docs/architecture.md)
- Operator: [`docs/deployment.md`](./docs/deployment.md) -> [`docs/api-reference.md`](./docs/api-reference.md)

## Repository Structure

### Top level

```text
Meta-s-LedgerShield/
├── README.md
├── docs/
├── server/
├── tests/
├── inference.py
├── inference_improved.py
├── inference_llm_powered.py
├── task_c_guardrails.py
├── task_d_guardrails.py
├── benchmark_report.py
├── compare_models_live.py
├── sync_benchmark_metadata.py
├── compare_all_models.py
├── llm_utils.py
├── llm_judge_grader.py
├── models.py
├── client.py
├── ledgershield_env.py
├── openenv_compat.py
├── openenv.yaml
├── pyproject.toml
├── requirements.txt
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
| `server/tools.py` | investigation tool implementations, email thread parsing, domain alignment inference |
| `server/currency_engine.py` | FX conversion, IBAN/SWIFT checks, currency mismatch detection, aging reports |
| `server/compliance_engine.py` | SOX-style AP control evaluation |
| `server/curriculum.py` | dynamic difficulty adaptation |
| `server/dual_agent_mode.py` | Dec-POMDP watchdog/auditor mode with Stackelberg SSE |
| `server/sprt_engine.py` | **Pillar 1** — Wald SPRT optimal stopping, 12 hypotheses, 9 likelihood tables |
| `server/causal_model.py` | **Pillar 2** — Pearl SCM with 17 scenario templates, d-separation, counterfactuals |
| `server/causal_grader.py` | **Pillar 2** — 3-level causal grading (association, intervention, counterfactual) |
| `server/voi_engine.py` | **Pillar 3** — Value of Information action ranking, myopic and non-myopic planning |
| `server/proper_scoring.py` | **Pillar 4** — Brier, log, penalized, calibration ECE, composite proper scoring |
| `server/reward_machine.py` | **Pillar 5** — LTLf reward machines for all 5 task families |
| `server/information_design.py` | **Pillar 7** — Kamenica-Gentzkow Bayesian persuasion environment |
| `server/adversarial_designer.py` | **Pillar 8** — PAIRED regret-guided adversarial PCG |
| `server/categorical_composition.py` | **Pillar 9** — Categorical MDP pushout composition, wired into reset() |
| `server/rl_export.py` | **Pillar 10** — 37-dimensional RL state vector export |
| `benchmark_report.py` | public benchmark + holdout + contrastive reporting |
| `compare_models_live.py` | live multi-model evaluation with capability profiles and debug artifacts |
| `sync_benchmark_metadata.py` | refreshes README/docs/openenv metadata from the current artifacts and runtime defaults |
| `inference.py` | submission-safe agent with ModelCapabilityProfile tiers and evidence-grounded output |
| `inference_improved.py` | experimental improved agent entrypoint |
| `inference_llm_powered.py` | richer LLM-powered agent used for debugging and comparisons |
| `task_c_guardrails.py` / `task_d_guardrails.py` | grounded output sanitizers with composite signal detection and PAY evidence construction |
| `llm_utils.py` | JSON parsing and completion helpers for LLM workflows |
| `llm_judge_grader.py` | optional LLM-as-judge grading experiments |
| `models.py` | shared dataclasses and Pydantic reward model |
| `.github/workflows/ci.yml` | pytest, Docker build, and metadata validation in CI |

For the full file-by-file map, see [`docs/development.md`](./docs/development.md).

## Current Engineering Status

- Core environment upgrades from Phases 1 through 5 are implemented in code.
- Patch-level fixes applied: correct `DEGENERATE_EVIDENCE_CAP` in grading, composite bank-override signal, domain-alignment token overlap, constructive PAY evidence in guardrails.
- The agent (`inference.py`) now uses `ModelCapabilityProfile` tiers (elite/strong/standard) that adapt planning mode, repair level, and budget bonuses.
- `compare_models_live.py` records per-model capability profiles and includes monotonic strength ordering checks.
- The repo includes 21 curated benchmark cases and generated challenge/holdout tooling.
- CI is present via GitHub Actions with pytest config now in `pyproject.toml`.
- The test suite includes API smoke, grading, environment, inference, inference-runtime, compliance, currency, curriculum, and guardrail coverage.
- The environment remains submission-compatible through `inference.py`.

## Safety Note

LedgerShield is a benchmark and simulation environment. It models payment-integrity risk and enterprise controls, but it is not a production fraud platform and should not be used to approve or block real payments without independent controls, audit, and governance.
