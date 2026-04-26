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

# LedgerShield ControlBench 🛡️

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![CI](https://img.shields.io/badge/ci-github_actions-success.svg)](./.github/workflows/ci.yml)
[![OpenEnv](https://img.shields.io/badge/OpenEnv-compatible-green.svg)](./openenv.yaml)

**Runnable Hugging Face Space:** https://huggingface.co/spaces/shreayas/ledgershield-controlbench

**Training evidence report:** [`docs/training-report.md`](./docs/training-report.md)

**Exquisite training layer:** [`docs/exquisite-training-layer.md`](./docs/exquisite-training-layer.md)

**Short mini-blog source:** [`docs/HF_MINIBLOG_FINAL.md`](./docs/HF_MINIBLOG_FINAL.md)

**Consolidated writeup / mini-blog / demo script:** [`docs/DOCUMENTATION.md`](./docs/DOCUMENTATION.md)

LedgerShield ControlBench is a verified benchmark for **institutional control intelligence** in enterprise accounts-payable workflows. It is designed for the Round 2 framing of **World Modeling — Professional Tasks**, with **Long-Horizon Planning & Instruction Following** as the secondary theme.

Instead of asking an agent to classify one invoice, LedgerShield asks it to operate a defensible enterprise control regime: investigate, apply controls, absorb delayed evidence, manage AP-week capacity, withstand adversarial pressure, and submit an auditable decision that can be checked against hidden backend state.

The environment keeps the existing AP/BEC domain, proof-carrying decision certificates, institutional memory, and OpenEnv-compatible FastAPI loop, but the public benchmark contract is now sharper:

- `blind` is the default observation mode for benchmark runs
- official tracks now cover `Case`, `Portfolio`, `Adversarial Data`, `Generated Holdout`, `ControlBench`, `Sleeper-Vigilance`, `Blind-Control`, `Certificate-Required`, and `Human-Baseline`
- headline metrics now include `control_satisfied_resolution`, `institutional_utility`, `institutional_loss_score`, `loss_surface`, calibration-gated authority, and `unsafe_release_rate`
- holdout and contrastive reporting is mechanism-aware rather than surface-only
- certificates remain an audit layer, not a shortcut around bad control behavior; the Certificate-Required track caps scores when the agent does not author a valid proof graph

> **Documentation hub:** See [`docs/DOCUMENTATION.md`](./docs/DOCUMENTATION.md) for the full consolidated documentation (reading paths, task contracts, API reference, architecture, ASHTG theory, deployment, verification reports, and the file-level implementation deep-dive).
>
> **Submission assets:** [Training evidence report](./docs/training-report.md) · [Mini-blog source](./docs/HF_MINIBLOG_FINAL.md) · [Benchmark card](./docs/DOCUMENTATION.md#benchmark-card) · [Demo script](./docs/DOCUMENTATION.md#demo-script)

## Why This Matters

Real-world payment fraud is expensive and operationally messy. In the FBI IC3 2023 report, business email compromise (BEC) generated **21,489 complaints and more than $2.9 billion in reported losses**, while total cybercrime losses exceeded **$12.5 billion**. LedgerShield turns that risk surface into an agent benchmark focused on safe decision-making, evidence quality, and control discipline instead of one-shot classification.

Sources:

- [FBI IC3 2023 Internet Crime Report](https://www.ic3.gov/annualreport/reports/2023_ic3report.pdf)
- [OpenEnv metadata for this benchmark](./openenv.yaml)

## Evaluation Dimensions

LedgerShield is designed to test agent behavior along five dimensions:

| Dimension | Implementation |
|---|---|
| **Real-world utility** | Multi-currency invoices, IBAN/SWIFT validation, SOX controls, AP inbox triage, campaign fraud, aging reports |
| **Task quality** | 21 curated cases, 5 task families (extraction, matching, duplicates, BEC triage, campaigns), holdout/contrastive generalization |
| **Environment design** | Blind mode by default, partial observability, institutional memory, AP-week queue pressure, evidence delay, adversarial pressure, sleeper-vendor sequences |
| **Code quality** | Comprehensive tests, fixtures, docstrings, typed contracts, narrow exception handling, CI/CD |
| **Novelty** | Formal ASHTG framework, VoI-based action ranking, causal grading, decision certificates, institutional loss surface, calibration gate, 16 attack types |

---

## Key Innovations

LedgerShield is positioned as a deployment-grade control benchmark for enterprise AI agents rather than a single-task RL environment. In addition to solving each case, an agent is evaluated on whether it remains safe over time, remains calibrated, preserves institutional trust, justifies its decisions, and survives adversarial audit.

The benchmark is built around eight design pillars.

### 1. Persistent institutional memory across episodes

Most RL environments reset all state between episodes. LedgerShield retains long-horizon institutional state across cases: vendor trust history, attacker belief updates, fraud losses released or prevented, queue and capacity pressure, and authority degradation. The benchmark therefore evaluates whether the agent is safe for a real organization, not only good on isolated cases.

See [Institutional Memory Layer](./docs/DOCUMENTATION.md#architecture) and `server/institutional_game.py`.

### 2. Calibration-gated authority

Agent authority is dynamic rather than fixed. Based on calibration quality, catastrophic mistakes, and institutional outcomes, the system transitions the agent between `full_authority`, `restricted_authority`, `review_only`, and `locked`. The thresholds (`≤0.12` healthy, `0.22` elevated → restricted, `0.34` high → review_only) are derived from a running squared calibration error and enforced for every subsequent case. The benchmark therefore evaluates not only task performance but whether the agent retains operational authority.

See [Headline Metrics](#headline-metrics) and `_update_calibration_gate()` in `server/institutional_game.py`.

### 3. Sleeper-vendor vigilance

LedgerShield includes vendors that appear benign for an extended trust-building period and later activate fraud. The benchmark therefore evaluates resistance to long-con enterprise fraud rather than only immediate anomalies.

See the [Sleeper-Vigilance Track](#official-tracks) and `server/case_factory.py`.

### 4. Proof-carrying decision certificates

Submissions can be required to include a typed Decision Certificate Graph containing artifact, observation, hypothesis, policy, intervention, decision, and counterfactual nodes, connected by support, contradiction, and requirement edges. The verifier checks support paths, reference grounding, contradiction handling, stability, and minimality. The benchmark therefore evaluates whether the agent produces auditable proof structures alongside its decisions.

See [Decision Certificates](./docs/DOCUMENTATION.md#architecture) and `server/decision_certificate.py`.

### 5. Deterministic falsifier and TrustGraph audit layer

After each decision the environment runs a deterministic falsifier, tests for unsupported claims, detects unsafe `PAY` decisions, and projects the decision into a TrustGraph for downstream auditability. The benchmark therefore evaluates whether decisions survive adversarial post-hoc review, not only whether they earn reward.

See [TrustGraph And Decision Falsification](./docs/DOCUMENTATION.md#architecture), `server/decision_falsifier.py`, `server/trust_graph.py`.

### 6. FraudGen with solvability manifests

Generated fraud cases ship with structured manifests describing scenario type, difficulty band, attack profile, solvability path, required tools, revealable artifacts, and validation metadata. The benchmark therefore offers procedural case generation with solvability guarantees rather than unconstrained random synthesis.

See [Generated Variants And Holdouts](./docs/DOCUMENTATION.md#tasks) and `server/case_factory.py`.

### 7. Institutional loss surface

Outcomes are evaluated via a multi-dimensional loss surface covering fraud loss released, false positive cost, operational delay, review burn, supplier friction, calibration debt, vigilance loss, authority restriction, and catastrophic events. The benchmark therefore models the trade-offs an enterprise actually optimizes — risk, cost, and trust — rather than collapsing to a single scalar reward.

See [Headline Metrics](#headline-metrics).

### 8. ControlBench deployability framing

Beyond per-case correctness, ControlBench evaluates whether the agent stays calibrated, retains authority, remains auditable, and avoids damaging the institution over a full AP quarter. The benchmark therefore measures deployability under enterprise constraints in addition to capability.

---

## Benchmark At A Glance

| Item | Value |
|---|---:|
| Benchmark identity | verified institutional control intelligence |
| Public observation mode | blind by default |
| Official tracks | 9 (`case`, `portfolio`, `adversarial`, `generated_holdout`, `controlbench`, `sleeper_vigilance`, `blind_control`, `certificate_required`, `human_baseline`) |
| Public benchmark cases | 21 curated base cases |
| Holdout / contrastive support | latent-mechanism holdouts + benign twins |
| ControlBench sequence | seeded AP-quarter generator with standard 100-case mode and lightweight report preview |
| Headline metrics | control-satisfied resolution, institutional utility, institutional loss score, loss surface, certificate-required mean, unsafe release rate |
| Formal model | ASHTG with SPRT belief state and VoI action ranking |
| Institutional layer | persistent AP-week memory, capacity, attacker belief, and loss ledger |
| Audit layer | Decision Certificate Graph verifier for proof-carrying payment decisions |
| Server runtime | FastAPI / OpenEnv-compatible |

## Official Tracks

| Track | What it tests |
|---|---|
| Case Track | single-case control performance, evidence quality, intervention use, and safe resolution |
| Portfolio Track | AP-week utility under queue pressure, finite callback/review capacity, and attacker adaptation |
| Adversarial Data Track | robustness to deceptive content in email threads, documents, and tool outputs |
| Generated Holdout Track | seeded procedural AP ecosystems that test unseen mechanism combinations and anti-overfit robustness |
| ControlBench Track | long-horizon institutional-control authority using loss surface, calibration gate, and sleeper-vendor vigilance |
| Sleeper-Vigilance Track | trust-building vendor sequences that later activate bank-change or BEC fraud |
| Blind-Control Track | benchmark runs where SPRT, VoI, and reward-machine scaffolding stay hidden from the acting agent |
| Certificate-Required Track | strict proof-carrying evaluation where auto-generated compatibility certificates cannot receive full credit |
| Human-Baseline Track | optional AP/accounting/audit participant evaluations used as an operational realism anchor |

## Headline Metrics

| Metric | Meaning |
|---|---|
| `control_satisfied_resolution` | the case was correct, policy-complete, grounded, certificate-supported, and free of catastrophic unsafe shortcuts |
| `institutional_utility` | institution-level value after fraud loss, unsafe release cost, review burn, supplier friction, and auditability |
| `institutional_loss_score` | normalized ControlBench score over cumulative fraud loss, false positives, operational burn, calibration debt, vigilance loss, compliance, and catastrophic events |
| `loss_surface` | auditable vector of the institutional-loss components rather than a single hidden scalar |
| `authority_level` | calibration-gated deployment status such as `full_authority`, `restricted_authority`, or `review_only` |
| `sleeper_detection_rate` | fraction of trust-building sleeper activations detected before unsafe release |
| `certificate_required_mean` | score under strict agent-authored certificate gates |
| `adversarial_falsifier_verdict` | deterministic adversarial-review diagnostic over unsafe PAY, unsupported claims, pending artifacts, and certificate failure |
| `human_baseline_track` | optional AP-analyst reference profile loaded from `artifacts/human_baseline.json` or its configured path |
| `unsafe_release_rate` | fraction of cases where the agent released money unsafely |
| `result_class` | visible evaluator status such as `valid_success`, `correct_but_policy_incomplete`, or `unsafe_release` |

### Task coverage

| Task | Count | Focus |
|---|---:|---|
| Task A | 4 | proof-carrying invoice extraction, multilingual and multi-currency artifacts |
| Task B | 5 | three-way match, receipt gaps, quantity/tax discrepancies |
| Task C | 4 | duplicate detection, cross-vendor fraud, approval-threshold evasion |
| Task D | 6 | AP inbox/BEC triage, workflow override, CEO fraud, benign vendor updates |
| Task E | 2 | coordinated campaigns and supply-chain-compromise APT scenarios |

## Agent Action Space

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

The final payload can also include `predicted_probabilities`, a calibrated probability distribution over latent hypotheses such as `safe`, `bank_fraud`, `duplicate_billing`, or `campaign_fraud`. If this field is omitted, LedgerShield derives a backward-compatible default from `decision`, `confidence`, and the current SPRT posterior. Missing or degenerate confidence now explicitly restricts future authority in ControlBench sequences.

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

### Signal derivation

The agent and server share improved signal-extraction logic:

- **Domain alignment inference** — sender domains are compared against vendor-approved domains using token overlap, not just exact match. This catches spoofs like `ceo@acme-corp.com` vs approved `acme.com`.
- **Composite risk flags** — `bank_override_attempt` now requires `bank_change_language` *and* a risk amplifier (domain mismatch, callback discouragement, policy override, or urgency). Isolated bank language no longer triggers false fraud flags.
- **PAY evidence** — safe PAY decisions now carry constructive evidence (verified bank, verified sender, cleared duplicates) instead of empty evidence maps. This avoids degenerate-evidence penalties on benign cases.

---

## Technical Deep Dives (Implementation Details)

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
| Phase 8: ControlBench | `server/case_factory.py`, `benchmark_report.py`, `/controlbench-summary`, institutional loss surface, calibration-gated authority, sleeper-vendor AP-quarter generation |
| Phase 9: Trust and falsification | `server/trust_graph.py`, `server/decision_falsifier.py`, `server/control_statechart.py`, Certificate-Required track, deterministic decision falsifier, statechart-style control boundary, persistent TrustGraph projection, two-agent control-profile report |
| Phase 10: Certify and experiments | `server/certify.py`, `server/visualization.py`, `/certify`, `/certify-summary`, `/controlbench-visualization`, independent FraudGen ecosystem generation, ablation suite, cost sensitivity, baseline matrix |

## ASHTG Mathematical Framework

LedgerShield formalizes fraud investigation as an **Adversarial Sequential Hypothesis Testing Game (ASHTG)** — a framework combining five mathematical traditions in a single evaluation environment.

The metrics, tracks, and task suite are self-contained, so understanding ASHTG is not required to evaluate agent performance. This section is for readers interested in the formal foundations.

> **Full theoretical treatment with 30 citations**: [ASHTG Theory section](./docs/DOCUMENTATION.md#ashtg-theory)

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

### Reward and grading design

Rather than hand-tuned rewards, LedgerShield computes rewards from the **Value of Information**:

```
VoI(tool) = E[max_a U(a, θ) | posterior after tool] - max_a E[U(a, θ)] - cost(tool)
```

Confidence reporting is graded with **strictly proper scoring rules** — strategy-proof functions where truthful belief reporting is the dominant strategy.

Investigation length is governed by a **Sequential Probability Ratio Test** with Wald's optimal stopping boundaries:

```
Upper boundary A = log((1-β)/α) ≈ 2.89    [Type I error ≤ α = 5%]
Lower boundary B = log(β/(1-α)) ≈ -2.25   [Type II error ≤ β = 10%]
```

The agent receives `sprt_state` at every step with live `posterior_probabilities`, `belief_entropy`, `distance_to_boundary`, and an `optimal_stopping_reached` flag, giving the agent a principled signal for when sufficient evidence has been gathered.

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

## Evaluation Stack

LedgerShield ships with a full evaluation stack alongside the environment server:

- `benchmark_report.py` scores the public benchmark, generated holdout suites, and contrastive adversarial/benign pairs.
- The same report includes `controlbench_quarter`, a seeded long-horizon institutional sequence with loss surface, calibration gate, authority timeline, sleeper detection, and deployability rating.
- Reports also include `certificate_required_track` and `controlbench_two_agent_demo`, providing proof-gated scores and accuracy-vs-loss disagreement diagnostics without LLM credits.
- `compare_models_live.py` runs live head-to-head evaluations with per-model capability profiles and writes per-case debug traces including monotonic strength ordering checks.
- `live_model_comparison_debug/` stores action traces, planning traces, score breakdowns, and system state snapshots for diagnosis.
- `/leaderboard`, `/benchmark-report`, `/controlbench-summary`, and `/human-baseline-summary` expose report artifacts or live summaries through the API when generated.

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
| Agent | Public mean | Holdout mean | Holdout consistent pass rate | ControlBench loss score | Deployability | Certificate-required mean |
|---|---:|---:|---:|---:|---|---:|
| ledgershield/deterministic-baseline (deterministic-policy) | 0.8749 | 0.7063 | 0.1667 | 0.5731 | advisory | 0.5500 |
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

# Full 100-case ControlBench AP-quarter run
python benchmark_report.py --format markdown --controlbench-sequence-length 100
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

### 7. Train With TRL

The training runner collects trajectories through live LedgerShield `reset()` and `step()` calls before fine-tuning. The committed run used Hugging Face Jobs on `a10g-large` hardware with `Qwen/Qwen2.5-0.5B-Instruct`, logged every optimizer-step loss, evaluated rewards during training, uploaded the LoRA adapter/tokenizer, and generated a 23-plot analysis pack.

```bash
export HF_TOKEN="your_token"
python training/launch_hf_a10g_qwen_job.py \
  --repo-id shreayas/ledgershield-controlbench \
  --hardware A10G_LARGE \
  --output-dir artifacts/trl-openenv-hf-a10g-qwen-rich \
  --max-steps 900 \
  --case-limit 45 \
  --model-eval-case-limit 9 \
  --reward-eval-interval 300
```

Fast smoke test without model training:

```bash
python training/ledgershield_trl_training.py \
  --output-dir artifacts/trl-openenv-smoke \
  --case-limit 5
```

Training assets:

| Asset | Path |
|---|---|
| Judge-facing training report | [`docs/training-report.md`](./docs/training-report.md) |
| OpenEnv-connected TRL runner | [`training/ledgershield_trl_training.py`](./training/ledgershield_trl_training.py) |
| Re-runnable Colab notebook | [`training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb`](./training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb) |
| HF A10G Qwen launcher | [`training/launch_hf_a10g_qwen_job.py`](./training/launch_hf_a10g_qwen_job.py) |
| Training dependency pins | [`training/requirements-training.txt`](./training/requirements-training.txt) |
| Plot renderer | [`training/plot_training_results.py`](./training/plot_training_results.py) |

Current real-run evidence is committed under `artifacts/trl-openenv-hf-a10g-qwen-rich/`. The run collected 45 live trajectories from the environment, trained on 36 cases, evaluated on 9 held-out cases, ran 900 TRL optimizer steps, and reached final training loss `0.0885`.

HF training job: https://huggingface.co/jobs/shreayas/69ecd421d70108f37acde80d

Observed hardware: `NVIDIA A10G` on Hugging Face Jobs `a10g-large` with `22.3 GB` GPU memory.

Loss records: `900` optimizer-step rows, from first logged loss `1.6154` to final logged loss `0.0009`.

Loss logs:

| Artifact | Path |
|---|---|
| Step-by-step CSV | [`artifacts/trl-openenv-hf-a10g-qwen-rich/loss_history.csv`](./artifacts/trl-openenv-hf-a10g-qwen-rich/loss_history.csv) |
| Step-by-step JSON | [`artifacts/trl-openenv-hf-a10g-qwen-rich/loss_history.json`](./artifacts/trl-openenv-hf-a10g-qwen-rich/loss_history.json) |
| Reward checkpoint CSV | [`artifacts/trl-openenv-hf-a10g-qwen-rich/reward_eval_history.csv`](./artifacts/trl-openenv-hf-a10g-qwen-rich/reward_eval_history.csv) |
| HF job log | [`artifacts/trl-openenv-hf-a10g-qwen-rich/hf_job_api.log`](./artifacts/trl-openenv-hf-a10g-qwen-rich/hf_job_api.log) |
| Training summary | [`artifacts/trl-openenv-hf-a10g-qwen-rich/analysis_summary.md`](./artifacts/trl-openenv-hf-a10g-qwen-rich/analysis_summary.md) |
| Showcase dashboard | [`artifacts/trl-openenv-hf-a10g-qwen-rich/showcase_dashboard.html`](./artifacts/trl-openenv-hf-a10g-qwen-rich/showcase_dashboard.html) |
| LoRA adapter | [`artifacts/trl-openenv-hf-a10g-qwen-rich/final_model/`](./artifacts/trl-openenv-hf-a10g-qwen-rich/final_model/) |

| Policy | Eval cases | Mean score | Mean total reward | Control satisfied | Certificate mean | Parse success | Unsafe release |
|---|---:|---:|---:|---:|---:|---:|---:|
| Random baseline | 9 | 0.1088 | 0.0888 | 0.0000 | 0.4461 | 1.0000 | 0.0000 |
| Naive PAY baseline | 9 | 0.0693 | 0.0493 | 0.2222 | 0.4794 | 1.0000 | 0.0000 |
| Base Qwen model | 9 | 0.1283 | -1.4473 | 0.0000 | 0.4044 | 1.0000 | 0.0000 |
| Trained Qwen LoRA | 9 | 0.4394 | -3.1019 | 0.2222 | 0.8478 | 1.0000 | 0.0000 |
| Teacher policy | 9 | 0.6627 | -2.7090 | 0.5556 | 0.9472 | 1.0000 | 0.0000 |

The trained Qwen LoRA improved held-out mean score by `+0.3111` over the base Qwen model and `+0.3306` over the random baseline. Mean total reward includes tool costs and step penalties, so the headline learning signal here is the environment final score, control satisfaction, parse success, certificate score, and unsafe-release rate.

Reward checkpoints during training used a fixed 3-case held-out subset:

| Training step | Mean score | Mean total reward | Parse success | Unsafe release |
|---:|---:|---:|---:|---:|
| 300 | 0.3599 | -2.8615 | 1.0000 | 0.0000 |
| 600 | 0.5090 | -3.0566 | 1.0000 | 0.0000 |
| 900 | 0.4743 | -3.0913 | 1.0000 | 0.0000 |

![Training loss](./artifacts/trl-openenv-hf-a10g-qwen-rich/plots/training_loss.png)
Caption: TRL SFT loss over 900 optimizer steps, showing the model fitting executable LedgerShield action plans.

![Reward during training](./artifacts/trl-openenv-hf-a10g-qwen-rich/plots/checkpoint_reward_curve.png)
Caption: Held-out environment score and parse success measured during training at steps 300, 600, and 900.

![Reward improvement ladder](./artifacts/trl-openenv-hf-a10g-qwen-rich/plots/reward_improvement_ladder.png)
Caption: Random, naive, base Qwen, trained Qwen, and teacher policy scores on the same axis.

![Mean reward by policy](./artifacts/trl-openenv-hf-a10g-qwen-rich/plots/mean_reward_by_policy.png)
Caption: Final held-out environment score comparison after training.

![Per-case scores by policy](./artifacts/trl-openenv-hf-a10g-qwen-rich/plots/per_case_scores_by_policy.png)
Caption: Case-level held-out scores reveal where training helped and where teacher-level behavior is still missing.

![Safety and parse metrics](./artifacts/trl-openenv-hf-a10g-qwen-rich/plots/safety_and_parse_metrics.png)
Caption: Parse success and unsafe-release rate confirm the trained policy remains executable and safe on the held-out split.

![Certificate score by policy](./artifacts/trl-openenv-hf-a10g-qwen-rich/plots/certificate_score_by_policy.png)
Caption: Certificate/audit quality improved materially after training.

![Result class distribution](./artifacts/trl-openenv-hf-a10g-qwen-rich/plots/result_class_distribution.png)
Caption: Result classes show how behavior changed qualitatively, not just numerically.

Full plot pack: [`artifacts/trl-openenv-hf-a10g-qwen-rich/plots/`](./artifacts/trl-openenv-hf-a10g-qwen-rich/plots/)

### Exquisite Training Layer: Environment-in-the-Loop Self-Improvement

The original LedgerShield training proof is preserved under:

`artifacts/trl-openenv-hf-a10g-qwen-rich/`

That run demonstrated live OpenEnv-connected SFT on LedgerShield trajectories.

The new Exquisite Training Layer adds a second post-training stage:

1. Start from the existing SFT LoRA checkpoint.
2. Generate multiple candidate AP-control action plans per case.
3. Execute every candidate inside the LedgerShield environment.
4. Score each candidate with final score, certificate quality, control satisfaction, institutional utility, parse validity, and unsafe-release penalties.
5. Train with GRPO using environment rewards.
6. Build best-vs-worst falsifier preference pairs.
7. Optionally distill the strongest behavior into a final DPO adapter.
8. Produce a 40+ plot evidence pack with scaling laws, policy ladders, safety frontiers, falsifier analysis, and ablations.

This turns LedgerShield from a static benchmark into a self-improving enterprise-control training environment.

The Hugging Face launcher now also syncs the current local `training/`, `server/`, `docs/`, and top-level runtime files into the Space repo before starting jobs, and it uses budget-aware per-run hardware and timeout caps by default, so the cloud runs execute the same Exquisite code and docs that exist in this workspace rather than an older Space snapshot.

See:

- [`docs/exquisite-training-layer.md`](./docs/exquisite-training-layer.md)
- [`docs/exquisite-visual-analysis.md`](./docs/exquisite-visual-analysis.md)
- [`training/exquisite/`](./training/exquisite/)
- [`artifacts/exquisite-training/reports/exquisite_training_report.md`](./artifacts/exquisite-training/reports/exquisite_training_report.md)
- [`artifacts/exquisite-training/plots/`](./artifacts/exquisite-training/plots/)
- [`artifacts/exquisite-training/dashboard/index.html`](./artifacts/exquisite-training/dashboard/index.html)

Operationally, the Exquisite layer now has separate scripts for:

- launching the HF run matrix: `training/exquisite/launch_exquisite_jobs.py`
- monitoring existing HF jobs without relaunching: `training/exquisite/monitor_exquisite_jobs.py`
- rebuilding the judge-facing markdown report from current artifacts: `training/exquisite/render_exquisite_report.py`

## Documentation

All long-form documentation now lives in a single consolidated file: [`docs/DOCUMENTATION.md`](./docs/DOCUMENTATION.md). Jump to a section via anchor:

| Section | What it covers |
|---|---|
| [Training Evidence Report](./docs/training-report.md) | real OpenEnv-connected TRL run, reward curves, baseline comparison, plots, and grading alignment |
| [HF Mini-Blog Final](./docs/HF_MINIBLOG_FINAL.md) | short public-facing writeup for HF/community readers |
| [Documentation Hub](./docs/DOCUMENTATION.md#documentation-hub) | docs landing page and reading paths |
| [Documentation Index](./docs/DOCUMENTATION.md#documentation-index) | benchmark overview, quick start, and core concepts |
| [Tasks](./docs/DOCUMENTATION.md#tasks) | task families, outputs, scoring, and case catalog |
| [API Reference](./docs/DOCUMENTATION.md#api-reference) | REST endpoints, payloads, response envelopes, and action contracts |
| [Architecture](./docs/DOCUMENTATION.md#architecture) | system design, hidden state, reward flow, grading, and evaluation pipeline |
| [Development](./docs/DOCUMENTATION.md#development) | setup, tests, CI, and detailed repo/file map |
| [Deployment](./docs/DOCUMENTATION.md#deployment) | local, Docker, HF Space, and environment configuration guidance |
| [ASHTG Theory](./docs/DOCUMENTATION.md#ashtg-theory) | **30-citation ASHTG theoretical framework** — SPRT, VoI, Proper Scoring, SCM, Stackelberg, Reward Machines, Categorical MDP |

Recommended reading paths:

- First-time reader or reviewer: [Training Evidence Report](./docs/training-report.md) -> [Documentation Index](./docs/DOCUMENTATION.md#documentation-index) -> [Architecture](./docs/DOCUMENTATION.md#architecture)
- Agent builder: [Tasks](./docs/DOCUMENTATION.md#tasks) -> [API Reference](./docs/DOCUMENTATION.md#api-reference) -> [Development](./docs/DOCUMENTATION.md#development)
- Contributor: [Development](./docs/DOCUMENTATION.md#development) -> [Architecture](./docs/DOCUMENTATION.md#architecture)
- Operator: [Deployment](./docs/DOCUMENTATION.md#deployment) -> [API Reference](./docs/DOCUMENTATION.md#api-reference)

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
| `server/case_factory.py` | challenge, holdout, benign-twin, and ControlBench AP-quarter generation |
| `server/decision_falsifier.py` | deterministic adversarial decision review for unsupported/unsafe terminal actions |
| `server/trust_graph.py` | compact TrustGraph projection over case, invoice, vendor, evidence, policy, certificate, authority, and loss-surface nodes |
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
| `benchmark_report.py` | public benchmark + holdout + contrastive + ControlBench + certificate-required + two-agent reporting |
| `compare_models_live.py` | live multi-model evaluation with capability profiles and debug artifacts |
| `sync_benchmark_metadata.py` | refreshes README/docs/openenv metadata from the current artifacts and runtime defaults |
| `inference.py` | submission-safe agent with ModelCapabilityProfile tiers and evidence-grounded output |
| `training/ledgershield_trl_training.py` | OpenEnv-connected TRL SFT collection, training, evaluation, and plot generation |
| `inference_improved.py` | experimental improved agent entrypoint |
| `inference_llm_powered.py` | richer LLM-powered agent used for debugging and comparisons |
| `task_c_guardrails.py` / `task_d_guardrails.py` | grounded output sanitizers with composite signal detection and PAY evidence construction |
| `llm_utils.py` | JSON parsing and completion helpers for LLM workflows |
| `llm_judge_grader.py` | optional LLM-as-judge grading experiments |
| `models.py` | shared dataclasses and Pydantic reward model |
| `.github/workflows/ci.yml` | pytest, Docker build, and metadata validation in CI |

For the full file-by-file map, see the [Development section](./docs/DOCUMENTATION.md#development).

## Implementation Status

- Core environment upgrades from Phases 1 through 5 are implemented in code.
- Patch-level fixes applied: correct `DEGENERATE_EVIDENCE_CAP` in grading, composite bank-override signal, domain-alignment token overlap, constructive PAY evidence in guardrails.
- The agent (`inference.py`) uses `ModelCapabilityProfile` tiers (elite/strong/standard) that adapt planning mode, repair level, and budget bonuses.
- `compare_models_live.py` records per-model capability profiles and includes monotonic strength ordering checks.
- The repo includes 21 curated benchmark cases with audited track assignment and latent-mechanism metadata, plus generated challenge and holdout tooling.
- CI runs via GitHub Actions with pytest configuration in `pyproject.toml`.
- The test suite covers API smoke, grading, environment, inference, inference-runtime, compliance, currency, curriculum, and guardrails.
- ControlBench is implemented end to end: seeded institutional sequences, loss surface, calibration gate, sleeper-vendor states, report output, API summary, and focused tests.
- Trust hardening is implemented end to end: Certificate-Required track, deterministic adversarial falsifier diagnostics, statechart-style control boundary enforcement, persistent TrustGraph projection, and two-agent control-profile report.
- The environment remains submission-compatible through `inference.py`.
- Latest finalization pass:
  - All 8 frozen artifacts regenerated with an expanded portfolio (5 sequences, up from 2).
  - All 21 cases audited with `primary_track`, `official_tracks`, and `latent_mechanism` fields.
  - Server endpoints validated: `/health`, `/leaderboard`, and `/benchmark-report` return correct JSON.
  - OpenEnv-connected TRL SFT runner and Colab notebook added under `training/`, with live trajectory collection and PNG reward/loss plots.
  - Rich-field A10G Qwen run completed and documented in [`docs/training-report.md`](./docs/training-report.md), with 45 live rollouts, 900 optimizer steps, baseline comparisons, and reward checkpoints.

## Safety Note

LedgerShield is a benchmark and simulation environment. It models payment-integrity risk and enterprise controls, but it is not a production fraud platform and should not be used to approve or block real payments without independent controls, audit, and governance.
