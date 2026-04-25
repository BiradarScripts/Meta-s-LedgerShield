# A3 Benchmark-Contract Audit Report

> Historical archive: this audit report belongs to the pre-ControlBench v2
> freeze. Current primary docs and artifacts use `ledgershield-controlbench-v1`.

**Date:** 2026-04-20  
**Scope:** 21 curated benchmark cases in `server/fixtures/cases.json`  
**Auditors:** LedgerShield v2 Evaluation Pipeline

---

## A3.1: Curated Case Catalog Audit

### Summary

All 21 curated benchmark cases pass structural integrity checks.

| Category | Result |
|---|---|
| Total cases | 21 |
| All have `task_type` | ✓ 21/21 |
| All have `primary_track` | ✓ 21/21 |
| All have `official_tracks` | ✓ 21/21 |
| All have `latent_mechanism` | ✓ 21/21 |
| Duplicate case IDs | ✓ none |

### Task Family Distribution

| Task | Count | Focus |
|---|---:|---|
| Task A | 4 | Proof-carrying invoice extraction |
| Task B | 5 | Three-way match and discrepancy handling |
| Task C | 4 | Duplicate and bank-change risk triage |
| Task D | 6 | AP inbox / BEC incident triage |
| Task E | 2 | Coordinated campaign scenarios |
| **Total** | **21** | |

### Track Distribution

`primary_track` (disjoint assignment):

| Track | Cases | IDs |
|---|---:|---|
| Case Track | 15 | CASE-A-001, CASE-A-002, CASE-B-001, CASE-B-002, CASE-B-003, CASE-C-001, CASE-C-002, CASE-D-002, CASE-A-003, CASE-B-004, CASE-B-005, CASE-C-003, CASE-C-004, CASE-D-006, CASE-A-004 |
| Adversarial Data Track | 4 | CASE-D-001, CASE-D-003, CASE-D-004, CASE-D-005 |
| Portfolio Track | 2 | CASE-E-001, CASE-E-002 |

`official_tracks` membership (overlapping assignment used in reporting):

| Track | Membership count | IDs |
|---|---:|---|
| Case Track | 21 | all curated cases |
| Adversarial Data Track | 10 | CASE-C-001, CASE-C-003, CASE-D-001, CASE-D-002, CASE-D-003, CASE-D-004, CASE-D-005, CASE-D-006, CASE-E-001, CASE-E-002 |
| Portfolio Track | 8 | CASE-D-001, CASE-D-002, CASE-D-003, CASE-D-004, CASE-D-005, CASE-D-006, CASE-E-001, CASE-E-002 |

### Difficulty Distribution

| Difficulty | Count |
|---|---:|
| Easy | 3 |
| Medium | 7 |
| Hard | 9 |
| Expert | 2 |

---

## A3.2: Latent Mechanism Field Audit

Each case includes all 8 latent-mechanism dimensions:

- `attack_family`
- `compromise_channel`
- `pressure_profile`
- `control_weakness`
- `vendor_history_state`
- `bank_adjustment_state`
- `campaign_linkage`
- `portfolio_context`

### Distribution Snapshot (from frozen curated cases)

| Field | Distribution |
|---|---|
| `attack_family` | clean=15, identity=4, campaign=2 |
| `compromise_channel` | document_stack=15, email_thread=6 |
| `pressure_profile` | routine=9, elevated=6, urgent_override=5, campaign=1 |
| `control_weakness` | baseline_control=6, three_way_match_gap=5, callback_gap=5, document_extraction_gap=4, workflow_override_gap=1 |
| `vendor_history_state` | steady_vendor=20, compromised_history_signal=1 |
| `bank_adjustment_state` | approved_on_file=9, requires_verification=7, proposed_unverified_change=5 |
| `campaign_linkage` | standalone=16, multi_invoice=2, campaign_linked=2, linked_pair=1 |
| `portfolio_context` | single_queue=18, campaign_week=3 |

### Sample Mechanism Metadata (exact from fixtures)

**CASE-D-001 (Adversarial primary):**
```json
{
  "latent_mechanism": {
    "attack_family": "identity",
    "compromise_channel": "email_thread",
    "pressure_profile": "urgent_override",
    "control_weakness": "callback_gap",
    "vendor_history_state": "steady_vendor",
    "bank_adjustment_state": "proposed_unverified_change",
    "campaign_linkage": "standalone",
    "portfolio_context": "single_queue"
  }
}
```

**CASE-E-001 (Portfolio primary):**
```json
{
  "latent_mechanism": {
    "attack_family": "campaign",
    "compromise_channel": "email_thread",
    "pressure_profile": "urgent_override",
    "control_weakness": "callback_gap",
    "vendor_history_state": "steady_vendor",
    "bank_adjustment_state": "proposed_unverified_change",
    "campaign_linkage": "campaign_linked",
    "portfolio_context": "campaign_week"
  }
}
```

### Validation Method

Metadata consistency is checked against the contract logic in `server/benchmark_contract.py` (`infer_latent_mechanism`, `infer_official_tracks`, `primary_track_for_case`, `ensure_case_contract_fields`).

---

## A3.3: Holdout and Contrastive Integrity

### No Benchmark-to-Holdout Leakage

Confirmed:

- Curated benchmark cases are fixed in `server/fixtures/cases.json`.
- Holdout variants are generated at evaluation time via `generate_holdout_suite(...)` over hard benchmark tasks.
- Generated holdouts use new IDs/variants and are kept separate from frozen curated IDs.

### Contrastive Pair Strategy

Contrastive evaluation uses benign twins generated from risky source cases (see `benchmark_report.py` + `server/case_factory.py`):

- Adversarial case and benign twin are mechanically similar.
- Fraud signals are removed or neutralized in the twin.
- Joint scoring rewards correct discrimination and penalizes over-control/under-control.

### Integrity Guarantees

| Property | Status | Evidence |
|---|---|---|
| No case ID collision | ✓ PASS | 21 unique curated IDs; generated variants use separate IDs |
| Holdout separation | ✓ PASS | Holdout suite generated from copies, not fixture overwrite |
| Contrastive pair validity | ✓ PASS | Adversarial/twin pairs scored with explicit joint metric |
| Track labeling completeness | ✓ PASS | Every case has `primary_track` + `official_tracks` |

---

## A3 Audit Conclusion

**PASSED**

The curated benchmark set is complete, internally consistent, and contract-aligned:

- 21/21 cases satisfy required schema fields.
- Task, track, and mechanism metadata are coherent with current evaluation code.
- Holdout and contrastive paths are structurally separated from curated fixtures.

These fixtures are ready for Round 2 evaluation and demo usage.

---

**Signed:** LedgerShield v2 Evaluation Pipeline  
**Date:** 2026-04-20
