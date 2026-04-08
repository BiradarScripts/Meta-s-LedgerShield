# LedgerShield Documentation

This folder contains the long-form documentation for LedgerShield. The root [`README.md`](../README.md) is the project pitch, quick-start guide, and entry point; the files here go deeper into benchmark design, task contracts, APIs, architecture, development workflow, and deployment.

---

## Where to Start

**If you are new here**, read the root [`README.md`](../README.md) first, then follow the reading path below that matches your role.

---

## Reading Paths

### Evaluating the benchmark (judge, reviewer, researcher)

1. [`README.md`](../README.md) — project overview, benchmark at a glance, upgrade snapshot
2. [`index.md`](./index.md) — why LedgerShield exists, core concepts, scoring philosophy
3. [`tasks.md`](./tasks.md) — task families, case catalog, output contracts, scoring dimensions
4. [`architecture.md`](./architecture.md) — system layers, hidden state, reward flow, grading pipeline

### Building an agent

1. [`index.md`](./index.md) — core concepts and episode lifecycle
2. [`tasks.md`](./tasks.md) — what the agent must output and how it is graded
3. [`api-reference.md`](./api-reference.md) — REST endpoints, payloads, action contracts
4. [`development.md`](./development.md) — repo map and extension guidance

### Contributing to the codebase

1. [`development.md`](./development.md) — setup, tests, CI, and repo map
2. [`architecture.md`](./architecture.md) — system design and grading pipeline
3. [`api-reference.md`](./api-reference.md) — payload schemas you must keep in sync
4. [`tasks.md`](./tasks.md) — scoring dimensions affected by code changes

### Operating or deploying LedgerShield

1. [`deployment.md`](./deployment.md) — local, Docker, HF Space, and runtime configuration
2. [`api-reference.md`](./api-reference.md) — endpoints and health checks
3. [`index.md`](./index.md) — benchmark scope and case loading

---

## Documentation Map

| File | Best for | Contents |
|---|---|---|
| [`index.md`](./index.md) | first-time readers | motivation, benchmark scope, core concepts, quick start, and evaluation framing |
| [`tasks.md`](./tasks.md) | agent builders and benchmark users | task families A–E, case catalog, output contracts by task, scoring weights, and penalties |
| [`api-reference.md`](./api-reference.md) | integrators and agent builders | REST endpoints (`/reset`, `/step`, `/state`, `/leaderboard`, `/benchmark-report`), request/response envelopes, action taxonomy, reward model |
| [`architecture.md`](./architecture.md) | researchers and maintainers | system layers, hidden-state mechanics, reward design, grading pipeline, case generation, realism modules |
| [`development.md`](./development.md) | contributors | local setup, test suite, CI expectations, detailed repo/file map, extension guidance |
| [`deployment.md`](./deployment.md) | operators | local/Docker/HF deployment, environment variables, deployment profiles, troubleshooting |

---

## How The Docs Relate to Code

| Doc section | Primary code files it documents |
|---|---|
| **Investigation tools** (`index.md`, `api-reference.md`) | `server/tools.py` — tool implementations, email thread parsing, domain alignment |
| **Grading and penalties** (`tasks.md`, `architecture.md`) | `server/grading.py`, `server/trajectory_grading.py`, `server/risk_rules.py`, `server/outcome_simulator.py` |
| **Agent behavior and tiering** (`README.md`, `development.md`) | `inference.py` — `ModelCapabilityProfile`, evidence grounding, guardrail pipelines |
| **Guardrail sanitization** (`development.md`, `tasks.md`) | `task_c_guardrails.py`, `task_d_guardrails.py` — composite signals, PAY evidence, sanitize logic |
| **Environment loop** (`architecture.md`) | `server/environment.py` — reward shaping, PBRS, truncation, rendering |
| **State and pressure** (`architecture.md`) | `server/world_state.py`, `server/pressure_events.py` |
| **Case generation** (`architecture.md`) | `server/case_factory.py`, `server/attack_library.py`, `server/data_loader.py` |
| **Benchmark evaluation** (`README.md`) | `benchmark_report.py`, `compare_models_live.py` — live comparison with capability profiles |

---

## Code Landmarks

| Path | Why you would open it |
|---|---|
| [`../server/environment.py`](../server/environment.py) | reward shaping, truncation semantics, rendering, tool dispatch |
| [`../server/world_state.py`](../server/world_state.py) | hidden/public state, artifacts, pressure events, decision readiness |
| [`../server/grading.py`](../server/grading.py) | task rubrics, degenerate evidence cap, semantic counterfactual scoring |
| [`../server/trajectory_grading.py`](../server/trajectory_grading.py) | trajectory-aware scoring and efficiency logic |
| [`../server/tools.py`](../server/tools.py) | investigation tools, email-thread payload construction, domain alignment |
| [`../server/case_factory.py`](../server/case_factory.py) | generated challenge/holdout/twin cases |
| [`../server/attack_library.py`](../server/attack_library.py) | adversarial attack inventory (16 types) |
| [`../server/currency_engine.py`](../server/currency_engine.py) | multi-currency realism (FX, IBAN, SWIFT, aging) |
| [`../server/compliance_engine.py`](../server/compliance_engine.py) | SOX-style control evaluation |
| [`../server/curriculum.py`](../server/curriculum.py) | dynamic difficulty adaptation |
| [`../server/dual_agent_mode.py`](../server/dual_agent_mode.py) | watchdog-mode novelty module |
| [`../inference.py`](../inference.py) | submission-safe agent with `ModelCapabilityProfile` tiers |
| [`../task_c_guardrails.py`](../task_c_guardrails.py) | Task C composite signal detection and PAY evidence |
| [`../task_d_guardrails.py`](../task_d_guardrails.py) | Task D composite signal detection and PAY evidence |
| [`../benchmark_report.py`](../benchmark_report.py) | benchmark report and leaderboard generation |
| [`../compare_models_live.py`](../compare_models_live.py) | live multi-model comparison with capability profiles |

---

## Practical Advice

- **Quick benchmark contract?** Start with [`tasks.md`](./tasks.md).
- **Agent failing a case?** Pair [`tasks.md`](./tasks.md) with the trace artifacts in `live_model_comparison_debug/`.
- **Changing scoring?** Read [`architecture.md`](./architecture.md) and then [`development.md`](./development.md).
- **Changing endpoints or payloads?** Keep [`api-reference.md`](./api-reference.md) in sync.
- **Adding a new tool or intervention?** Update `server/tools.py`, `server/schema.py`, `server/environment.py`, and then [`api-reference.md`](./api-reference.md) + [`architecture.md`](./architecture.md).
- **Understanding agent tiering?** See `inference.py` → `ModelCapabilityProfile` and the Upgrade Snapshot in the root [`README.md`](../README.md).