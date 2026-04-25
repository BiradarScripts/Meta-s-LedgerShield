# LedgerShield — Exhaustive Technical Deep-Dive (Updated)

> Reading Time: ~50 minutes | Inspection Date: 2026-04-25 | Scope: current repo + last 4 commits (`df53a65` → `bf345c6`)

## Table of Contents

1. What Is This Project?
2. What Changed In The Last 4 Commits?
3. Updated Root-Level File Map
4. Updated Server Package Deep Dive
5. Fixtures, Data, and Generated Ecosystems
6. Tests, Validation, and CI/CD
7. End-to-End Runtime Flow
8. Tech Stack and Formal Methods
9. Summary

---

## 1. What Is This Project?

### 1.1 — One-Sentence Summary

LedgerShield is now best described as a **ControlBench-style AP fraud benchmark**: a partially observable enterprise accounts-payable simulation where an AI agent must investigate invoices, vendor identity, bank-account changes, duplicate-payment risk, workflow overrides, and campaign-level fraud while also maintaining institutional safety over long-horizon sequences.

### 1.2 — The Domain

The domain is still enterprise payment integrity, but the benchmark has clearly evolved beyond single-case invoice fraud scoring. The current repo evaluates whether an agent can:

- investigate payment requests under partial information;
- apply AP controls like callback verification, duplicate review, and approval-chain validation;
- tolerate adversarial pressure and prompt-injection-style workflow overrides;
- produce grounded, proof-carrying decisions;
- operate safely across long institutional sequences with memory, capacity limits, and authority restrictions.

That means the benchmark now measures not just **case correctness**, but also **institutional deployability**.

### 1.3 — Updated Architecture Framing

The original POMDP + ASHTG framing is still correct, but it is now layered with a stronger ControlBench envelope:

```text
POMDP investigation loop
  + SPRT belief updates
  + VoI-based action ranking
  + Reward-machine milestone shaping
  + SCM / causal grading
  + Stackelberg watchdog auditing
  + Decision Certificate verification
  + Institutional memory + loss surface
  + Calibration-gated authority
  + Sleeper-vendor vigilance
  + TrustGraph + deterministic falsifier
  + FraudGen generated ecosystems
  + Certify + visualization product/report APIs
```

### 1.4 — Core Design Pillars

#### POMDP Environment
The agent still cannot directly observe hidden fraud state, hidden risk signals, pending artifact outcomes, or latent mechanism metadata. It must reveal these with tools and interventions.

#### SPRT + VoI
`server/sprt_engine.py` and `server/voi_engine.py` still drive sequential evidence accumulation and optimal next-action ranking.

#### Reward Machine
Task-specific milestone progression still exists via `server/reward_machine.py`, but it now sits inside a richer environment that also emits institutional metrics and control diagnostics.

#### Dual-Agent Watchdog
The embedded watchdog auditor still models separation-of-duties and can warn, escalate, or veto unsafe analyst behavior.

#### Causal + Proof-Carrying Evaluation
The project still uses SCM-based counterfactual reasoning and typed `decision_certificate` graphs, but recent changes make certificates part of a stricter deployment story rather than just a scoring bonus.

#### Institutional Control Intelligence
This is the major evolution. The system now tracks a **10-dimensional institutional loss surface**, authority downgrades, sleeper-vendor activation/detection, and sequence-level deployability ratings.

### 1.5 — Task Families

The five task families remain the same:

| Task | Description | Typical focus |
| --- | --- | --- |
| Task A | OCR-based invoice field extraction | structured document extraction |
| Task B | Three-way match verification | PO/receipt/policy discrepancies |
| Task C | Duplicate + bank-account triage | duplicate fraud, bank mismatch, threshold evasion |
| Task D | Full AP inbox fraud investigation | email/vendor/bank/callback synthesis |
| Task E | Campaign-level fraud reasoning | coordinated fraud, supply-chain compromise |

What changed is the **benchmark wrapper around them**: the same tasks are now used across extra tracks like generated holdouts, ControlBench sequences, sleeper vigilance, blind-control, and certificate-required evaluation.

### 1.6 — Final Decision Space

The final decision set is unchanged:

- `PAY`
- `HOLD`
- `NEEDS_REVIEW`
- `ESCALATE_FRAUD`

What is new is that a decision can now also be judged through:

- authority gating,
- deterministic falsification,
- TrustGraph support structure,
- certificate-required scoring,
- institutional loss consequences over time.

### 1.7 — Reward Signal

The environment still combines PBRS, VoI, reward-machine progress, milestone bonuses, and final submission score, but current code also surfaces run-level institutional metrics that affect long-horizon evaluation and deployability narratives.

---

## 2. What Changed In The Last 4 Commits?

The last four commits materially changed the benchmark surface.

| SHA | Commit | Main impact |
| --- | --- | --- |
| `bf345c6` | Complete ControlBench experiments and Certify APIs | added Certify endpoints, visualization payloads, experiment-suite outputs |
| `f9a0b40` | Harden ControlBench authority and sleeper demos | stronger authority gating, sleeper-vendor logic, demo/report hardening |
| `c8397ff` | Implement ControlBench fraudgen and proof hardening | added `fraudgen.py`, solvability manifests, proof/report hardening |
| `df53a65` | v12 | baseline ControlBench checkpoint for this latest report window |

### 2.1 — Big Conceptual Shift

The repo is no longer just documenting a fraud-investigation benchmark. It is documenting a **benchmark + certification + visualization stack** for evaluating whether an agent is deployable inside AP workflows.

### 2.2 — New Major Modules

The last 4 commits introduced these new first-class modules:

- `server/fraudgen.py`
- `server/certify.py`
- `server/visualization.py`

Together they add:

- generated fraud taxonomy and solvability manifests;
- product-facing certification summaries;
- graph-ready ControlBench visualization payloads.

### 2.3 — Institutional Memory Expanded

`server/institutional_game.py` now tracks a richer institutional ledger. The important change is that the old simpler loss ledger has become an auditable **loss surface** with ratios and deployability consequences.

Current loss surface dimensions include:

- fraud loss released;
- fraud loss prevented;
- false-positive cost;
- operational delay;
- manual-review burn;
- supplier friction;
- calibration debt;
- vigilance loss;
- authority restriction rate;
- catastrophic event rate.

### 2.4 — Authority Hardening

Authority is now explicitly calibration-gated. The public institutional state can expose:

- `full_authority`
- `restricted_authority`
- `review_only`
- `locked`

This means poor calibration or catastrophic control failures are no longer just score penalties; they can **reduce what the agent is allowed to do in later sequence steps**.

### 2.5 — Sleeper-Vendor Expansion

Sleeper-vendor behavior is now modeled more explicitly through warmup, trust-building, activation, and detection states. This lets the benchmark test whether an agent over-trusts previously clean vendors.

### 2.6 — FraudGen Holdouts And Independent Ecosystems

`server/fraudgen.py` and updated `server/case_factory.py` now support:

- scenario typing such as `sleeper_activation`, `campaign_fraud`, `duplicate_invoice`, `three_way_match_conflict`, and `prompt_injection_fraud`;
- difficulty banding;
- solvability manifests describing required tools, recommended interventions, revealable artifacts, and minimum evidence hops;
- independent generated AP ecosystems that do not depend on curated-case sampling.

This is a major benchmark-quality improvement because it strengthens anti-overfitting claims.

### 2.7 — New Public APIs

The server now exposes more than the classic environment endpoints. New important endpoints include:

- `POST /certify`
- `GET /certify-summary`
- `GET /controlbench-visualization`

These sit alongside:

- `GET /leaderboard`
- `GET /benchmark-report`
- `GET /controlbench-summary`
- `GET /human-baseline-summary`
- `GET /institutional-memory`
- `POST /institutional-reset`

### 2.8 — Reporting And Experiments Expanded

`benchmark_report.py` now includes more than benchmark means. It also supports or emits:

- `controlbench_quarter`
- `generated_holdout_track`
- `blind_control_track`
- `sleeper_vigilance_track`
- `certificate_required_track`
- `human_baseline_track`
- `controlbench_two_agent_demo`
- `controlbench_visualization`
- experiment-suite outputs
- FraudGen summaries across holdout/controlbench/generated ecosystems

### 2.9 — Test Surface Expanded

Recent additions also strengthened validation:

- API smoke coverage for `/certify` and `/controlbench-visualization`
- stronger `test_controlbench.py` coverage for authority gates, prompt-injection boundaries, and independent FraudGen solvability
- broader benchmark report assertions for FraudGen and visualization outputs

---

## 3. Updated Root-Level File Map

### 3.1 — Key Root Files

| File | Purpose |
| --- | --- |
| `__init__.py` | package export surface |
| `models.py` | core dataclasses / observation / action / state models |
| `client.py` | HTTP client wrapper |
| `ledgershield_env.py` | compatibility re-export shim |
| `openenv_compat.py` | OpenEnv compatibility + lazy FastAPI fallback |
| `inference.py` | submission-safe main baseline agent |
| `inference_llm_powered.py` | LLM-first comparison agent |
| `inference_improved.py` | experimental stronger agent path |
| `benchmark_report.py` | benchmark, ControlBench, holdout, and experiment reporting |
| `compare_models_live.py` | live model sweeps |
| `compare_all_models.py` | broader model comparison harness |
| `sync_benchmark_metadata.py` | syncs README/docs/OpenEnv metadata |
| `llm_utils.py` | JSON-parsing and chat wrapper utilities |
| `task_c_guardrails.py` | Task C validation / grounding |
| `task_d_guardrails.py` | Task D validation / grounding |
| `openenv.yaml` | benchmark metadata contract |
| `pyproject.toml` | package metadata and pytest config |
| `requirements.txt` | pinned runtime dependencies |
| `Dockerfile` | deployment image |
| `validate-submission.sh` | submission smoke/contract validator |

### 3.2 — Important Change In Root Reporting Surface

The root reporting stack now serves three different audiences:

1. **benchmark users** via `benchmark_report.py`;
2. **model comparison users** via `compare_models_live.py`;
3. **deployment/certification readers** via `server/certify.py` and `server/visualization.py` through the FastAPI layer.

That is a meaningful evolution from the earlier “single benchmark report generator” framing.

---

## 4. Updated Server Package Deep Dive

The current `server/` directory contains **43 entries** including fixtures and package metadata, with substantially more surface area than the older 34-file summary.

### 4.1 — `server/app.py`

This file is no longer just a minimal FastAPI wrapper. It now:

- constructs the environment via `build_app()`;
- loads the latest benchmark report artifact when present;
- exposes benchmark/report endpoints;
- exposes product/reporting endpoints for certification and visualization.

Key routes:

- `/`
- `/health`
- `/reset`
- `/step`
- `/state`
- `/leaderboard`
- `/benchmark-report`
- `/certify`
- `/certify-summary`
- `/controlbench-visualization`
- `/controlbench-summary`
- `/human-baseline-summary`
- `/institutional-memory`
- `/institutional-reset`

### 4.2 — `server/environment.py`

This remains the core environment loop, but the terminal submission branch now lives inside a much richer control stack. Beyond the classic grading path, terminal handling now interacts with:

- institutional memory updates;
- authority gating;
- decision certificates;
- deterministic falsifier diagnostics;
- TrustGraph projection;
- sequence-level portfolio metrics.

### 4.3 — `server/institutional_game.py`

This file changed materially.

#### Key current structures

- `VendorInstitutionalMemory`
- `InstitutionalLossLedger`
- `CalibrationGateState`
- `SleeperVendorState`
- `InstitutionalMemory`

#### Major current behaviors

- tracks loss-surface ratios, not just raw totals;
- computes normalized institutional loss score;
- exposes public `controlbench_summary`;
- tracks authority restrictions and catastrophic events;
- tracks sleeper-vendor activation and detection;
- exports authority policy derived from current authority level.

### 4.4 — `server/fraudgen.py` **(new)**

This is one of the most important additions from the last 4 commits.

Responsibilities:

- classify generated cases into scenario types;
- assign difficulty bands;
- build FraudGen manifests;
- derive solvability requirements;
- validate generated cases for non-trivial solvability;
- summarize FraudGen populations for reports.

Important outputs include:

- `scenario_type`
- `difficulty_band`
- `difficulty_signals`
- `attack_profile`
- `solvability_path`
- `validation`

This is what turns generated holdouts from “random variants” into **auditable synthetic benchmark instances**.

### 4.5 — `server/case_factory.py`

This file has grown beyond adversarial variants and benign twins. It now also supports:

- FraudGen-backed manifests attached into `generator_metadata`;
- solvability checks for generated cases;
- procedural holdouts;
- independent FraudGen ecosystem generation;
- ControlBench AP-quarter sequence generation.

### 4.6 — `server/certify.py` **(new)**

This new file builds product-facing certification summaries from benchmark reports or live institutional memory.

Core idea:

The repo can now explain not just *how well an agent scored*, but *what authority recommendation follows from that performance*.

Deployability outcomes currently include:

- `unsafe`
- `advisory`
- `review_required`
- `restricted_deployable`
- `deployable_with_audit`
- `high_trust`

The report includes:

- certification status;
- authority recommendation;
- control profile metrics;
- red-team plan;
- monitoring requirements;
- limitations.

### 4.7 — `server/visualization.py` **(new)**

This file builds graph-ready dashboard/demo payloads.

It prepares:

- accuracy vs institutional-loss profile points;
- authority timeline rows;
- compact loss-surface chart rows;
- certificate-gate comparison payloads;
- TrustGraph-health summaries;
- demo scripts and graph-layer descriptions.

This makes the benchmark more legible in demos and presentations without changing the core scoring logic.

### 4.8 — `server/trust_graph.py`, `server/decision_falsifier.py`, `server/control_statechart.py`

These modules were already part of the repo’s recent direction, and the last 4 commits lean on them harder.

- `trust_graph.py` projects terminal decisions into a compact graph over evidence, policy, authority, and loss nodes.
- `decision_falsifier.py` performs deterministic “murder-board” diagnostics over unsafe or unsupported decisions.
- `control_statechart.py` enforces runtime control boundaries, especially around prompt-injection-style premature PAY commits.

### 4.9 — `server/benchmark_contract.py`

The benchmark contract now matters more because reports and generated cases depend heavily on:

- official tracks;
- latent mechanism signatures;
- track labels;
- mechanism-family grouping.

### 4.10 — `server/tools.py`, `server/world_state.py`, `server/evidence_graph.py`

These remain core to the investigative experience, but they now operate inside a larger generated-case and TrustGraph-aware ecosystem.

Important current details:

- tools still reveal evidence and risk signals;
- world state now consumes FraudGen solvability metadata when present;
- evidence graphs still encode reveal logic, but generated-case validation now depends more on them.

---

## 5. Fixtures, Data, and Generated Ecosystems

### 5.1 — Fixture Directory

The current fixture directory is richer than the older summary. It now includes:

- `cases.json`
- `vendors.json`
- `vendor_history.json`
- `ledger_index.json`
- `email_threads.json`
- `po_records.json`
- `receipts.json`
- `policy_rules.json`

### 5.2 — Generated Data Story

The project is no longer limited to static fixtures plus challenge variants. It now supports three distinct data sources:

1. curated benchmark cases;
2. generated holdout/challenge variants;
3. independent FraudGen ecosystems.

That last category is especially important for evaluating generalization beyond memorized benchmark structure.

---

## 6. Tests, Validation, and CI/CD

### 6.1 — Test Coverage

The current test suite covers classic environment behavior plus ControlBench-specific logic.

Important files include:

- `tests/test_api_smoke.py`
- `tests/test_benchmark_report.py`
- `tests/test_controlbench.py`
- `tests/test_institutional_game.py`
- `tests/test_decision_certificate.py`
- `tests/test_compare_models_live.py`
- `tests/test_ledgershield_env.py`

### 6.2 — Newer Test Themes

Recent tests specifically verify:

- `/certify` returns authority recommendations;
- `/controlbench-visualization` returns graph-ready payloads;
- authority-gate failures downgrade decisions;
- prompt-injection boundaries force review outcomes;
- independent FraudGen ecosystems stay solvable without curated-case sampling;
- benchmark reports include FraudGen and visualization summaries.

### 6.3 — CI / Validation

The GitHub Actions workflow still runs test, docker-build, and validation jobs, but the validation surface is now larger because metadata sync and benchmark artifact generation must stay in step with ControlBench outputs.

---

## 7. End-to-End Runtime Flow

### Phase 0 — Boot

1. `server/app.py` builds the FastAPI app.
2. `LedgerShieldEnvironment` initializes loaders, curriculum, and institutional memory.
3. Optional benchmark artifacts are loaded lazily for leaderboard/report/certify/visualization endpoints.

### Phase 1 — Reset

1. A curated or generated case is selected.
2. Benchmark contract metadata is attached.
3. `world_state.build_hidden_world()` derives hidden signals, latent mechanism, evidence graph, policy, and intervention timing.
4. Institutional context is attached.
5. SPRT, reward machine, and watchdog state are initialized.
6. Public observation is returned.

### Phase 2 — Investigation Loop

1. The agent calls tools or interventions.
2. Results are normalized.
3. SPRT and observed-risk state update.
4. Budget and trajectory update.
5. Pending artifacts and pressure events advance.
6. Reward shaping is computed.
7. Next observation is returned.

### Phase 3 — Submission

1. A final decision is validated.
2. Predicted probabilities are normalized or implied.
3. Decision certificate is verified or synthesized.
4. Outcome simulation computes downstream consequences.
5. Compliance and task grading run.
6. Institutional memory updates loss surface, authority, and sleeper state.
7. Falsifier / TrustGraph / control-boundary diagnostics can affect the final evaluation story.
8. Terminal score and info payload are emitted.

### Phase 4 — Reporting / Certification / Visualization

After or alongside benchmark runs:

- `benchmark_report.py` builds benchmark/controlbench artifacts;
- `server/certify.py` can convert report or live memory into deployment guidance;
- `server/visualization.py` can convert report or memory into graph-ready payloads.

This is one of the clearest repo-level changes in the last 4 commits: reporting is now part of the product story, not just a research afterthought.

---

## 8. Tech Stack and Formal Methods

### 8.1 — Runtime Stack

- Python 3.11+
- FastAPI
- Uvicorn
- Pydantic
- Requests / HTTPX
- OpenAI SDK
- OpenEnv compatibility layer
- Docker
- pytest
- GitHub Actions

### 8.2 — Formal / Benchmark Foundations

- POMDP partial observability
- SPRT sequential hypothesis testing
- VoI action ranking
- Reward-machine temporal progress tracking
- SCM / causal reasoning
- proper scoring rules
- Stackelberg watchdog auditing
- categorical MDP composition
- RL state export
- institutional loss-surface evaluation

### 8.3 — Newer Benchmark-Specific Layers

- calibration-gated authority
- sleeper-vendor vigilance
- deterministic adversarial falsification
- TrustGraph projection
- FraudGen ecosystem generation
- Certify deployability reporting
- visualization payload generation

---

## 9. Summary

The older description of LedgerShield as “a POMDP fraud benchmark” is still directionally right, but it is no longer sufficient.

The current repo is more accurately a **long-horizon institutional-control benchmark and reporting platform** for AP fraud workflows.

The last 4 commits especially added or hardened:

- FraudGen scenario generation and solvability manifests;
- stronger authority gating and sleeper-vendor evaluation;
- product-facing Certify APIs;
- ControlBench visualization payloads;
- richer benchmark-report outputs and experiment surfaces.

In short: LedgerShield now evaluates not just whether an agent can solve a fraud case, but whether it can be **trusted, audited, visualized, and deployment-scoped** inside an enterprise payment-control setting.
