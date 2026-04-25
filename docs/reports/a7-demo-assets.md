---
title: "A7 — Demo Asset Package"
description: "Frozen demo asset bundle: scripts, traces, screenshots, and judge-facing materials."
icon: "image"
sidebarTitle: "A7 Demo Assets"
---

> Source: `docs/A7_DEMO_ASSET_PACKAGE.md` (consolidated)

**Date:** 2026-04-20  
**Main Demo Case:** CASE-D-001  
**Status:** FROZEN

---

## Demo Case Selection

**CASE-D-001** has been selected as the main live demo case because it:

1. **Demonstrates core challenge:** Email-based CEO fraud with callback verification opportunity
2. **Shows agent sophistication:** Requires email thread analysis, bank account comparison, callback intervention
3. **Has clear resolution path:** Attackers vs. legitimate CEO; binary outcome
4. **Is representative:** Task D (AP triage) is the largest task family (6 cases)
5. **Supports all three tracks:** Case Track, Adversarial Data Track, and Portfolio Track

### Case Details

```json
{
  "case_id": "CASE-D-001",
  "task_type": "task_d",
  "difficulty": "hard",
  "primary_track": "adversarial",
  "official_tracks": ["adversarial", "case", "portfolio"],
  "task_label": "AP Inbox Triage - CEO Fraud",
  "mechanism": {
    "attack_family": "identity",
    "compromise_channel": "email_thread",
    "pressure_profile": "high"
  }
}
```

---

## Demo Action Flow

**Frozen action sequence for live demo:**

1. **Reset in blind mode**
   - Observe: basic task, instruction, visible documents
   - Institution memory is clean (fresh AP-week)
   - Agent sees inbox document: payment request email

2. **Inspect email thread**
   - Action: request email thread inspection
   - Reveals: sender email, subject, body, timestamp
   - Signal: email appears to be from CEO but syntax/tone slightly off

3. **Compare bank account**
   - Action: compare_bank_account for payment routing
   - Reveals: requested bank account differs from vendor's standard account
   - Signal: This is a red flag (attacker changed bank routing)

4. **Request callback verification**
   - Action: request_callback_verification (intervention)
   - Result: Callback to actual CEO reveals he didn't send the email
   - Signal: Definitive proof of fraud

5. **Submit decision**
   - Action: submit_decision with reason codes
   - Submission: ESCALATE_FRAUD, approve_category="zero_pay"
   - Result: Correct decision, fraud prevented

---

## Demo Metrics Snapshot

After execution, the demo will show:

```json
{
  "case_id": "CASE-D-001",
  "score": 0.9188,
  "result_class": "valid_success",
  "decision": "ESCALATE_FRAUD",
  "control_satisfied_resolution": 1.0,
  "institutional_utility": 0.95,
  "unsafe_release_rate": 0.0,
  "actions_taken": 5,
  "investigation_budget_used": 0.60,
  "decision_certificate": {...}
}
```

---

## Demo Asset Checklist

- [x] **Live case selected:** CASE-D-001 (frozen)
- [x] **Action flow documented:** 5-step investigation → decision
- [x] **Expected outputs known:** score, result_class, decision
- [x] **Fallback screenshots prepared:** (pre-recorded trace available)
- [x] **Server ready:** FastAPI running, endpoints live
- [x] **Demo trace frozen:** artifacts/demo_trace_CASE_D_001.json (2.4 KB)

---

## Fallback Demo Assets

If live demo fails:

1. **Pre-recorded trace:** artifacts/demo_trace_CASE_D_001.json
   - Full episode record with all steps and results
   - Can be replayed or shown as screenshot

2. **Before/after visual:** artifacts/before_after.html
   - Shows measured deterministic profile delta (`gpt-3.5-turbo` -> `gpt-5.4`)
   - Portfolio track snapshot

3. **Deterministic baseline:** inference.py with deterministic policy
   - Guaranteed reproducible
   - Can be executed locally or in sandbox

---

## Demo Success Criteria

The demo is considered successful if judges see:

1. ✓ **Environment clarity:** Case description, observation mode, action choices visible
2. ✓ **Agent reasoning:** Tool calls are explicable (why callback verification?)
3. ✓ **Evidence discovery:** Email thread and bank account differences highlighted
4. ✓ **Safety outcome:** Fraud is caught, no unsafe payment released
5. ✓ **Metrics visibility:** Score, result class, decision certificate shown

---

**Certified:** Demo package is frozen and ready for live or fallback execution.

**Date:** 2026-04-20

---
