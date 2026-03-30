---
title: LedgerShield OpenEnv
emoji: 🛡️
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
  - accounts-payable
  - audit
  - fraud-detection
---

# LedgerShield

A state-of-the-art multimodal accounts payable audit OpenEnv environment. AI agents learn to audit invoices, detect fraud, and make payment decisions through the standard `step()` / `reset()` / `state()` API.

## Environment Overview

LedgerShield simulates a real-world accounts payable audit workflow where agents must:

- **Extract** invoice fields and line items from documents
- **Detect** discrepancies between purchase orders, receipts, and invoices
- **Identify** potential fraud indicators and duplicate payments
- **Apply** policy rules to determine correct payment decisions

## Quick Start

```python
from envs.ledgershield_env import LedgerShieldEnv, LedgerShieldAction

with LedgerShieldEnv(base_url="http://localhost:8000") as env:
    result = env.reset()
    print(f"Case: {result.observation.case_id}")
    print(f"Task: {result.observation.task_type}")
    
    result = env.step(LedgerShieldAction(
        action_type="lookup_vendor",
        payload={"vendor_key": "northwind-industrial"}
    ))
```

## Task Types

| Task | Description | Difficulty |
|------|-------------|------------|
| **task_a** | Invoice field extraction with evidence | Easy → Medium |
| **task_b** | Discrepancy detection and policy compliance | Medium |
| **task_c** | Fraud/duplicate detection | Medium → Hard |
| **task_d** | Full policy compliance review with counterfactual | Hard |

## Available Actions

| Action | Description | Cost |
|--------|-------------|------|
| `lookup_vendor` | Get vendor master data | 0.20 |
| `lookup_vendor_history` | Get vendor bank account changes | 0.25 |
| `lookup_policy` | Get policy rules | 0.15 |
| `lookup_po` | Get purchase order records | 0.20 |
| `lookup_receipt` | Get goods receipt records | 0.20 |
| `search_ledger` | Search for duplicate invoices | 0.35 |
| `inspect_email_thread` | Check for email fraud signals | 0.25 |
| `compare_bank_account` | Verify bank account matches | 0.15 |
| `ocr` | Extract text from documents | 0.45-1.10 |
| `zoom` | Get document crop with visual tokens | 0.20 |
| `get_doc_crop` | Get specific document region | 0.20 |
| `submit_decision` | Submit final payment decision | 0.0 |

## Decision Types

- `PAY` — Approve for payment
- `HOLD` — Hold for manual review
- `NEEDS_REVIEW` — Escalate for additional review
- `ESCALATE_FRAUD` — Escalate to fraud team

## Building Docker Image

```bash
docker build -t ledgershield:latest -f server/Dockerfile .
```

## Deploying to Hugging Face Spaces

```bash
openenv push
```

## Environment Details

### Observation Space

- `case_id`: Unique case identifier
- `task_type`: One of task_a, task_b, task_c, task_d
- `instruction`: Natural language task description
- `visible_documents`: List of available documents
- `budget_remaining`: Remaining tool budget
- `step_count`: Current step number
- `last_tool_result`: Result from previous action

### Reward Function

Rewards are based on:
- Field extraction accuracy (task_a)
- Discrepancy detection (task_b)
- Fraud/duplicate identification (task_c)
- Policy compliance (task_d)
- Budget efficiency penalty

Final scores range from 0.0 to 1.0 with partial credit for progress.
