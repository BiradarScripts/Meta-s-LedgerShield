---
title: "Action Taxonomy"
description: "The action types accepted by /step: investigation tools, interventions, and the final submit_decision payload."
icon: "list-tree"
sidebarTitle: "Actions"
---

Every action sent to [`POST /step`](/api-reference/endpoints#post-step) has an `action_type` and a `payload` matching one of the categories below.

## Investigation actions

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

## Intervention actions

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

## Final decision

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

`decision_certificate` is optional for backward compatibility. If absent, the server synthesizes a compatibility certificate from the existing evidence, policy, reason-code, intervention, and counterfactual fields for diagnostics. Agent-authored certificates are verified and can receive a small auditability bonus or malformed-certificate penalty.

For the per-task fields (`extracted_fields`, `discrepancies`, `duplicate_links`, `cross_invoice_links`, `campaign_signals`, `predicted_probabilities`, `counterfactual`), see [Tasks & scoring](/benchmark/tasks).
