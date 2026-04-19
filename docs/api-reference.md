# API Reference

LedgerShield exposes an OpenEnv-compatible HTTP API backed by FastAPI. This page documents the endpoints, action payloads, response envelope, and the key object shapes an agent needs to handle.

## Base URL

```text
http://127.0.0.1:8000
```

## Response Envelope

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

- `done`: the episode has ended for any reason
- `terminated`: a true terminal condition, currently a successful `submit_decision`
- `truncated`: the episode ended because of budget exhaustion or max-step exhaustion
- `info.reward_model`: structured reward breakdown for the last action

## Endpoints

### `GET /`

Basic service probe.

Example response:

```json
{
  "status": "ok",
  "service": "LedgerShield OpenEnv"
}
```

### `GET /health`

Health check used by local smoke tests, Docker smoke tests, and CI.

Example response:

```json
{
  "status": "ok"
}
```

### `POST /reset`

Start a new episode or load a specific case.

Request body:

```json
{
  "seed": 42,
  "case_id": "CASE-D-001"
}
```

Fields:

| Field | Type | Required | Notes |
|---|---|---|---|
| `seed` | integer | no | used for random case selection |
| `case_id` | string | no | when provided, loads that specific case |

Example response:

```json
{
  "observation": {
    "case_id": "CASE-D-001",
    "task_type": "task_d",
    "instruction": "Act as an AP analyst...",
    "visible_documents": [
      {
        "doc_id": "INV-D-001",
        "doc_type": "invoice",
        "thumbnail": "thumbnail::INV-D-001",
        "page_count": 1,
        "language": "en",
        "available_views": [
          "thumbnail",
          "zoom",
          "get_doc_crop",
          "ocr_fast",
          "ocr_accurate"
        ]
      }
    ],
    "revealed_artifacts": [],
    "pending_events": [],
    "budget_remaining": 16.0,
    "budget_total": 16.0,
    "step_count": 0,
    "max_steps": 18,
    "case_clock": 0,
    "risk_snapshot": {},
    "investigation_status": {},
    "last_tool_result": {},
    "messages": ["Loaded case CASE-D-001"],
    "allowed_actions": ["zoom", "get_doc_crop", "ocr", "submit_decision"],
    "available_interventions": ["request_callback_verification", "route_to_security"],
    "case_metadata": {
      "task_label": "AP inbox incident triage",
      "due_date_days": 30,
      "ashtg": "Adversarial Sequential Hypothesis Testing Game"
    },
    "portfolio_context": {},
    "sprt_state": {
      "recommended_decision": "NEEDS_REVIEW",
      "decision_ready": false,
      "optimal_stopping_reached": false,
      "posterior_probabilities": {
        "safe": 0.0833,
        "bank_fraud": 0.0833
      }
    },
    "tool_rankings": {
      "recommended_tool": "compare_bank_account",
      "voi": 0.17,
      "voi_cost_ratio": 1.13,
      "should_stop": false
    },
    "reward_machine": {
      "state_id": 0,
      "progress_fraction": 0.0,
      "accepting": false,
      "rejecting": false
    }
  },
  "reward": 0.0,
  "done": false,
  "truncated": false,
  "terminated": false,
  "info": {
    "case_id": "CASE-D-001"
  }
}
```

### `POST /step`

Execute one action.

Request body:

```json
{
  "action_type": "ocr",
  "payload": {
    "doc_id": "INV-D-001",
    "mode": "accurate"
  }
}
```

`submit_decision` payloads may also include `predicted_probabilities`, a probability distribution over latent hypotheses. This field is optional for backward compatibility.

Example response:

```json
{
  "observation": {
    "case_id": "CASE-D-001",
    "step_count": 1,
    "budget_remaining": 14.9,
    "last_tool_result": {
      "tool_name": "ocr",
      "success": true,
      "doc_id": "INV-D-001",
      "mode": "accurate",
      "scope": "document",
      "text_preview": "Invoice ...",
      "cost": 1.1,
      "reward_model": {
        "value": -1.0,
        "terminal": false,
        "components": {
          "voi_reward": -1.1,
          "information_value": 0.0,
          "cost_penalty": -1.1,
          "potential_delta": 0.1
        },
        "metadata": {
          "action_type": "ocr",
          "success": true
        }
      }
    }
  },
  "reward": -1.0,
  "done": false,
  "truncated": false,
  "terminated": false,
  "info": {
    "tool_name": "ocr",
    "success": true,
    "reward_model": {
      "value": -0.055,
      "terminal": false
    }
  }
}
```

### `GET /state`

Return the current public environment state, not the full hidden system state.

Key fields:

| Field | Meaning |
|---|---|
| `episode_id` | current episode UUID |
| `case_id` | current case |
| `task_type` | task family |
| `budget_total`, `budget_remaining` | budget accounting |
| `step_count`, `case_clock`, `max_steps` | episode progress |
| `trajectory` | public action history |
| `interventions_taken` | public intervention log |
| `observed_risk_signals` | only signals the agent has revealed |
| `sprt_state` | public sequential hypothesis-testing state |
| `tool_rankings` | VoI ranking over next actions |
| `reward_machine_state` | task-progress automaton snapshot |
| `pending_events` | delayed artifacts waiting to resolve |
| `pressure_events_seen` | injected pressure events already observed |
| `terminal_reason` | why the episode ended if it ended |

### `GET /leaderboard`

Returns leaderboard entries if a leaderboard artifact exists, otherwise derives a minimal payload from the latest benchmark report artifact.

Typical response shape:

```json
<!-- sync:api-leaderboard-example:start -->
{
  "benchmark": "ledgershield-v3",
  "generated_at": "2026-04-16T09:58:59.221224+00:00",
  "entries": [
    {
      "model": "ledgershield/deterministic-baseline",
      "type": "deterministic-policy",
      "public_mean": 0.9018,
      "holdout_mean": 0.7124,
      "holdout_pass_k_consistent": 0.2222
    }
  ]
}
<!-- sync:api-leaderboard-example:end -->
```

### `GET /benchmark-report`

Returns the latest benchmark report artifact if present. If none exists yet, the endpoint returns a placeholder note telling you to run `benchmark_report.py`.

### `GET /institutional-memory`

Returns the persistent AP-week memory for the current environment instance:
queue depth, remaining manual-review and callback capacity, vendor trust,
attacker-belief weights, cumulative loss ledger, and amendment count.

### `POST /institutional-reset`

Resets the persistent institutional memory and loss ledger without changing the
fixture database. This is useful before a fresh model-comparison run.

## Observation Shape

The observation returned by `/reset` and `/step` includes:

| Field | Type | Notes |
|---|---|---|
| `case_id` | string | current case ID |
| `task_type` | string | one of `task_a`..`task_e` |
| `instruction` | string | natural-language episode instruction |
| `visible_documents` | list | document catalog entries only, not raw OCR |
| `revealed_artifacts` | list | artifacts unlocked by interventions |
| `pending_events` | list | future artifact events not yet resolved |
| `budget_remaining` | float | current remaining budget |
| `budget_total` | float | episode budget |
| `step_count` | integer | executed step count |
| `max_steps` | integer | episode cap |
| `case_clock` | integer | logical clock used by delayed events |
| `risk_snapshot` | object | summarized public risk signals |
| `investigation_status` | object | tool/intervention/reveal counts |
| `last_tool_result` | object | payload from the most recent action |
| `messages` | list[string] | user-facing environment messages |
| `allowed_actions` | list[string] | investigation + intervention + final action names |
| `available_interventions` | list[string] | intervention subset |
| `case_metadata` | object | task label, due-date info, benchmark track, and track mode |
| `portfolio_context` | object | cross-invoice/campaign context when relevant |
| `institutional_memory` | object | public AP-week memory and cumulative loss state |
| `sprt_state` | object | present in instrumented mode, hidden in blind mode |
| `tool_rankings` | object | present in instrumented mode, hidden in blind mode |
| `reward_machine` | object | present in instrumented mode, hidden in blind mode |

## Action Taxonomy

### Investigation actions

| Action | Required payload |
|---|---|
| `zoom` | `doc_id`, optional `page`, `bbox` |
| `get_doc_crop` | `doc_id`, optional `page`, `bbox` |
| `ocr` | `doc_id`, optional `mode`, `page`, `bbox` |
| `lookup_vendor` | `vendor_key` |
| `lookup_vendor_history` | `vendor_key` |
| `lookup_policy` | optional `rule_id` |
| `lookup_po` | `po_id` |
| `lookup_receipt` | `receipt_id` |
| `search_ledger` | optional `vendor_key`, `invoice_number`, `amount` |
| `inspect_email_thread` | `thread_id` |
| `compare_bank_account` | `vendor_key`, `proposed_bank_account` |

### Intervention actions

| Action | Typical use |
|---|---|
| `request_callback_verification` | verify vendor identity or remittance changes |
| `freeze_vendor_profile` | contain high-risk vendor state |
| `request_bank_change_approval_chain` | unlock approval-chain artifact |
| `request_po_reconciliation` | unlock PO reconciliation artifact |
| `request_additional_receipt_evidence` | unlock receipt reconciliation artifact |
| `route_to_procurement` | route operationally |
| `route_to_security` | escalate suspicious incidents |
| `flag_duplicate_cluster_review` | request duplicate cluster artifact |
| `create_human_handoff` | create structured handoff packet |

### Final decision action

`submit_decision` carries the structured task output.

Minimal example:

```json
{
  "action_type": "submit_decision",
  "payload": {
    "decision": "ESCALATE_FRAUD",
    "confidence": 0.95,
    "reason_codes": ["sender_domain_spoof", "bank_override_attempt"],
    "policy_checks": {
      "bank_change_verification": "fail"
    },
    "evidence_map": {},
    "decision_certificate": {
      "certificate_version": "ledgershield-dcg-v1",
      "nodes": [
        {"id": "decision.final", "type": "decision", "value": "ESCALATE_FRAUD"}
      ],
      "edges": []
    }
  }
}
```

`decision_certificate` is optional for backward compatibility. If absent, the
server synthesizes a compatibility certificate from the existing evidence,
policy, reason-code, intervention, and counterfactual fields for diagnostics.
Agent-authored certificates are verified and can receive a small auditability
bonus or malformed-certificate penalty.

## Reward Model

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

## Python API Notes

The HTTP API is the main integration path, but the Python environment class also exposes:

- `LedgerShieldEnvironment.action_space()`
- `LedgerShieldEnvironment.observation_space()`
- `LedgerShieldEnvironment.render(mode="text")`

These are useful for local experiments and Gymnasium-style tooling, but they are not separate REST endpoints.

## Agent Capability Profiles

The reference agent in `inference.py` uses a `ModelCapabilityProfile` to adapt behavior to model strength. This is part of the agent-side logic, not the server API, but it affects how different models interact with the environment:

<!-- sync:api-capability-table:start -->
| Tier | Capability score | Plan mode | Repair level | Decision token budget |
|---|---|---|---|---|
| Elite | >= 5.0 | `llm` | `partial` | >= 1536 |
| Strong | >= 4.5 | `hybrid` | `partial` | >= 1280 |
| Standard | < 4.5 | `llm` | `none` | model default |
<!-- sync:api-capability-table:end -->

The tier determines investigation and intervention budget bonuses, whether repair attempts are made on malformed outputs, and how much planning context the agent maintains. In the code, `llm` is the internal label for the LLM-first planning path.
