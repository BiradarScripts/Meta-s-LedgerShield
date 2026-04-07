# API Reference

Complete reference for the LedgerShield REST API.

## Base URL

```
http://localhost:8000
```

## Content Type

All requests and responses use JSON:

```
Content-Type: application/json
```

## Endpoints

### Health Check

Check if the server is running.

```http
GET /health
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2026-04-07T10:30:00Z"
}
```

**Status Codes:**
- `200` - Server is healthy
- `503` - Server is unavailable

---

### Reset Episode

Initialize a new episode with the specified case.

```http
POST /reset
```

**Request Body:**

```json
{
  "case_id": "CASE-D-001"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `case_id` | string | Yes | Case identifier (e.g., "CASE-D-001") |
| `seed` | integer | No | Random seed for reproducibility |

**Response:**

```json
{
  "case_id": "CASE-D-001",
  "task_type": "task_d",
  "instruction": "Investigate this AP inbox incident...",
  "visible_documents": [
    {
      "doc_id": "INV-D-001",
      "doc_type": "invoice",
      "thumbnail": "thumbnail::INV-D-001",
      "page_count": 1,
      "language": "en",
      "available_views": ["thumbnail", "zoom", "get_doc_crop", "ocr_fast", "ocr_accurate"]
    }
  ],
  "revealed_artifacts": [],
  "pending_events": [],
  "budget_remaining": 16.0,
  "budget_total": 16.0,
  "step_count": 0,
  "max_steps": 18,
  "case_clock": 0,
  "risk_snapshot": {
    "risk_level": "medium",
    "observed_signals": []
  },
  "investigation_status": {
    "tools_used": 0,
    "interventions_taken": 0,
    "artifacts_revealed": 0,
    "budget_used": 0.0
  },
  "last_tool_result": {},
  "messages": ["Loaded case CASE-D-001"],
  "allowed_actions": ["zoom", "get_doc_crop", "ocr", ...],
  "available_interventions": ["request_callback_verification", "freeze_vendor_profile", ...],
  "case_metadata": {
    "task_label": "ap_inbox_triage",
    "due_date_days": 7
  },
  "portfolio_context": {}
}
```

**Status Codes:**
- `200` - Episode initialized successfully
- `400` - Invalid case_id
- `500` - Server error

---

### Execute Action

Execute an action in the current episode.

```http
POST /step
```

**Request Body:**

```json
{
  "action_type": "ocr",
  "payload": {
    "doc_id": "INV-D-001",
    "mode": "accurate"
  }
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action_type` | string | Yes | Action to execute (see [Action Types](#action-types)) |
| `payload` | object | Yes | Action-specific parameters |

**Response:**

```json
{
  "observation": {
    "case_id": "CASE-D-001",
    "task_type": "task_d",
    "instruction": "Investigate this AP inbox incident...",
    "visible_documents": [...],
    "revealed_artifacts": [],
    "pending_events": [],
    "budget_remaining": 14.9,
    "budget_total": 16.0,
    "step_count": 1,
    "max_steps": 18,
    "case_clock": 1,
    "risk_snapshot": {
      "risk_level": "medium",
      "observed_signals": []
    },
    "investigation_status": {
      "tools_used": 1,
      "interventions_taken": 0,
      "artifacts_revealed": 0,
      "budget_used": 1.1
    },
    "last_tool_result": {
      "tool_name": "ocr",
      "success": true,
      "doc_id": "INV-D-001",
      "mode": "accurate",
      "scope": "document",
      "tokens": [...],
      "text_preview": "Invoice #...",
      "message": "Returned accurate OCR.",
      "cost": 1.1,
      "reward_model": {
        "value": -0.055,
        "terminal": false,
        "components": {
          "cost_penalty": -0.055
        },
        "metadata": {
          "action_type": "ocr",
          "success": true
        }
      }
    },
    "messages": ["Returned accurate OCR."],
    "allowed_actions": [...],
    "available_interventions": [...],
    "case_metadata": {...},
    "portfolio_context": {}
  },
  "reward": -0.055,
  "done": false,
  "info": {
    "tool_name": "ocr",
    "success": true,
    "reward_model": {...}
  }
}
```

**Status Codes:**
- `200` - Action executed successfully
- `400` - Invalid action or payload
- `409` - Episode not initialized (call /reset first)
- `500` - Server error

---

### Get State

Retrieve the current environment state.

```http
GET /state
```

**Response:**

Returns the same observation structure as `/reset` and `/step`.

---

### Get Leaderboard

Retrieve the latest benchmark results.

```http
GET /leaderboard
```

**Response:**

```json
{
  "benchmark": "ledgershield",
  "timestamp": "2026-04-07T10:30:00Z",
  "results": [
    {
      "case_id": "CASE-A-001",
      "task_type": "task_a",
      "score": 0.998,
      "steps": 5,
      "success": true
    },
    ...
  ],
  "summary": {
    "mean_score": 0.969,
    "total_cases": 12,
    "pass_rate": 1.0
  }
}
```

---

### Get Benchmark Report

Retrieve detailed benchmark report.

```http
GET /benchmark-report
```

**Response:**

```json
{
  "benchmark": "ledgershield-v3",
  "generated_at": "2026-04-07T10:30:00Z",
  "public_cases": {
    "mean_score": 0.9688,
    "pass_at_threshold": 1.0
  },
  "holdout_cases": {
    "mean_score": 0.6621,
    "pass_at_threshold": 0.619
  },
  "case_results": [...]
}
```

## Action Types

### Investigation Actions

| Action | Description | Cost | Payload |
|--------|-------------|------|---------|
| `zoom` | Inspect document region | 0.20 | `{"doc_id": "...", "page": 1, "bbox": [x1, y1, x2, y2]}` |
| `get_doc_crop` | Get cropped region | 0.20 | `{"doc_id": "...", "page": 1, "bbox": [x1, y1, x2, y2]}` |
| `ocr` | Extract text from document | 0.45 (fast) / 1.10 (accurate) | `{"doc_id": "...", "mode": "fast"\|"accurate", "page"?: int, "bbox"?: [...]}` |
| `lookup_vendor` | Query vendor master | 0.20 | `{"vendor_key": "..."}` |
| `lookup_vendor_history` | Get vendor change history | 0.25 | `{"vendor_key": "..."}` |
| `lookup_policy` | Retrieve policy rules | 0.15 | `{}` or `{"policy_id": "..."}` |
| `lookup_po` | Load purchase order | 0.20 | `{"po_id": "..."}` |
| `lookup_receipt` | Load goods receipt | 0.20 | `{"receipt_id": "..."}` |
| `search_ledger` | Search for duplicates | 0.35 | `{"vendor_key": "...", "invoice_number": "...", "amount": float}` |
| `inspect_email_thread` | Analyze email thread | 0.25 | `{"thread_id": "..."}` |
| `compare_bank_account` | Validate bank account | 0.15 | `{"vendor_key": "...", "proposed_bank_account": "..."}` |

### Intervention Actions

| Action | Description | Cost | Payload |
|--------|-------------|------|---------|
| `request_callback_verification` | Request vendor callback | 0.40 | `{}` |
| `freeze_vendor_profile` | Freeze vendor account | 0.20 | `{}` |
| `request_bank_change_approval_chain` | Request bank change approval | 0.30 | `{}` |
| `request_po_reconciliation` | Request PO reconciliation | 0.30 | `{}` |
| `request_additional_receipt_evidence` | Request additional receipts | 0.25 | `{}` |
| `route_to_procurement` | Route to procurement | 0.15 | `{}` |
| `route_to_security` | Route to security | 0.20 | `{}` |
| `flag_duplicate_cluster_review` | Flag for duplicate review | 0.25 | `{}` |
| `create_human_handoff` | Create handoff packet | 0.20 | `{"summary": "...", "recommended_next_step": "...", "confidence": float}` |

### Terminal Action

| Action | Description | Cost | Payload |
|--------|-------------|------|---------|
| `submit_decision` | Submit final decision | 0.0 | See [Decision Payload](#decision-payload) |

## Decision Payload

When submitting a decision via `submit_decision`:

```json
{
  "action_type": "submit_decision",
  "payload": {
    "decision": "ESCALATE_FRAUD",
    "confidence": 0.95,
    "extracted_fields": {
      "vendor_name": "Acme Corp",
      "invoice_number": "INV-001",
      "invoice_date": "2026-04-01",
      "total": 5000.00,
      "currency": "USD"
    },
    "line_items": [
      {
        "description": "Consulting services",
        "qty": 10,
        "unit_price": 500.00,
        "line_total": 5000.00
      }
    ],
    "discrepancies": ["price_mismatch"],
    "duplicate_links": ["LED-001"],
    "fraud_flags": ["bank_override_attempt", "sender_domain_spoof"],
    "reason_codes": ["bank_override_attempt", "approval_threshold_evasion"],
    "policy_checks": {
      "three_way_match": "fail",
      "bank_change_verification": "fail",
      "duplicate_check": "fail",
      "approval_threshold_check": "fail"
    },
    "evidence_map": {
      "bank_override_attempt": {
        "doc_id": "INV-D-001",
        "page": 1,
        "bbox": [100, 200, 300, 250],
        "token_ids": ["tok_1", "tok_2"]
      }
    },
    "counterfactual": "Would PAY if sender domain matched and bank account was verified.",
    "notes": "Multiple risk signals detected.",
    "recommended_next_action": "manual_review",
    "handoff_packet": {
      "summary": "High-risk case with multiple fraud indicators.",
      "recommended_next_step": "fraud_investigation",
      "confidence": 0.95
    },
    "intervention_log": [
      {"action": "request_callback_verification", "step": 5}
    ],
    "campaign_signals": ["shared_bank_account", "coordinated_timing"],
    "cross_invoice_links": ["INV-D-001", "INV-D-002"]
  }
}
```

**Decision Values:**
- `PAY` - Release payment
- `HOLD` - Hold for review
- `NEEDS_REVIEW` - Escalate for human review
- `ESCALATE_FRAUD` - Escalate as potential fraud

## Data Models

### LedgerShieldObservation

```python
@dataclass
class LedgerShieldObservation:
    case_id: str                    # Case identifier
    task_type: str                  # Task family (task_a..task_e)
    instruction: str                # Task instructions
    visible_documents: List[dict]   # Available documents
    revealed_artifacts: List[dict]  # Unlocked artifacts
    pending_events: List[dict]      # Scheduled events
    budget_remaining: float         # Remaining budget
    budget_total: float             # Initial budget
    step_count: int                 # Current step
    max_steps: int                  # Step limit
    case_clock: int                 # Case time counter
    risk_snapshot: dict             # Risk telemetry
    investigation_status: dict      # Investigation metrics
    last_tool_result: dict          # Last action result
    messages: List[str]             # Status messages
    allowed_actions: List[str]      # Available actions
    available_interventions: List[str]  # Available interventions
    case_metadata: dict             # Case metadata
    portfolio_context: dict         # Campaign context
```

### LedgerShieldAction

```python
@dataclass
class LedgerShieldAction:
    action_type: str        # Action name
    payload: dict          # Action parameters
```

### LedgerShieldReward

```python
class LedgerShieldReward(BaseModel):
    value: float           # Reward value
    terminal: bool         # Is terminal reward
    components: dict       # Reward breakdown
    metadata: dict         # Context
```

### StepResult

```python
@dataclass
class StepResult:
    observation: LedgerShieldObservation
    reward: float
    done: bool
    info: dict
```

## Error Handling

### Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "INVALID_ACTION",
    "message": "Action type 'invalid_action' is not allowed",
    "details": {}
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_CASE_ID` | 400 | Case not found |
| `INVALID_ACTION` | 400 | Action not in allowed list |
| `INVALID_DECISION` | 400 | Decision not in allowed values |
| `EPISODE_NOT_INITIALIZED` | 409 | Call /reset first |
| `BUDGET_EXHAUSTED` | 400 | No budget remaining |
| `MAX_STEPS_REACHED` | 400 | Step limit exceeded |
| `INTERNAL_ERROR` | 500 | Server error |

## Rate Limiting

The API does not implement rate limiting, but each episode has:
- **Budget limit**: Total investigation budget per case
- **Step limit**: Maximum actions per episode

## Example Usage

### Complete Episode Flow

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Reset episode
response = requests.post(f"{BASE_URL}/reset", json={"case_id": "CASE-D-001"})
obs = response.json()

# 2. Get invoice document ID
invoice_doc = next(d for d in obs["visible_documents"] if d["doc_type"] == "invoice")
doc_id = invoice_doc["doc_id"]

# 3. OCR the invoice
response = requests.post(f"{BASE_URL}/step", json={
    "action_type": "ocr",
    "payload": {"doc_id": doc_id, "mode": "accurate"}
})
result = response.json()
obs = result["observation"]

# 4. Inspect email thread
email_doc = next(d for d in obs["visible_documents"] if d["doc_type"] == "email")
response = requests.post(f"{BASE_URL}/step", json={
    "action_type": "inspect_email_thread",
    "payload": {"thread_id": email_doc["doc_id"]}
})

# 5. Request callback verification
response = requests.post(f"{BASE_URL}/step", json={
    "action_type": "request_callback_verification",
    "payload": {}
})

# 6. Submit decision
response = requests.post(f"{BASE_URL}/step", json={
    "action_type": "submit_decision",
    "payload": {
        "decision": "ESCALATE_FRAUD",
        "confidence": 0.95,
        "reason_codes": ["bank_override_attempt", "sender_domain_spoof"],
        "evidence_map": {...}
    }
})
final = response.json()
print(f"Final score: {final['observation']['last_tool_result']['final_score']}")
```

## WebSocket Support

Currently, LedgerShield uses HTTP REST API only. WebSocket support is not implemented.

## Authentication

The LedgerShield environment server does not require authentication. Authentication is handled at the client level when calling LLM APIs (e.g., Hugging Face, OpenAI).

## Versioning

API version is tied to the LedgerShield package version. The current version is available in the `/health` endpoint response.

## OpenEnv Compatibility

LedgerShield implements the OpenEnv standard API:

- `POST /reset` - Initialize episode
- `POST /step` - Execute action
- `GET /state` - Get current state
- `GET /health` - Health check

Additional endpoints:
- `GET /leaderboard` - Benchmark results
- `GET /benchmark-report` - Detailed report

See [OpenEnv Specification](https://github.com/openenv/spec) for standard compliance details.
