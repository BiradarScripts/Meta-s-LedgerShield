---
title: "API Reference"
description: "OpenEnv-compatible REST API: base URL, the shared response envelope, and how to navigate the rest of the API reference."
icon: "webhook"
sidebarTitle: "Overview"
---

LedgerShield exposes an OpenEnv-compatible HTTP API backed by FastAPI. This section documents the endpoints, action payloads, response envelope, and the key object shapes an agent needs to handle.

## Base URL

```text
http://127.0.0.1:8000
```

## Response envelope

`POST /reset` and `POST /step` return a common top-level envelope:

```json
{
  "observation": {},
  "reward": 0.0,
  "done": false,
  "truncated": false,
  "terminated": false,
  "info": {}
}
```

### Semantics

- `done` — the episode has ended for any reason
- `terminated` — a true terminal condition, currently a successful `submit_decision`
- `truncated` — the episode ended because of budget exhaustion or max-step exhaustion
- `info.reward_model` — structured reward breakdown for the last action

## Sections

- [Endpoints](/api-reference/endpoints) — every HTTP endpoint, request/response shape, and example payloads
- [Observation shape](/api-reference/observation) — fields returned in `observation` from `/reset` and `/step`
- [Action taxonomy](/api-reference/actions) — investigation tools, interventions, and the `submit_decision` payload
- [Reward & runtime](/api-reference/reward-and-runtime) — reward model, Python API, and agent capability profiles
