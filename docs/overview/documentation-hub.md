---
title: "Documentation Hub"
description: "Reading paths, code landmarks, and how the docs map to the LedgerShield ControlBench codebase."
icon: "book-open"
sidebarTitle: "Hub"
---

> Source: `docs/README.md` (consolidated)

This document contains the long-form documentation for LedgerShield ControlBench. The root [`README.md`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/README.md) is the project overview, quick-start guide, and entry point; the sections below go deeper into benchmark design, task contracts, APIs, architecture, development workflow, deployment, ControlBench institutional-control evaluation, proof-gated certificates, TrustGraph projection, and deterministic decision falsification.

---

## Where to Start

**If you are new here**, read the root [`README.md`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/README.md) first, then follow the reading path below that matches your role.

---

## Reading Paths

### Evaluating the benchmark (reviewer, researcher)

1. [`README.md`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/README.md) — project overview, benchmark at a glance, upgrade snapshot
2. [`index.md`](/overview/documentation-index) — why LedgerShield exists, core concepts, scoring philosophy
3. [`tasks.md`](/benchmark/tasks) — task families, case catalog, output contracts, scoring dimensions
4. [`architecture.md`](/architecture/overview) — system layers, hidden state, reward flow, grading pipeline

### Building an agent

1. [`index.md`](/overview/documentation-index) — core concepts and episode lifecycle
2. [`tasks.md`](/benchmark/tasks) — what the agent must output and how it is graded
3. [`api-reference.md`](/api-reference) — REST endpoints, payloads, action contracts
4. [`development.md`](/guides/development) — repo map and extension guidance

### Contributing to the codebase

1. [`development.md`](/guides/development) — setup, tests, CI, and repo map
2. [`architecture.md`](/architecture/overview) — system design and grading pipeline
3. [`api-reference.md`](/api-reference) — payload schemas you must keep in sync
4. [`tasks.md`](/benchmark/tasks) — scoring dimensions affected by code changes

### Operating or deploying LedgerShield

1. [`deployment.md`](/guides/deployment) — local, Docker, HF Space, and runtime configuration
2. [`api-reference.md`](/api-reference) — endpoints and health checks
3. [`index.md`](/overview/documentation-index) — benchmark scope and case loading

---

## Documentation Map

| File | Best for | Contents |
|---|---|---|
| [`index.md`](/overview/documentation-index) | first-time readers | motivation, benchmark scope, core concepts, quick start, and evaluation framing |
| [`tasks.md`](/benchmark/tasks) | agent builders and benchmark users | task families A–E, case catalog, output contracts by task, scoring weights, and penalties |
| [`api-reference.md`](/api-reference) | integrators and agent builders | REST endpoints (`/reset`, `/step`, `/state`, `/leaderboard`, `/benchmark-report`, `/controlbench-summary`, `/human-baseline-summary`, `/institutional-memory`, `/institutional-reset`), request/response envelopes, action taxonomy, reward model |
| [`architecture.md`](/architecture/overview) | researchers and maintainers | system layers, hidden-state mechanics, reward design, grading pipeline, case generation, realism modules |
| [`development.md`](/guides/development) | contributors | local setup, test suite, CI expectations, detailed repo/file map, extension guidance |
| [`deployment.md`](/guides/deployment) | operators | local/Docker/HF deployment, environment variables, deployment profiles, troubleshooting |

---

## How The Docs Relate to Code

| Doc section | Primary code files it documents |
|---|---|
| **Investigation tools** (`index.md`, `api-reference.md`) | `server/tools.py` — tool implementations, email thread parsing, domain alignment |
| **Grading and penalties** (`tasks.md`, `architecture.md`) | `server/grading.py`, `server/trajectory_grading.py`, `server/risk_rules.py`, `server/outcome_simulator.py`, `server/decision_certificate.py`, `server/institutional_game.py` |
| **Agent behavior and tiering** (`README.md`, `development.md`) | `inference.py` — `ModelCapabilityProfile`, evidence grounding, guardrail pipelines |
| **Guardrail sanitization** (`development.md`, `tasks.md`) | `task_c_guardrails.py`, `task_d_guardrails.py` — composite signals, PAY evidence, sanitize logic |
| **Environment loop** (`architecture.md`) | `server/environment.py` — reward shaping, PBRS, truncation, rendering, institutional memory updates, certificate verification |
| **State and pressure** (`architecture.md`) | `server/world_state.py`, `server/pressure_events.py` |
| **Case generation** (`architecture.md`) | `server/case_factory.py`, `server/attack_library.py`, `server/data_loader.py` — challenge, procedural holdout ecosystems, twins, ControlBench AP-quarter sequences, and certificate-required clones |
| **Benchmark evaluation** (`README.md`) | `benchmark_report.py`, `compare_models_live.py` — public/holdout/contrastive/ControlBench/sleeper/blind/certificate-required/human-baseline reports and live comparison with capability profiles |

---

## Code Landmarks

| Path | Why you would open it |
|---|---|
| [`../server/environment.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/environment.py) | reward shaping, truncation semantics, rendering, tool dispatch |
| [`../server/world_state.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/world_state.py) | hidden/public state, artifacts, pressure events, decision readiness |
| [`../server/grading.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/grading.py) | task rubrics, degenerate evidence cap, semantic counterfactual scoring |
| [`../server/decision_certificate.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/decision_certificate.py) | Decision Certificate Graph construction and verification |
| [`../server/decision_falsifier.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/decision_falsifier.py) | deterministic adversarial review of terminal decisions |
| [`../server/trust_graph.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/trust_graph.py) | compact TrustGraph projection for payment decisions |
| [`../server/institutional_game.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/institutional_game.py) | persistent AP-week memory, institutional loss surface, calibration gate, and sleeper-vendor state |
| [`../server/trajectory_grading.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/trajectory_grading.py) | trajectory-aware scoring and efficiency logic |
| [`../server/tools.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/tools.py) | investigation tools, email-thread payload construction, domain alignment |
| [`../server/case_factory.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/case_factory.py) | generated challenge/holdout/twin cases and ControlBench AP-quarter sequences |
| [`../server/attack_library.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/attack_library.py) | adversarial attack inventory (16 types) |
| [`../server/currency_engine.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/currency_engine.py) | multi-currency realism (FX, IBAN, SWIFT, aging) |
| [`../server/compliance_engine.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/compliance_engine.py) | SOX-style control evaluation |
| [`../server/curriculum.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/curriculum.py) | dynamic difficulty adaptation |
| [`../server/dual_agent_mode.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/server/dual_agent_mode.py) | watchdog-mode novelty module |
| [`../inference.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/inference.py) | submission-safe agent with `ModelCapabilityProfile` tiers |
| [`../task_c_guardrails.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/task_c_guardrails.py) | Task C composite signal detection and PAY evidence |
| [`../task_d_guardrails.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/task_d_guardrails.py) | Task D composite signal detection and PAY evidence |
| [`../benchmark_report.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/benchmark_report.py) | benchmark report, ControlBench sequence report, sleeper/blind/generated-holdout summaries, certificate-required report, human-baseline summary, two-agent demo, and leaderboard generation |
| [`../compare_models_live.py`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/compare_models_live.py) | live multi-model comparison with capability profiles, certificate metrics, and institutional-loss metrics |

---

## Practical Advice

- **Quick benchmark contract?** Start with [`tasks.md`](/benchmark/tasks).
- **Agent failing a case?** Pair [`tasks.md`](/benchmark/tasks) with the trace artifacts in `live_model_comparison_debug/`.
- **Changing scoring?** Read [`architecture.md`](/architecture/overview) and then [`development.md`](/guides/development).
- **Changing endpoints or payloads?** Keep [`api-reference.md`](/api-reference) in sync.
- **Adding a new tool or intervention?** Update `server/tools.py`, `server/schema.py`, `server/environment.py`, and then [`api-reference.md`](/api-reference) + [`architecture.md`](/architecture/overview).
- **Understanding agent tiering?** See `inference.py` → `ModelCapabilityProfile` and the Upgrade Snapshot in the root [`README.md`](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/README.md).

---
