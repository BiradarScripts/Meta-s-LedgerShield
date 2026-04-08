# LedgerShield Documentation

Welcome to the LedgerShield documentation. LedgerShield is a stateful, adversarial enterprise payment-integrity environment for training and evaluating AI agents in realistic high-stakes financial operations.

## What is LedgerShield?

LedgerShield models the complete accounts-payable control tower workflow where AI agents must investigate payment cases, detect fraud, and make evidence-backed decisions. Unlike static benchmarks that simply ask "can the model read this document?", LedgerShield asks:

> "Can the agent safely operate an enterprise payment-control workflow under uncertainty, with tools, budget limits, policy constraints, and adversarial pressure?"

## Why LedgerShield?

### The Problem with Traditional Benchmarks

| Benchmark Type | Tests | Missing |
|---------------|-------|---------|
| Static OCR | Document reading | State, safety semantics, decision pressure |
| Fraud Classification | Label assignment | Process quality, interventions |
| Document QA | Question answering | Operational consequences |
| Workflow Simulator | Following procedures | Adversarial realism, multi-modal evidence |

### LedgerShield's Approach

LedgerShield combines all these aspects into a unified environment:

- **Realistic Domain**: Enterprise AP/payment-integrity operations
- **Statefulness**: Hidden risk signals, revealed artifacts, intervention status
- **Trajectory Matters**: Investigation quality, intervention choice, efficiency all affect scoring
- **Adversarial Robustness**: Replayable attack patterns prevent overfitting
- **Enterprise Semantics**: Fraud prevention, policy compliance, operational continuity

## Core Concepts

### Partial Observability

The agent starts with only a partial view of each case:

- Visible documents (invoices, emails)
- Budget and step constraints
- Initial risk snapshot

The environment maintains hidden state including:
- Latent fraud signals
- Artifact templates
- Pending intervention results
- Downstream outcome maps

### Investigation Actions

Agents use tools to gather evidence:

- `ocr` - Extract text from documents
- `lookup_vendor` - Query vendor master data
- `search_ledger` - Find duplicate payments
- `inspect_email_thread` - Analyze email communications
- `compare_bank_account` - Validate bank account changes

Each action has a cost that consumes the investigation budget.

### Intervention Actions

Special actions that unlock additional evidence:

- `request_callback_verification` - Trigger vendor callback
- `freeze_vendor_profile` - Apply containment control
- `route_to_security` - Escalate suspicious cases
- `flag_duplicate_cluster_review` - Initiate duplicate review

Interventions often reveal artifacts that become available after a delay.

### Decision Space

The final decision must be one of:

| Decision | Use Case |
|----------|----------|
| `PAY` | Clean invoice, all checks pass |
| `HOLD` | Issues found, needs further review |
| `NEEDS_REVIEW` | Uncertain, requires human judgment |
| `ESCALATE_FRAUD` | High-risk, potential fraud detected |

### Grading

Scores combine multiple factors:

- **Task-specific metrics**: Field extraction accuracy, discrepancy detection
- **Investigation quality**: Coverage of risk signals
- **Intervention quality**: Appropriate use of controls
- **Calibration**: Avoiding false positives/negatives
- **Efficiency**: Budget usage and step count
- **Downstream outcomes**: Simulated enterprise impact

## Quick Start Guide

### 1. Installation

```bash
# Clone repository
git clone https://github.com/BiradarScripts/Meta-s-LedgerShield.git
cd Meta-s-LedgerShield

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
pip install -r requirements.txt
```

### 2. Start the Environment Server

```bash
python -m server.app
```

The server will start on `http://127.0.0.1:8000`.

### 3. Run the Baseline Agent

In a new terminal:

```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-5.4"
export HF_TOKEN="your_token_here"
export ENV_URL="http://127.0.0.1:8000"

python inference.py
```

### 4. Verify Installation

```bash
# Run tests
python -m pytest tests/ -q

# Validate OpenEnv compliance
openenv validate
```

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Agent         │────▶│   Environment    │────▶│   Tools         │
│                 │     │                  │     │                 │
│ - Investigates  │◀────│ - Maintains state│◀────│ - Query data    │
│ - Intervenes    │     │ - Applies costs  │     │ - Return evidence│
│ - Decides       │     │ - Scores results │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │   Grading        │
                        │                  │
                        │ - Task scores    │
                        │ - Trajectory     │
                        │ - Outcomes       │
                        └──────────────────┘
```

For detailed architecture documentation, see [Architecture](./architecture.md).

## API Overview

LedgerShield exposes a standard OpenEnv-compatible REST API:

```python
# Initialize episode
POST /reset
{"case_id": "CASE-D-001"}

# Take action
POST /step
{
  "action_type": "ocr",
  "payload": {"doc_id": "INV-D-001", "mode": "accurate"}
}

# Get state
GET /state
```

See [API Reference](./api-reference.md) for complete documentation.

## Task Overview

LedgerShield includes 5 task families:

| Task | Description | Key Skills |
|------|-------------|------------|
| **A** | Field Extraction | OCR, structured extraction, evidence grounding |
| **B** | Three-Way Match | PO/receipt reconciliation, policy checking |
| **C** | Fraud Triage | Duplicate detection, bank validation, escalation |
| **D** | AP Inbox Triage | Email analysis, spoof detection, multi-hop reasoning |
| **E** | Campaign Detection | Cross-invoice analysis, threshold evasion detection |

See [Task Reference](./tasks.md) for detailed descriptions.

## Next Steps

- Learn about [system architecture](./architecture.md)
- Explore the [API reference](./api-reference.md)
- Understand the [task suite](./tasks.md)
- Set up your [development environment](./development.md)
- Deploy to [production](./deployment.md)

## Resources

- [GitHub Repository](https://github.com/BiradarScripts/Meta-s-LedgerShield)
- [Issue Tracker](https://github.com/BiradarScripts/Meta-s-LedgerShield/issues)
- [OpenEnv Specification](https://github.com/openenv/spec)

## Getting Help

If you encounter issues:

1. Check the [API Reference](./api-reference.md) for endpoint details
2. Review [common issues](./development.md#troubleshooting) in the development guide
3. Search [existing issues](https://github.com/BiradarScripts/Meta-s-LedgerShield/issues)
4. Create a new issue with:
   - Environment details (Python version, OS)
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant logs
