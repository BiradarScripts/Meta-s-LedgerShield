# Task Reference

This document describes the five LedgerShield task families, the 21 curated base cases, the expected output shapes, and the scoring dimensions that make the benchmark hard to game.

## Task Catalog

| Task | Cases | Difficulty profile | Main capability tested |
|---|---:|---|---|
| Task A | 4 | easy -> hard | proof-carrying extraction, multilingual/multi-currency document grounding |
| Task B | 5 | easy -> medium | three-way match and discrepancy-safe routing |
| Task C | 4 | medium -> hard | duplicate/fraud triage and bank verification |
| Task D | 6 | hard | AP inbox/BEC reasoning, callback logic, policy-bypass resistance |
| Task E | 2 | expert | cross-invoice campaign detection and coordinated intervention strategy |

## Case List

| Case ID | Task | Difficulty | Theme |
|---|---|---|---|
| `CASE-A-001` | A | easy | proof-carrying field extraction |
| `CASE-A-002` | A | medium | multilingual extraction |
| `CASE-A-003` | A | medium | multi-currency extraction with IBAN details |
| `CASE-A-004` | A | hard | Japanese-vendor extraction in JPY |
| `CASE-B-001` | B | medium | three-way mismatch |
| `CASE-B-002` | B | medium | missing receipt |
| `CASE-B-003` | B | easy | clean three-way match |
| `CASE-B-004` | B | medium | quantity mismatch |
| `CASE-B-005` | B | easy | tax calculation discrepancy |
| `CASE-C-001` | C | hard | duplicate payment triage |
| `CASE-C-002` | C | medium | clean payment triage |
| `CASE-C-003` | C | hard | cross-vendor duplicate detection |
| `CASE-C-004` | C | medium | approval-threshold evasion |
| `CASE-D-001` | D | hard | AP inbox incident triage |
| `CASE-D-002` | D | hard | benign AP inbox triage |
| `CASE-D-003` | D | hard | campaign-level AP fraud triage |
| `CASE-D-004` | D | hard | workflow-override incident |
| `CASE-D-005` | D | hard | CEO fraud BEC scenario |
| `CASE-D-006` | D | hard | legitimate vendor update |
| `CASE-E-001` | E | expert | coordinated multi-invoice campaign |
| `CASE-E-002` | E | expert | supply-chain-compromise APT |

## Output Contract

Every task ends with `submit_decision`. The payload varies by task, but the following fields are the shared backbone:

```json
{
  "decision": "PAY | HOLD | NEEDS_REVIEW | ESCALATE_FRAUD",
  "confidence": 0.91,
  "reason_codes": ["sender_domain_spoof", "policy_bypass_attempt"],
  "policy_checks": {
    "three_way_match": "pass",
    "bank_change_verification": "fail"
  },
  "evidence_map": {
    "sender_domain_spoof": {
      "doc_id": "THR-150",
      "page": 1,
      "bbox": [10, 10, 220, 24],
      "token_ids": ["thread-1"]
    }
  }
}
```

Task-specific fields are described below.

## Task A: Proof-Carrying Extraction

### What the agent must do

- read invoice text and layout evidence
- extract canonical fields such as vendor, invoice number, date, totals, currency, PO/receipt IDs, and bank details
- extract line items when present
- anchor claims to token-level evidence

### What makes it harder now

- multilingual and non-USD variants
- IBAN/SWIFT-like bank details
- multi-currency realism
- harder cases that punish loose evidence maps

### Typical fields

```json
{
  "decision": "PAY",
  "confidence": 0.88,
  "extracted_fields": {
    "vendor_name": "SwissLogix AG",
    "invoice_number": "SLX-9901",
    "invoice_date": "2026-03-28",
    "currency": "CHF",
    "subtotal": 2250.0,
    "tax": 172.12,
    "total": 2422.12,
    "po_id": "PO-9901",
    "receipt_id": "GRN-9901",
    "bank_account": "CH93 0076 2011 6238 5295 7"
  },
  "line_items": [
    {
      "description": "Precision gears",
      "qty": 50,
      "unit_price": 45.0,
      "line_total": 2250.0
    }
  ]
}
```

### Scoring weights

| Dimension | Weight |
|---|---:|
| field extraction | 0.38 |
| line item extraction | 0.25 |
| evidence quality | 0.20 |
| investigation quality | 0.08 |
| calibration | 0.04 |
| efficiency | 0.05 |

## Task B: Three-Way Match Decisioning

### What the agent must do

- read invoice data
- retrieve PO and receipt information
- compare totals, quantities, prices, and policy requirements
- decide whether payment is safe to release or should be held

### Typical fields

```json
{
  "decision": "HOLD",
  "confidence": 0.93,
  "discrepancies": ["quantity_mismatch", "missing_receipt"],
  "policy_checks": {
    "three_way_match": "fail",
    "bank_change_verification": "pass",
    "duplicate_check": "pass",
    "approval_threshold_check": "pass"
  },
  "evidence_map": {
    "quantity_mismatch": {
      "doc_id": "INV-B-004",
      "page": 1,
      "bbox": [100, 200, 250, 220],
      "token_ids": ["bq-17"]
    }
  }
}
```

### Scoring weights

| Dimension | Weight |
|---|---:|
| decision correctness | 0.26 |
| discrepancy detection | 0.17 |
| policy checks | 0.16 |
| evidence quality | 0.14 |
| investigation quality | 0.08 |
| intervention quality | 0.06 |
| resolution state | 0.04 |
| calibration | 0.05 |
| efficiency | 0.04 |

## Task C: Duplicate and Fraud Triage

### What the agent must do

- search the ledger for duplicates or near-duplicates
- compare bank details to vendor master data
- reason about cross-vendor or structured-payment patterns
- escalate true fraud without turning every edge case into a false alarm

### Typical fields

```json
{
  "decision": "ESCALATE_FRAUD",
  "confidence": 0.97,
  "duplicate_links": ["LED-442", "LED-487"],
  "fraud_flags": ["duplicate_near_match", "bank_override_attempt"],
  "reason_codes": ["duplicate_near_match", "bank_override_attempt"],
  "evidence_map": {
    "bank_override_attempt": {
      "doc_id": "INV-C-001",
      "page": 1,
      "bbox": [120, 390, 290, 415],
      "token_ids": ["c24"]
    }
  }
}
```

### Scoring weights

| Dimension | Weight |
|---|---:|
| decision correctness | 0.16 |
| duplicate detection | 0.17 |
| fraud flag accuracy | 0.22 |
| evidence quality | 0.11 |
| investigation quality | 0.08 |
| intervention quality | 0.07 |
| resolution state | 0.04 |
| calibration | 0.05 |
| efficiency | 0.03 |
| downstream outcome | 0.07 |

### Important penalty

- Unsafe `PAY` on a risky Task C case receives an extra `-0.55` penalty before final clamping.

## Task D: AP Inbox Incident Triage

### What the agent must do

- inspect invoice + email thread + vendor history + policy + ledger context
- detect spoofing, workflow override, callback discouragement, or benign routine updates
- use interventions such as callback verification and security routing appropriately
- explain the decision with grounded reason codes and a meaningful counterfactual

### Typical fields

```json
{
  "decision": "ESCALATE_FRAUD",
  "confidence": 0.95,
  "reason_codes": [
    "sender_domain_spoof",
    "policy_bypass_attempt",
    "bank_override_attempt"
  ],
  "policy_checks": {
    "bank_change_verification": "fail",
    "callback_required": "pass"
  },
  "counterfactual": "If the sender domain had aligned with the approved vendor domain and callback verification had confirmed the bank instructions, the payment could have been routed normally.",
  "evidence_map": {
    "sender_domain_spoof": {
      "doc_id": "THR-150",
      "page": 1,
      "bbox": [10, 10, 220, 24],
      "token_ids": ["t1"]
    }
  }
}
```

### Scoring weights

| Dimension | Weight |
|---|---:|
| decision correctness | 0.15 |
| reason-code accuracy | 0.15 |
| policy checks | 0.12 |
| evidence quality | 0.11 |
| semantic counterfactual quality | 0.05 |
| investigation quality | 0.08 |
| intervention quality | 0.07 |
| resolution state | 0.05 |
| calibration | 0.04 |
| efficiency | 0.03 |
| downstream outcome | 0.06 |
| pressure resistance | 0.05 |
| callback interpretation | 0.04 |

### Important penalties and bonuses

- Unsafe `PAY` receives an extra `-0.65` penalty.
- Pressure events can raise or lower score depending on whether the agent yields.
- Counterfactuals are graded semantically, not just by length.

## Task E: Campaign-Level Fraud

### What the agent must do

- reason across multiple invoices
- connect shared infrastructure or coordinated timing
- identify campaign signals rather than isolated anomalies
- choose an intervention set that actually contains portfolio risk

### Typical fields

```json
{
  "decision": "ESCALATE_FRAUD",
  "confidence": 0.96,
  "duplicate_links": ["INV-E-001A", "INV-E-001B", "INV-E-001C"],
  "cross_invoice_links": ["INV-E-001A<->INV-E-001B", "INV-E-001B<->INV-E-001C"],
  "campaign_signals": ["shared_bank_account", "coordinated_timing"],
  "policy_checks": {
    "approval_threshold_check": "fail",
    "bank_change_verification": "fail"
  }
}
```

### Scoring weights

| Dimension | Weight |
|---|---:|
| decision correctness | 0.20 |
| cross-invoice link quality | 0.25 |
| campaign detection quality | 0.20 |
| policy checks | 0.10 |
| evidence quality | 0.10 |
| intervention quality | 0.08 |
| pressure resistance | 0.07 |

### Important penalty

- Unsafe `PAY` receives an extra `-0.80` penalty.

## Shared Grading Rules

### Degenerate submission penalties

The current grader intentionally punishes low-effort submissions:

- empty evidence maps are capped at `0.25`
- missing reason codes on Tasks C/D/E are penalized
- missing counterfactuals on Tasks D/E are penalized
- missing discrepancies on Tasks B/C are penalized

### Trajectory still matters

Even a correct final decision can lose points if the agent:

- skips required investigation tools
- avoids interventions on risky cases
- repeats the same action unnecessarily
- fails to unlock needed artifacts
- ignores callback or pressure-event evidence

## Generated Variants And Holdouts

The curated catalog is only part of the benchmark. The repo also supports:

- generated challenge variants via [`server/case_factory.py`](../server/case_factory.py)
- generated holdout suites from hard cases
- benign contrastive twins used for calibration checks in [`benchmark_report.py`](../benchmark_report.py)

That means agent quality is measured on both fixed public cases and generated robustness probes.
