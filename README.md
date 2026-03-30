# LedgerShield

A state-of-the-art multimodal accounts payable audit environment built for the Meta OpenEnv Hackathon.

## What is LedgerShield?

LedgerShield is an OpenEnv-compatible environment that simulates a real-world accounts payable audit workflow. AI agents learn to:

- **Extract** invoice fields and line items from multimodal documents
- **Detect** discrepancies between purchase orders, receipts, and invoices
- **Identify** potential fraud indicators and duplicate payments
- **Apply** policy rules to determine correct payment decisions

## Project Structure

```
Meta-s-LedgerShield/
├── inference.py              # Baseline inference script
├── README.md                 # This file
├── envs/
│   └── ledgershield_env/
│       ├── openenv.yaml      # OpenEnv specification
│       ├── models.py         # Typed models (Action, Observation, State)
│       ├── client.py         # EnvClient for connecting to server
│       ├── openenv_compat.py # OpenEnv API compatibility layer
│       └── server/
│           ├── app.py        # FastAPI application
│           ├── environment.py # LedgerShieldEnvironment class
│           ├── grading.py     # Task graders and scoring
│           ├── tools.py       # Tool implementations
│           ├── schema.py      # Utility functions
│           ├── risk_rules.py  # Risk assessment rules
│           ├── data_loader.py # Fixture data loading
│           ├── Dockerfile     # Container definition
│           └── fixtures/      # Test data (cases, vendors, etc.)
├── tests/
│   ├── test_ledgershield_env.py  # Environment tests
│   └── test_api_smoke.py         # API smoke tests
└── pyproject.toml
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- Docker (for deployment)
- Hugging Face account (for deployment)

### Local Development

```bash
# Install dependencies
pip install -r envs/ledgershield_env/server/requirements.txt

# Run tests
python -m pytest tests/ -v

# Start local server
cd envs/ledgershield_env
uvicorn server.app:app --reload
```

### Run Inference

```bash
# Set environment variables
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="meta-llama/Llama-3.3-70B-Instruct"
export HF_TOKEN="your-hf-token"

# Run inference
python inference.py
```

## Tasks

| Task | Description | Actions Required |
|------|-------------|------------------|
| **task_a** | Invoice field extraction with evidence | lookup_vendor, ocr, submit_decision |
| **task_b** | Discrepancy detection | lookup_po, lookup_receipt, compare_bank_account |
| **task_c** | Fraud/duplicate detection | search_ledger, inspect_email_thread |
| **task_d** | Full policy compliance review | All tools + counterfactual reasoning |

## Action/Observation Spaces

### Actions (LedgerShieldAction)

```python
@dataclass
class LedgerShieldAction(Action):
    action_type: ActionType  # zoom, ocr, lookup_vendor, submit_decision, etc.
    payload: dict[str, Any]  # Tool-specific parameters
```

### Observations (LedgerShieldObservation)

```python
@dataclass
class LedgerShieldObservation(Observation):
    case_id: str
    task_type: str
    instruction: str
    visible_documents: list[dict]
    budget_remaining: float
    step_count: int
    last_tool_result: dict
    messages: list[str]
    allowed_actions: list[str]
    case_metadata: dict
```

## Grading

Each task has an agent grader that scores submissions 0.0–1.0:

- **task_a**: Field accuracy (45%), line items (30%), evidence (25%)
- **task_b**: Decision (35%), discrepancies (25%), policy (20%), evidence (20%)
- **task_c**: Decision (25%), duplicates (25%), fraud flags (35%), evidence (15%)
- **task_d**: Decision (25%), reasons (25%), policy (20%), evidence (20%), counterfactual (10%)

Budget efficiency penalties apply based on tool usage.

## Deployment

### Build Docker Image

```bash
docker build -t ledgershield:latest -f envs/ledgershield_env/server/Dockerfile .
```

### Push to Hugging Face Spaces

```bash
pip install openenv-core
openenv push
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_BASE_URL` | LLM API endpoint | `https://router.huggingface.co/v1` |
| `MODEL_NAME` | Model identifier | `meta-llama/Llama-3.3-70B-Instruct` |
| `HF_TOKEN` | Hugging Face API key | Required |
| `ENV_URL` | Environment server URL | `http://localhost:8000` |

## Team

- **Shreyas Biradar** (Team Lead)
- **Aryaman Pathak**
- **Hemant Gupta**

## License

MIT
