---
title: "Reward & Runtime"
description: "Per-step reward model, the Python environment class, and the agent capability profiles used by inference.py."
icon: "gauge"
sidebarTitle: "Reward & Runtime"
---

## Reward model

Every step may include `info.reward_model` and `observation.last_tool_result.reward_model` with:

| Field | Meaning |
|---|---|
| `value` | scalar reward emitted for the step |
| `terminal` | whether the reward ended the episode |
| `components` | shaping/cost/outcome breakdown |
| `metadata` | action type, success flag, terminal reason, and other step context |

The environment currently combines:

- action cost penalties
- PBRS shaping delta
- information-gain bonus
- milestone rewards
- terminal score on `submit_decision`

For a deeper treatment of the reward shaping constants, see [Architecture → Reward Design](/architecture/overview#reward-design).

## Python API notes

The HTTP API is the main integration path, but the Python environment class also exposes:

- `LedgerShieldEnvironment.action_space()`
- `LedgerShieldEnvironment.observation_space()`
- `LedgerShieldEnvironment.render(mode="text")`

These are useful for local experiments and Gymnasium-style tooling, but they are not separate REST endpoints.

## Agent capability profiles

The reference agent in `inference.py` uses a `ModelCapabilityProfile` to adapt behavior to model strength. This is part of the agent-side logic, not the server API, but it affects how different models interact with the environment:

| Tier | Capability score | Plan mode | Repair level | Decision token budget |
|---|---|---|---|---|
| Elite | >= 5.0 | `llm` | `partial` | >= 1536 |
| Strong | >= 4.5 | `hybrid` | `partial` | >= 1280 |
| Standard | < 4.5 | `llm` | `none` | model default |

The tier determines investigation and intervention budget bonuses, whether repair attempts are made on malformed outputs, and how much planning context the agent maintains. In the code, `llm` is the internal label for the LLM-first planning path.
