# LedgerShield: Multimodal Payment Integrity Control Tower

LedgerShield is an OpenEnv-compatible environment for accounts payable audit, payment-integrity control, and fraud-safe approval routing.

## Why this version is stronger

- 4 deterministic AP tasks, including AP inbox incident triage
- proof-carrying decisions with evidence maps
- vendor history and email-thread fraud signals
- tool-cost economics
- no gold leakage through state()
- evidence-aware graders

## Tasks

### Task A - Proof-carrying field and line-item extraction
### Task B - Three-way match decisioning
### Task C - Batch payment-integrity triage
### Task D - AP inbox incident triage

## Actions

- `zoom`
- `get_doc_crop`
- `ocr`
- `lookup_vendor`
- `lookup_vendor_history`
- `lookup_policy`
- `lookup_po`
- `lookup_receipt`
- `search_ledger`
- `inspect_email_thread`
- `compare_bank_account`
- `submit_decision`

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r envs/ledgershield_env/server/requirements.txt
uvicorn envs.ledgershield_env.server.app:app --reload
```

## Example submission payload

```json
{
  "decision": "ESCALATE_FRAUD",
  "reason_codes": ["bank_override_attempt", "sender_domain_spoof", "duplicate_near_match"],
  "policy_checks": {
    "three_way_match": "pass",
    "bank_change_verification": "fail",
    "duplicate_check": "fail"
  },
  "evidence_map": {
    "bank_override_attempt": {
      "doc_id": "INV-D-001",
      "page": 1,
      "bbox": [10, 110, 170, 120],
      "token_ids": ["d6"]
    }
  },
  "counterfactual": "Would PAY if the bank account matched vendor master and there was no duplicate candidate."
}
```
