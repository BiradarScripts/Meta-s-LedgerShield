---
title: "Endpoints"
description: "Every HTTP endpoint on the LedgerShield FastAPI server: request/response payloads, example envelopes, and what each one returns."
icon: "plug"
sidebarTitle: "Endpoints"
---

All endpoints below are served from the [base URL](/api-reference) and return JSON. Episode-changing endpoints (`/reset`, `/step`) wrap their payloads in the [shared response envelope](/api-reference#response-envelope).

## `GET /`

Basic service probe.

Example response:

```json
{
  "status": "ok",
  "service": "LedgerShield OpenEnv"
}
```

## `GET /health`

Health check used by local smoke tests, Docker smoke tests, and CI.

Example response:

```json
{
  "status": "ok"
}
```

## `POST /reset`

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

## `POST /step`

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

## `GET /state`

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

## `GET /leaderboard`

Returns leaderboard entries if a leaderboard artifact exists, otherwise derives a minimal payload from the latest benchmark report artifact.

Typical response shape:

```json
{
  "benchmark": "ledgershield-controlbench-v1",
  "generated_at": "2026-04-24T11:05:28.417269+00:00",
  "entries": [
    {
      "model": "ledgershield/deterministic-baseline",
      "type": "deterministic-policy",
      "public_mean": 0.8749,
      "holdout_mean": 0.7063,
      "holdout_pass_k_consistent": 0.1667,
      "controlbench_institutional_loss_score": 0.5731,
      "controlbench_deployability_rating": "advisory",
      "certificate_required_mean": 0.55
    }
  ]
}
```

## `GET /benchmark-report`

Returns the latest benchmark report artifact if present. If none exists yet, the endpoint returns a placeholder note telling you to run `benchmark_report.py`.

The current report includes `controlbench_quarter`, a seeded institutional-control sequence with `loss_surface`, `calibration_gate`, `authority_timeline`, `sleeper_detection_rate`, `catastrophic_event_count`, and `deployability_rating`.

It also includes `generated_holdout_track`, `blind_control_track`, `sleeper_vigilance_track`, `certificate_required_track`, `human_baseline_track`, and `controlbench_two_agent_demo`. Together these cover public-core, generated-holdout, blind-control, sleeper, proof, human-anchor, and institutional-quarter evaluation.

## `GET /institutional-memory`

Returns the persistent AP-week memory for the current environment instance: queue depth, remaining manual-review and callback capacity, vendor trust, attacker-belief weights, cumulative loss surface, calibration-gated authority, sleeper-vendor state, and amendment count.

Important ControlBench fields:

| Field | Meaning |
|---|---|
| `loss_ledger.loss_surface` | cumulative fraud loss, false-positive cost, operational burn, calibration debt, vigilance loss, compliance, and catastrophic-event ratios |
| `calibration_gate` | running calibration error, authority level, and gate-trigger count |
| `authority_level` | current deployment authority (`full_authority`, `restricted_authority`, `review_only`, or `locked`) |
| `sleeper_vendors` | trust-building vendor state and activation/detection status |
| `trust_graph_memory` | persistent TrustGraph rollup across prior ControlBench cases |
| `controlbench_summary` | compact institutional loss score, authority level, sleeper detection rate, and catastrophic events |

## `GET /controlbench-summary`

Returns the latest generated ControlBench sequence artifact when available. If no artifact exists, it falls back to the live environment's institutional-memory summary.

## `GET /human-baseline-summary`

Returns the loaded human-baseline summary when present in the latest benchmark report or on disk. If no artifact exists, the endpoint returns an empty summary with a note describing how to provide `artifacts/human_baseline.json`.

## `POST /certify`

Returns a product-facing **LedgerShield Certify** report for an agent/workflow payload. The response packages the latest ControlBench report or live institutional-memory state into a certification status, deployability rating, authority recommendation, red-team plan, and monitoring requirements. This does not fabricate real human-baseline results or real uploaded ERP execution.

## `GET /certify-summary`

Returns the same Certify report using the latest benchmark artifact or live environment memory without requiring a request body.

## `GET /controlbench-visualization`

Returns a graph-ready visualization artifact with accuracy-vs-loss points, authority timeline, loss-surface bars, certificate-gate panel data, TrustGraph health, and demo-script hints. It is intended for dashboards or notebooks rather than as a full frontend UI.

## `POST /institutional-reset`

Resets the persistent institutional memory and loss ledger without changing the fixture database. This is useful before a fresh model-comparison run.
