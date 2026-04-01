---
title: LedgerShield
emoji: 🛡️
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 8000
pinned: false
---



# LedgerShield - Hackathon Winning Solution

## Meta OpenEnv Hackathon - Accounts Payable Audit AI Agent

---

## 🎯 Quick Start

```bash
# Run inference with GitHub Models
python inference.py \
  --api-url "https://models.github.ai/inference" \
  --model "openai/gpt-4.1" \
  --token "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"
```

---

## 🏆 Winning Threshold

| Metric | Required | Target |
|--------|----------|--------|
| Average Score | > 0.6 | > 0.7 |
| Success Rate | > 60% | > 80% |

---

## 📁 Project Structure

```
Meta-s-LedgerShield/
├── inference.py              # HACKATHON-WINNING inference script (THIS IS YOUR KEY FILE)
├── README.md                 # This documentation
├── validate_grader.py        # Grader validation tests
├── test_scoring.py          # Score simulation script
├── envs/
│   └── ledgershield_env/
│       ├── openenv.yaml      # OpenEnv specification
│       ├── models.py         # Typed models (Action, Observation, State)
│       ├── client.py         # EnvClient for connecting to server
│       ├── openenv_compat.py # OpenEnv API compatibility layer
│       └── server/
│           ├── app.py        # FastAPI application
│           ├── environment.py # LedgerShieldEnvironment class
│           ├── grading.py    # Task graders and scoring
│           ├── tools.py      # Tool implementations
│           ├── schema.py     # Utility functions
│           ├── risk_rules.py # Risk assessment rules
│           ├── data_loader.py# Fixture data loading
│           └── fixtures/      # Test data (cases, vendors, etc.)
├── tests/
│   ├── test_ledgershield_env.py
│   └── test_api_smoke.py
└── pyproject.toml
```

---

## 🔬 What is LedgerShield?

LedgerShield is an **OpenEnv-compatible environment** that simulates a real-world accounts payable audit workflow.

AI agents must:
- **Extract** invoice fields and line items from multimodal documents
- **Detect** discrepancies between purchase orders, receipts, and invoices
- **Identify** potential fraud indicators and duplicate payments
- **Apply** policy rules to determine correct payment decisions

---

## 📊 Task Types & Scoring

### Task A: Invoice Field Extraction

| Component | Weight | How to Score |
|-----------|--------|--------------|
| Field accuracy | 45% | Match vendor_name, invoice_number, date, amounts |
| Line items | 30% | Include correct description, qty, unit_price, line_total |
| Evidence map | 25% | Link each field to doc_id, page, bbox, token_ids |

### Task B: Discrepancy Detection

| Component | Weight |
|-----------|--------|
| Decision | 35% |
| Discrepancies | 25% |
| Policy checks | 20% |
| Evidence map | 20% |

### Task C: Fraud Detection

| Component | Weight |
|-----------|--------|
| Decision | 25% |
| Duplicate links | 25% |
| Fraud flags | 35% |
| Evidence map | 15% |

### Task D: Policy Compliance

| Component | Weight |
|-----------|--------|
| Decision | 25% |
| Reason codes | 25% |
| Policy checks | 20% |
| Evidence map | 20% |
| Counterfactual | 10% |

---

## 🧠 The Solution: How It Works

### Workflow

```
1. LLM receives task instruction
      ↓
2. LLM calls OCR on invoice document
      ↓
3. Code parses OCR tokens → extracts fields
      ↓
4. LLM calls lookup_vendor, lookup_po, lookup_receipt
      ↓
5. Code builds evidence_map linking fields to locations
      ↓
6. LLM calls submit_decision with FULL payload
      ↓
7. Grader scores: fields + line_items + evidence_map
```

### Key Innovation: Evidence Map

The **evidence_map** is critical for winning:

```python
evidence_map = {
    "vendor_name": {
        "doc_id": "INV-A-001",
        "page": 1,
        "bbox": [x, y, width, height],  # Bounding box
        "token_ids": ["a1n"]            # OCR token reference
    },
    "invoice_number": {...},
    "subtotal": {...},
    # ... each extracted field
}
```

**Why it matters:** Evidence map adds ~0.25 to your score per task.

---

## 📈 Score Analysis

### Theoretical Scores

| Submission Quality | Expected Score |
|-------------------|----------------|
| Just decision (no data) | 0.00 |
| Partial fields | 0.09 |
| All fields, no evidence | 0.42 avg |
| **Perfect + evidence_map** | **0.85+** |
| 80% extraction (realistic) | **0.61** |

### Manual Test Results

```python
# Perfect submission (all fields + evidence_map)
Score: 0.8449
Breakdown: {'field_score': 1.0, 'line_item_score': 1.0, 'evidence_score': 0.38}

# 80% correct (realistic LLM)
Score: 0.6136
Breakdown: {'field_score': 0.7, 'line_item_score': 0.875, 'evidence_score': 0.14}
```

---

## 🚀 Running the Solution

### Prerequisites

1. **Python 3.11+**
2. **GitHub PAT with `models:read` scope**

To create/update your token:
1. Go to: https://github.com/settings/tokens?type=beta
2. Generate new token or edit existing
3. Enable **`models:read`** permission

### Start the Environment Server

```bash
# Terminal 1: Start server
cd /Users/aryamanpathak/meta-hackathon/Meta-s-LedgerShield
python -m uvicorn envs.ledgershield_env.server.app:app --host 0.0.0.0 --port 8000
```

### Run Inference

```bash
# Terminal 2: Run inference
cd /Users/aryamanpathak/meta-hackathon/Meta-s-LedgerShield
python3.11 inference.py \
  --api-url "https://models.github.ai/inference" \
  --model "openai/gpt-4.1" \
  --token "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" \
  --cases CASE-A-001 CASE-A-002 CASE-B-001 CASE-C-001 CASE-D-001
```

### Alternative: Run Specific Model

```bash
# GPT-4.1 (recommended - best reasoning)
--model "openai/gpt-4.1"

# GPT-4.1-nano (faster, cheaper, still good)
--model "openai/gpt-4.1-nano"

# Claude 4 Sonnet (excellent for structured extraction)
--model "anthropic/claude-4-sonnet"

# Llama 4 Maverick (good value)
--model "meta/llama-4-maverick"
```

---

## 🔧 Solution Architecture

### 1. Field Extraction (`extract_fields_from_ocr`)

Parses OCR tokens using regex patterns:

```python
def extract_fields_from_ocr(ocr_result):
    # Vendor name - first substantial non-numeric text
    # Invoice number - pattern: INV-XXXX
    # Date - pattern: YYYY-MM-DD
    # Currency - USD, EUR, INR, etc.
    # Amounts - Subtotal, Tax, Total from "Subtotal 1234.56" format
```

### 2. Evidence Map Building

Links extracted fields to document locations:

```python
evidence_map[field_name] = {
    "doc_id": token['doc_id'],
    "page": token['page'],
    "bbox": token['bbox'],
    "token_ids": [token['token_id']]
}
```

### 3. Multi-Step Agent Loop

1. **Research phase**: Call OCR → Parse → Lookup vendor/PO/receipt
2. **Extract phase**: Build extracted_fields, line_items, evidence_map
3. **Submit phase**: Call submit_decision with complete payload

### 4. Task-Specific Payloads

```python
# Task A: Field extraction
{
    "decision": "NEEDS_REVIEW",
    "extracted_fields": {...},
    "line_items": [...],
    "evidence_map": {...}
}

# Task B: Discrepancy detection
{
    "decision": "HOLD",
    "discrepancies": [...],
    "policy_checks": {...},
    "evidence_map": {...}
}

# Task C: Fraud detection
{
    "decision": "ESCALATE_FRAUD",
    "duplicate_links": [...],
    "fraud_flags": [...],
    "evidence_map": {...}
}

# Task D: Policy compliance
{
    "decision": "NEEDS_REVIEW",
    "reason_codes": [...],
    "policy_checks": {...},
    "evidence_map": {...},
    "counterfactual": "Would PAY if..."
}
```

---

## 📝 Available Tools

| Tool | Purpose | Payload |
|------|---------|---------|
| `ocr` | Extract text from invoice | `{"doc_id": "...", "mode": "fast"}` |
| `zoom` | Magnify document region | `{"doc_id": "...", "bbox": [...]}` |
| `get_doc_crop` | Get cropped document | `{"doc_id": "...", "page": 1, "bbox": [...]}` |
| `lookup_vendor` | Get vendor details | `{"vendor_key": "..."}` |
| `lookup_vendor_history` | Get vendor transaction history | `{"vendor_key": "..."}` |
| `lookup_policy` | Get applicable policies | `{}` |
| `lookup_po` | Get purchase order | `{"po_id": "..."}` |
| `lookup_receipt` | Get receipt/GRN | `{"receipt_id": "..."}` |
| `search_ledger` | Search for duplicates | `{"vendor_key": "...", "amount": ...}` |
| `inspect_email_thread` | Check email communications | `{"thread_id": "..."}` |
| `compare_bank_account` | Verify bank accounts | `{"vendor_key": "...", "bank_account": "..."}` |
| `submit_decision` | Submit final decision | See payloads above |

---

## 🧪 Testing & Validation

### Validate Grader

```bash
python validate_grader.py
```

This tests:
- API health
- Gymnasium loop
- Reward stability
- Edge cases
- 100+ episode benchmark
- Determinism
- Exploit resistance

### Score Simulation

```bash
python test_scoring.py
```

Tests different agent strategies:
- Random baseline
- No research
- Partial research
- Good effort
- Near-perfect
- Gold standard

### Manual Score Test

```python
from envs.ledgershield_env.server.environment import LedgerShieldEnvironment
from envs.ledgershield_env import LedgerShieldAction

env = LedgerShieldEnvironment()
env.reset(case_id='CASE-A-001')

result = env.step(LedgerShieldAction(
    action_type='submit_decision',
    payload={
        'decision': 'NEEDS_REVIEW',
        'extracted_fields': {'vendor_name': 'Northwind Industrial', ...},
        'line_items': [...],
        'evidence_map': {...}
    }
))

print(f"Score: {result.last_tool_result.get('final_score', 0.0):.4f}")
```

---

## 🎓 Tips for Winning

### 1. Always Include Evidence Map

Even partial evidence_map adds points. Structure:
```python
evidence_map = {
    "vendor_name": {"doc_id": "INV-A-001", "page": 1, "bbox": [x,y,w,h], "token_ids": ["a1n"]}
}
```

### 2. Extract Complete Fields

For Task A, target these fields:
- vendor_name
- invoice_number
- invoice_date
- currency
- subtotal
- tax
- total
- po_id
- receipt_id
- bank_account

### 3. Include Line Items

Even basic line items help:
```python
line_items = [
    {"description": "...", "qty": 100, "unit_price": 12.0, "line_total": 1200.0}
]
```

### 4. Use GPT-4.1 or Claude

These models have:
- Better structured output
- Improved tool calling
- Stronger reasoning

### 5. Don't Over-Research

- 3-4 tool calls is enough
- Budget efficiency is penalized
- Auto-submit kicks in after 3+ steps with OCR

---

## 🔐 Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `API_BASE_URL` | LLM API endpoint | Yes | `https://router.huggingface.co/v1` |
| `MODEL_NAME` | Model identifier | Yes | `meta-llama/Llama-3.3-70B-Instruct` |
| `HF_TOKEN` | API key | Yes | - |
| `ENV_URL` | Environment server | No | `http://localhost:8000` |

### GitHub Models Configuration

```bash
export API_BASE_URL="https://models.github.ai/inference"
export MODEL_NAME="openai/gpt-4.1"
export HF_TOKEN="github_pat_11BCEVC3A0..."
```

---

## 📦 Deployment

### Docker Build

```bash
docker build -t ledgershield:latest -f envs/ledgershield_env/server/Dockerfile .
```

### Hugging Face Spaces

```bash
pip install openenv-core
openenv push
```

---

## 👥 Team

- **Shreyas Biradar** (Team Lead)
- **Aryaman Pathak**
- **Hemant Gupta**

---

## 📄 License

MIT

---

## 🗺️ Roadmap

- [x] Basic inference implementation
- [x] OCR field extraction
- [x] Evidence map building
- [x] Multi-step agent workflow
- [x] Task-specific payloads
- [x] Score > 0.6 validation
- [x] GitHub Models support
- [x] Documentation

---

**Good luck at the hackathon! 🚀**
