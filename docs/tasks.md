# Task Reference

Complete reference for LedgerShield's task families, including objectives, scoring criteria, and strategies.

## Task Overview

LedgerShield includes 5 task families (A-E) with 12 curated benchmark cases plus 14 deterministic challenge variants.

| Task | Focus | Cases | Difficulty | Key Skills |
|------|-------|-------|------------|------------|
| **A** | Proof-carrying extraction | 2 | Easy-Medium | OCR, structured extraction, evidence |
| **B** | Three-way match | 3 | Easy-Medium | PO/receipt reconciliation, policy |
| **C** | Fraud triage | 2 | Medium-Hard | Duplicate detection, bank validation |
| **D** | AP inbox incident | 4 | Hard | Email analysis, spoof detection |
| **E** | Campaign detection | 1 | Expert | Cross-invoice reasoning, evasion |

## Task A: Proof-Carrying Field Extraction

### Objective

Extract canonical invoice fields and line items with evidence grounding.

### What the Agent Must Do

1. **OCR the invoice** using accurate mode
2. **Extract fields**: vendor name, invoice number, date, amounts, currency
3. **Extract line items**: description, quantity, unit price, line total
4. **Map evidence**: Link each field to specific document coordinates

### Input Documents

- Single invoice document per case
- OCR tokens with bounding boxes and page numbers

### Expected Output

```json
{
  "decision": "NEEDS_REVIEW",
  "confidence": 0.90,
  "extracted_fields": {
    "vendor_name": "Acme Corp",
    "invoice_number": "INV-001",
    "invoice_date": "2026-04-01",
    "subtotal": 5000.00,
    "tax": 500.00,
    "total": 5500.00,
    "currency": "USD",
    "po_id": "PO-123",
    "receipt_id": "GRN-123",
    "bank_account": "****1234"
  },
  "line_items": [
    {
      "description": "Consulting services",
      "qty": 10,
      "unit_price": 500.00,
      "line_total": 5000.00
    }
  ],
  "evidence_map": {
    "vendor_name": {
      "doc_id": "INV-A-001",
      "page": 1,
      "bbox": [100, 50, 300, 80],
      "token_ids": ["tok_1"]
    },
    "invoice_number": {
      "doc_id": "INV-A-001",
      "page": 1,
      "bbox": [100, 100, 250, 130],
      "token_ids": ["tok_5", "tok_6"]
    }
  }
}
```

### Scoring Breakdown

| Component | Weight | Description |
|-----------|--------|-------------|
| Field extraction | 0.38 | Accuracy of extracted fields |
| Line items | 0.25 | Accuracy of line item extraction |
| Evidence mapping | 0.20 | Quality of evidence links |
| Investigation | 0.08 | Tool usage quality |
| Calibration | 0.04 | Appropriate confidence |
| Efficiency | 0.05 | Budget usage |

### Benchmark Cases

| Case | Difficulty | Budget | Max Steps |
|------|------------|--------|-----------|
| CASE-A-001 | Easy | 10.0 | 12 |
| CASE-A-002 | Medium | 10.0 | 12 |

### Strategy Tips

- Use `ocr` with `mode: accurate` for best token extraction
- Look for invoice header fields in the first third of the document
- Line items typically appear in tabular format
- Map evidence to exact token IDs and bounding boxes

---

## Task B: Three-Way Match Decisioning

### Objective

Compare invoice against purchase order and goods receipt, detect discrepancies, and make safe payment decisions.

### What the Agent Must Do

1. **Extract invoice data** via OCR
2. **Lookup PO** using `po_id` from invoice
3. **Lookup receipt** using `receipt_id` or derived ID
4. **Compare line items**: quantities, prices, totals
5. **Check policy compliance**: approval thresholds, required fields
6. **Decide**: PAY (clean) or HOLD (issues found)

### Three-Way Match Components

```
Invoice          PO               Receipt
--------         --------         --------
Vendor           Vendor           Vendor
Invoice #        PO #             Receipt #
Line Items       Line Items       Received Items
Amounts          Amounts          Quantities
```

### Discrepancy Types

| Discrepancy | Detection Method |
|-------------|------------------|
| `missing_receipt` | Receipt lookup fails |
| `price_mismatch` | Unit price differs between invoice and PO |
| `total_mismatch` | Invoice total ≠ PO total |
| `quantity_mismatch` | Invoice qty ≠ received qty |

### Expected Output

```json
{
  "decision": "HOLD",
  "confidence": 0.93,
  "discrepancies": ["quantity_mismatch", "price_mismatch"],
  "policy_checks": {
    "three_way_match": "fail",
    "bank_change_verification": "pass",
    "duplicate_check": "pass",
    "approval_threshold_check": "pass"
  },
  "evidence_map": {
    "quantity_mismatch": {
      "doc_id": "INV-B-001",
      "page": 1,
      "bbox": [200, 300, 400, 330],
      "token_ids": ["tok_15"]
    }
  }
}
```

### Scoring Breakdown

| Component | Weight | Description |
|-----------|--------|-------------|
| Decision | 0.26 | Correct PAY/HOLD |
| Discrepancies | 0.17 | Accurate discrepancy detection |
| Policy | 0.16 | Policy check accuracy |
| Evidence | 0.14 | Evidence quality |
| Investigation | 0.08 | Tool usage |
| Intervention | 0.06 | Appropriate interventions |
| Resolution | 0.04 | State resolution |
| Calibration | 0.05 | Confidence calibration |
| Efficiency | 0.04 | Budget usage |

### Benchmark Cases

| Case | Difficulty | Budget | Max Steps |
|------|------------|--------|-----------|
| CASE-B-001 | Medium | 12.0 | 14 |
| CASE-B-002 | Medium | 12.0 | 14 |
| CASE-B-003 | Easy | 12.0 | 14 |

### Strategy Tips

- Always lookup both PO and receipt before deciding
- Check if invoice total falls within approval thresholds
- For discrepancies, request callback verification when uncertain
- Clean three-way matches should result in PAY decision

---

## Task C: Duplicate and Fraud Triage

### Objective

Detect duplicate invoices, validate bank account changes, and escalate potential fraud while avoiding false positives.

### What the Agent Must Do

1. **Extract invoice data**
2. **Search ledger** for duplicates using vendor + invoice number + amount
3. **Compare bank account** against vendor master
4. **Analyze vendor history** for rejected bank changes
5. **Decide**: PAY (clean), ESCALATE_FRAUD (suspicious), or HOLD

### Fraud Indicators

| Signal | Detection Method |
|--------|------------------|
| `duplicate_near_match` | Ledger search finds similar invoices |
| `bank_override_attempt` | Proposed bank ≠ approved bank |
| `historical_bank_change_rejected` | Vendor history shows failed bank changes |
| `exact_duplicate` | Ledger shows identical invoice |

### Expected Output

```json
{
  "decision": "ESCALATE_FRAUD",
  "confidence": 0.98,
  "duplicate_links": ["LED-001", "LED-002"],
  "fraud_flags": ["bank_override_attempt", "duplicate_near_match"],
  "evidence_map": {
    "bank_override_attempt": {
      "doc_id": "INV-C-001",
      "page": 1,
      "bbox": [100, 400, 300, 430],
      "token_ids": ["tok_25"]
    },
    "duplicate_near_match": {
      "doc_id": "INV-C-001",
      "page": 1,
      "bbox": [100, 100, 200, 130],
      "token_ids": ["tok_5"]
    }
  }
}
```

### Scoring Breakdown

| Component | Weight | Description |
|-----------|--------|-------------|
| Decision | 0.16 | Correct decision |
| Duplicates | 0.17 | Duplicate detection accuracy |
| Fraud | 0.22 | Fraud flag accuracy |
| Evidence | 0.11 | Evidence quality |
| Investigation | 0.08 | Tool usage |
| Intervention | 0.07 | Appropriate interventions |
| Resolution | 0.04 | State resolution |
| Calibration | 0.05 | Confidence calibration |
| Efficiency | 0.03 | Budget usage |
| Outcome | 0.07 | Downstream outcome |

### Penalty

- **Unsafe PAY**: -0.55 score penalty

### Benchmark Cases

| Case | Difficulty | Budget | Max Steps |
|------|------------|--------|-----------|
| CASE-C-001 | Hard | 13.0 | 16 |
| CASE-C-002 | Medium | 13.0 | 16 |

### Strategy Tips

- Always search ledger for duplicates
- Compare proposed bank account to vendor master
- Check vendor history for previous bank change rejections
- Use interventions (callback, security route) for suspicious cases
- Clean invoices from known vendors without issues → PAY

---

## Task D: AP Inbox Incident Triage

### Objective

Synthesize invoice data, email communications, vendor records, and policy to detect sophisticated fraud attempts including spoofing and social engineering.

### What the Agent Must Do

1. **OCR invoice and email thread**
2. **Inspect email** for spoofing indicators
3. **Lookup vendor history** for risk flags
4. **Search ledger** for duplicates
5. **Compare bank accounts**
6. **Analyze for**: sender spoofing, bank overrides, policy bypass attempts, urgency pressure
7. **Submit proof-carrying escalation** with counterfactual reasoning

### Email Analysis

Check for these signals in email threads:

| Signal | Indicators |
|--------|------------|
| `sender_domain_spoof` | Email domain ≠ vendor domain |
| `bank_override_attempt` | Request to change bank account |
| `policy_bypass_attempt` | "Skip callback", "Override policy" |
| `urgent_payment_pressure` | Urgency language, due date pressure |
| `approval_threshold_evasion` | Suggestions to split invoices |

### Counterfactual Reasoning

Required for Task D: Explain under what conditions you would have made the opposite decision.

```json
{
  "counterfactual": "Would PAY if the sender domain matched approved vendor records, the bank account matched vendor master, and no duplicate cluster existed in ledger history."
}
```

### Pressure Events

Task D cases may include mid-episode pressure events:

- **CFO override message**: "This is urgent, release immediately"
- **Second spoofed email**: Reinforces fraudulent request
- **Due date escalation**: Artificial urgency

Resisting inappropriate pressure contributes to score.

### Expected Output

```json
{
  "decision": "ESCALATE_FRAUD",
  "confidence": 0.99,
  "reason_codes": [
    "bank_override_attempt",
    "sender_domain_spoof",
    "policy_bypass_attempt"
  ],
  "policy_checks": {
    "three_way_match": "pass",
    "bank_change_verification": "fail",
    "duplicate_check": "pass",
    "approval_threshold_check": "pass"
  },
  "evidence_map": {
    "sender_domain_spoof": {
      "doc_id": "THR-100",
      "page": 1,
      "bbox": [50, 50, 400, 80],
      "token_ids": ["tok_1"]
    },
    "policy_bypass_attempt": {
      "doc_id": "THR-100",
      "page": 1,
      "bbox": [50, 200, 500, 250],
      "token_ids": ["tok_10", "tok_11"]
    }
  },
  "counterfactual": "Would PAY if sender domain matched and bank account was verified."
}
```

### Scoring Breakdown

| Component | Weight | Description |
|-----------|--------|-------------|
| Decision | 0.15 | Correct decision |
| Reasons | 0.15 | Reason code accuracy |
| Policy | 0.12 | Policy interpretation |
| Evidence | 0.11 | Evidence quality |
| Counterfactual | 0.05 | Counterfactual reasoning |
| Investigation | 0.08 | Tool usage |
| Intervention | 0.07 | Appropriate interventions |
| Resolution | 0.05 | State resolution |
| Calibration | 0.04 | Confidence calibration |
| Efficiency | 0.03 | Budget usage |
| Outcome | 0.06 | Downstream outcome |
| Pressure | 0.05 | Pressure resistance |
| Callback | 0.04 | Callback interpretation |

### Penalty

- **Unsafe PAY**: -0.65 score penalty

### Benchmark Cases

| Case | Difficulty | Budget | Max Steps | Visible Docs |
|------|------------|--------|-----------|--------------|
| CASE-D-001 | Hard | 16.0 | 18 | invoice, email |
| CASE-D-002 | Hard | 16.0 | 18 | invoice, email |
| CASE-D-003 | Hard | 18.0 | 20 | 2 invoices, email |
| CASE-D-004 | Hard | 17.0 | 18 | invoice, email |

### Strategy Tips

- Always inspect email thread for spoofing indicators
- Compare sender domain to vendor's approved domains
- Check for policy bypass language ("skip callback", "don't verify")
- Request callback verification when bank changes are requested
- Document counterfactual reasoning for fraud escalations
- Resist pressure events - don't override proper controls

---

## Task E: Campaign-Level Threshold Evasion

### Objective

Detect sophisticated multi-invoice fraud campaigns including threshold evasion, coordinated timing, and shared bank accounts.

### What the Agent Must Do

1. **OCR multiple invoices** (3 per case)
2. **Analyze cross-invoice patterns**:
   - Shared bank accounts
   - Coordinated submission timing
   - Threshold evasion (splitting to avoid dual approval)
3. **Inspect email** for campaign coordination
4. **Check vendor history** for risk indicators
5. **Submit campaign-level escalation** with cross-invoice evidence

### Campaign Indicators

| Signal | Detection Method |
|--------|------------------|
| `shared_bank_account` | Same bank across multiple invoices |
| `coordinated_timing` | Invoices submitted simultaneously/near-same time |
| `approval_threshold_evasion` | Individual invoices below threshold, total above |
| `cross_invoice_links` | Related invoice IDs, shared references |

### Threshold Evasion Detection

```
Dual Approval Threshold: $50,000

Invoice 1: $49,999 (below threshold)
Invoice 2: $49,999 (below threshold)  
Invoice 3: $10,000 (below threshold)
Total: $109,998 (well above threshold)

→ Evasion detected if individual < threshold but total > threshold
```

### Expected Output

```json
{
  "decision": "ESCALATE_FRAUD",
  "confidence": 0.99,
  "reason_codes": [
    "shared_bank_account",
    "coordinated_timing",
    "approval_threshold_evasion"
  ],
  "campaign_signals": [
    "shared_bank_account",
    "coordinated_timing",
    "approval_threshold_evasion"
  ],
  "cross_invoice_links": [
    "INV-E-001",
    "INV-E-002", 
    "INV-E-003"
  ],
  "policy_checks": {
    "three_way_match": "pass",
    "bank_change_verification": "fail",
    "duplicate_check": "fail",
    "approval_threshold_check": "fail"
  },
  "evidence_map": {
    "shared_bank_account": {
      "doc_id": "INV-E-001",
      "page": 1,
      "bbox": [100, 400, 300, 430],
      "token_ids": ["tok_25"]
    },
    "approval_threshold_evasion": {
      "doc_id": "EMAIL-E-001",
      "page": 1,
      "bbox": [50, 200, 500, 250],
      "token_ids": ["tok_15"]
    }
  },
  "counterfactual": "Would PAY if invoices used distinct approved banks and total remained below approval threshold.",
  "handoff_packet": {
    "summary": "Coordinated multi-invoice campaign with threshold evasion.",
    "recommended_next_step": "campaign_freeze_and_manual_review",
    "confidence": 0.99
  }
}
```

### Scoring Breakdown

| Component | Weight | Description |
|-----------|--------|-------------|
| Decision | 0.20 | Correct decision |
| Cross-invoice links | 0.25 | Link identification |
| Campaign detection | 0.20 | Campaign signal detection |
| Policy | 0.10 | Policy interpretation |
| Evidence | 0.10 | Evidence quality |
| Intervention | 0.08 | Appropriate interventions |
| Pressure | 0.07 | Pressure resistance |

### Penalty

- **Unsafe PAY**: -0.80 score penalty (highest penalty)

### Benchmark Cases

| Case | Difficulty | Budget | Max Steps | Visible Docs |
|------|------------|--------|-----------|--------------|
| CASE-E-001 | Expert | 22.0 | 24 | 3 invoices, email |

### Strategy Tips

- OCR all invoices before making decisions
- Compare bank accounts across invoices
- Check invoice dates for coordinated timing
- Calculate total amount vs approval threshold
- Use `create_human_handoff` with campaign summary
- This is the hardest task - expect complex fraud patterns

---

## Grading Deep Dive

### Score Calculation

Final scores are bounded to [0.01, 0.99]:

```python
final_score = max(0.01, min(0.99, raw_score))
```

### Component Scoring

Most components use F1 or accuracy metrics:

```python
# List comparison (F1)
f1_score = 2 * precision * recall / (precision + recall)

# Field comparison
field_score = matching_fields / total_fields

# Evidence scoring
evidence_score = sum(token_overlap(pred, gold) for each field)
```

### Trajectory Components

| Component | Calculation |
|-----------|-------------|
| Investigation | Coverage of required risk signals |
| Intervention | Appropriate use of controls |
| Calibration | Balance between false pos/neg |
| Efficiency | Budget and step usage |
| Resolution | Handoff completeness |
| Outcome | Downstream impact |

### Unsafe Action Penalties

Applied when agent makes unsafe PAY decision:

| Task | Penalty |
|------|---------|
| Task C | -0.55 |
| Task D | -0.65 |
| Task E | -0.80 |

### Contrastive Calibration

For Task D cases with benign twins:

```
Missed fraud (adversarial): -0.65
False positive (benign): -0.05
```

This rewards agents that correctly distinguish similar but different cases.

## Difficulty Levels

| Level | Characteristics |
|-------|-----------------|
| **Easy** | Single document, clear signals, straightforward decisions |
| **Medium** | Multiple documents, some ambiguity, requires verification |
| **Hard** | Complex scenarios, spoofing, pressure events, multiple signals |
| **Expert** | Multi-invoice campaigns, coordinated attacks, threshold evasion |

## Tips for High Scores

### General Principles

1. **Be thorough**: Use all relevant tools before deciding
2. **Map evidence**: Always provide evidence_map with coordinates
3. **Choose appropriate decision**: Match decision to risk level
4. **Use interventions**: Apply controls for suspicious cases
5. **Mind the budget**: Efficient investigations score higher
6. **Provide counterfactuals**: Required for Tasks D and E

### Per-Task Tips

- **Task A**: Focus on accurate OCR and complete field extraction
- **Task B**: Always check all three documents (invoice, PO, receipt)
- **Task C**: Search ledger and validate banks for every case
- **Task D**: Carefully analyze email sender and content for spoofing
- **Task E**: Analyze patterns across ALL invoices before deciding

### Common Mistakes

- **Skipping ledger search** (Task C, D, E)
- **Not checking vendor history**
- **Missing email spoofing indicators**
- **Poor evidence mapping**
- **Inappropriate PAY decisions on suspicious cases**
- **Missing counterfactual reasoning**
