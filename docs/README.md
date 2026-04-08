# LedgerShield Documentation

This directory contains the long-form documentation for LedgerShield. The root [`README.md`](../README.md) gives the big picture. This page is the documentation landing page for people who want a guided reading path through the rest of the repo.

## Documentation Map

Every markdown file in `docs/` is linked below with a clear purpose.

| Document | Best for | Contents |
|----------|----------|----------|
| [`index.md`](./index.md) | first-time readers | overview, benchmark motivation, core concepts, quick start, and API overview |
| [`tasks.md`](./tasks.md) | benchmark users and prompt engineers | task families, expected output formats, scoring breakdowns, benchmark cases, and strategy guidance |
| [`api-reference.md`](./api-reference.md) | anyone building a custom client | REST endpoints, payload shapes, response examples, and integration details |
| [`architecture.md`](./architecture.md) | contributors and researchers | environment design, state model, component graph, and data flow |
| [`development.md`](./development.md) | maintainers and contributors | setup, tests, project structure, and extension workflow |
| [`deployment.md`](./deployment.md) | operators | local, Docker, and production deployment patterns |

## Recommended Reading Paths

### If you are evaluating models

Start with:

1. [`index.md`](./index.md)
2. [`tasks.md`](./tasks.md)
3. [`api-reference.md`](./api-reference.md)

This sequence explains what the benchmark measures, what the agent is expected to output, and how to interact with the environment programmatically.

### If you are trying to improve benchmark performance

Start with:

1. [`tasks.md`](./tasks.md)
2. [`architecture.md`](./architecture.md)
3. [`development.md`](./development.md)

This path helps you understand the scoring levers, the hidden-state and artifact model, and where to make safe code changes.

### If you are deploying LedgerShield

Start with:

1. [`deployment.md`](./deployment.md)
2. [`api-reference.md`](./api-reference.md)
3. [`index.md`](./index.md)

### If you are new to the project

Start with:

1. [`../README.md`](../README.md)
2. [`index.md`](./index.md)
3. [`architecture.md`](./architecture.md)
4. [`tasks.md`](./tasks.md)

## How The Docs Fit Together

The documentation is intentionally layered:

- the root [`README.md`](../README.md) explains the benchmark at a project level
- [`index.md`](./index.md) is the conceptual onboarding guide
- [`tasks.md`](./tasks.md) translates those concepts into concrete benchmark expectations
- [`api-reference.md`](./api-reference.md) defines the environment contract
- [`architecture.md`](./architecture.md) explains how the server, state model, tools, and grader interact
- [`development.md`](./development.md) and [`deployment.md`](./deployment.md) cover implementation and operations

## Where To Look In The Code

The docs are most useful when paired with the main source files:

| Source file or directory | Why you would open it |
|--------------------------|-----------------------|
| [`../server/environment.py`](../server/environment.py) | understand the episode loop and action dispatch |
| [`../server/world_state.py`](../server/world_state.py) | inspect hidden risk, required actions, and artifact logic |
| [`../server/grading.py`](../server/grading.py) | understand task-specific scoring |
| [`../server/trajectory_grading.py`](../server/trajectory_grading.py) | understand investigation and intervention scoring |
| [`../inference.py`](../inference.py) | inspect the submission-safe agent |
| [`../inference_llm_powered.py`](../inference_llm_powered.py) | inspect the comparison/debug agent |
| [`../tests/`](../tests/) | verify contracts and regression coverage |

## Practical Navigation Tips

- If you only need the task contract, go straight to [`tasks.md`](./tasks.md).
- If your agent is failing a live comparison case, read the root [`README.md`](../README.md) first, then inspect the debug trace JSON files produced by the comparison scripts.
- If you are changing schemas or decisions, pair [`tasks.md`](./tasks.md) with [`api-reference.md`](./api-reference.md).
- If you are changing environment dynamics or scoring, pair [`architecture.md`](./architecture.md) with [`development.md`](./development.md).

## Support

- Project overview: [`../README.md`](../README.md)
- Repository: [GitHub](https://github.com/BiradarScripts/Meta-s-LedgerShield)
- Issues: [GitHub Issues](https://github.com/BiradarScripts/Meta-s-LedgerShield/issues)
- Discussions: [GitHub Discussions](https://github.com/BiradarScripts/Meta-s-LedgerShield/discussions)
