---
title: "Observation Shape"
description: "Fields returned in the observation object from /reset and /step, including blind-mode vs instrumented-mode disclosure rules."
icon: "eye"
sidebarTitle: "Observation"
---

The observation returned by [`/reset`](/api-reference/endpoints#post-reset) and [`/step`](/api-reference/endpoints#post-step) includes the fields below. By default the environment runs in **blind mode** (`LEDGERSHIELD_TRACK_MODE=blind`) and the SPRT/VoI/reward-machine fields are hidden. Set `LEDGERSHIELD_TRACK_MODE=instrumented` to expose them for debugging.

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
| `institutional_memory` | object | public AP-week memory with cumulative loss surface, calibration gate, authority level, and sleeper-vendor state |
| `adversarial_falsifier` | object | terminal decision-falsifier diagnostics returned in final `/step` info |
| `control_boundary` | object | terminal statechart-style control-boundary diagnostics returned in final `/step` info |
| `trust_graph` | object | terminal TrustGraph projection returned in final `/step` info |
| `sprt_state` | object | present in instrumented mode, hidden in blind mode |
| `tool_rankings` | object | present in instrumented mode, hidden in blind mode |
| `reward_machine` | object | present in instrumented mode, hidden in blind mode |
