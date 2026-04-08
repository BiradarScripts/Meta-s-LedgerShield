# LedgerShield Documentation

This folder contains the long-form documentation for LedgerShield. The root [`README.md`](../README.md) is the project pitch and quick orientation guide; the files here go deeper into benchmark design, task contracts, APIs, architecture, development workflow, and deployment.

## Reading Paths

### If you are evaluating the benchmark

1. [`../README.md`](../README.md)
2. [`index.md`](./index.md)
3. [`tasks.md`](./tasks.md)
4. [`architecture.md`](./architecture.md)

### If you are building an agent

1. [`index.md`](./index.md)
2. [`tasks.md`](./tasks.md)
3. [`api-reference.md`](./api-reference.md)
4. [`development.md`](./development.md)

### If you are contributing to the codebase

1. [`development.md`](./development.md)
2. [`architecture.md`](./architecture.md)
3. [`api-reference.md`](./api-reference.md)
4. [`tasks.md`](./tasks.md)

### If you are operating or packaging LedgerShield

1. [`deployment.md`](./deployment.md)
2. [`api-reference.md`](./api-reference.md)
3. [`index.md`](./index.md)

## Documentation Map

| File | Best for | Contents |
|---|---|---|
| [`index.md`](./index.md) | first-time readers | motivation, benchmark scope, core concepts, quick start, and evaluation framing |
| [`tasks.md`](./tasks.md) | agent builders and benchmark users | task families, case catalog, output contracts, and scoring dimensions |
| [`api-reference.md`](./api-reference.md) | integrators | endpoints, request/response formats, action taxonomy, and payload examples |
| [`architecture.md`](./architecture.md) | researchers and maintainers | system layers, hidden state, reward flow, grading pipeline, and variant generation |
| [`development.md`](./development.md) | contributors | setup, tests, CI, repo map, and extension guidance |
| [`deployment.md`](./deployment.md) | operators | local/Docker/HF deployment, runtime env vars, and operational checks |

## How The Docs Fit Together

- [`../README.md`](../README.md) explains why LedgerShield exists and why it is interesting.
- [`index.md`](./index.md) explains what the benchmark measures.
- [`tasks.md`](./tasks.md) explains what a strong agent must output and how it is graded.
- [`api-reference.md`](./api-reference.md) explains how agents talk to the environment.
- [`architecture.md`](./architecture.md) explains how the server, state model, grader, and generators work.
- [`development.md`](./development.md) explains how to work safely inside the repo.
- [`deployment.md`](./deployment.md) explains how to run LedgerShield outside a local dev shell.

## Code Landmarks

| Path | Why you would open it |
|---|---|
| [`../server/environment.py`](../server/environment.py) | reward shaping, truncation semantics, rendering, tool dispatch |
| [`../server/world_state.py`](../server/world_state.py) | hidden/public state, artifacts, pressure events, decision readiness |
| [`../server/grading.py`](../server/grading.py) | task rubrics and penalties |
| [`../server/trajectory_grading.py`](../server/trajectory_grading.py) | trajectory-aware scoring and efficiency logic |
| [`../server/case_factory.py`](../server/case_factory.py) | generated challenge/holdout/twin cases |
| [`../server/attack_library.py`](../server/attack_library.py) | adversarial attack inventory |
| [`../server/currency_engine.py`](../server/currency_engine.py) | multi-currency realism hooks |
| [`../server/compliance_engine.py`](../server/compliance_engine.py) | SOX-style control evaluation |
| [`../server/curriculum.py`](../server/curriculum.py) | dynamic difficulty adaptation |
| [`../server/dual_agent_mode.py`](../server/dual_agent_mode.py) | watchdog-mode novelty module |
| [`../inference.py`](../inference.py) | submission-safe agent |
| [`../benchmark_report.py`](../benchmark_report.py) | benchmark report and leaderboard generation |

## Practical Advice

- If you need the benchmark contract quickly, start with [`tasks.md`](./tasks.md).
- If a model is failing a case, pair [`tasks.md`](./tasks.md) with the trace artifacts in `live_model_comparison_debug/`.
- If you are changing scoring, read [`architecture.md`](./architecture.md) and then [`development.md`](./development.md).
- If you are changing endpoints or payloads, keep [`api-reference.md`](./api-reference.md) in sync.
