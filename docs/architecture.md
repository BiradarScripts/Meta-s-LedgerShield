# Architecture

This document describes the LedgerShield system architecture, including component design, data flow, and the underlying formal model.

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Client Layer                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │  inference.py│  │  Custom Agent│  │   API Client │               │
│  │  (baseline)  │  │              │  │              │               │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │
└─────────┼──────────────────┼──────────────────┼─────────────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │ HTTP/REST
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Server Layer (FastAPI)                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      server/app.py                           │   │
│  │              FastAPI Application Entrypoint                  │   │
│  └────────────────────────┬────────────────────────────────────┘   │
│                           │                                        │
│  ┌────────────────────────▼────────────────────────────────────┐   │
│  │                  LedgerShieldEnvironment                     │   │
│  │              (server/environment.py)                         │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │   │
│  │  │  reset() │ │  step()  │ │  state() │ │public_   │       │   │
│  │  │          │ │          │ │          │ │state()   │       │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Core Systems                                     │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │ World State │  │   Tools     │  │   Grading   │  │  Outcome   │ │
│  │  Manager    │  │   Engine    │  │   Engine    │  │ Simulator  │ │
│  │             │  │             │  │             │  │            │ │
│  │- Hidden     │  │- OCR        │  │- Task       │  │- Payment   │ │
│  │  state       │  │- Lookup     │  │  scores     │  │  outcomes  │ │
│  │- Public     │  │- Search     │  │- Trajectory │  │- Risk      │ │
│  │  state       │  │- Compare    │  │  scores     │  │  metrics   │ │
│  │- Artifacts  │  │             │  │             │  │            │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Data Layer                                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │  Cases   │ │ Vendors  │ │    PO    │ │ Receipts │ │  Ledger  │   │
│  │  (JSON)  │ │  (JSON)  │ │(JSON)    │ │  (JSON)  │ │ (JSON)   │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                             │
│  │  Emails  │ │  Policy  │ │  Vendor  │                             │
│  │  (JSON)  │ │  (JSON)  │ │ History  │                             │
│  └──────────┘ └──────────┘ └──────────┘                             │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### 1. Client Layer

The client layer contains agent implementations that interact with the environment:

- **`inference.py`**: Baseline agent with deterministic policy
- **`client.py`**: HTTP client for environment interaction
- **`openenv_compat.py`**: OpenEnv compatibility layer

### 2. Server Layer

#### FastAPI Application (`server/app.py`)

Entry point that creates the FastAPI app with:
- Environment endpoints (`/reset`, `/step`, `/state`)
- Utility endpoints (`/health`, `/leaderboard`, `/benchmark-report`)
- OpenEnv compatibility middleware

#### Environment (`server/environment.py`)

Core environment class implementing the OpenEnv interface:

```python
class LedgerShieldEnvironment(Environment):
    def reset(self, seed=None, case_id=None) -> Observation
    def step(self, action) -> Observation
    def public_state(self) -> dict
```

Key responsibilities:
- Episode lifecycle management
- Action dispatch to tools
- State transitions
- Reward calculation
- Budget tracking

### 3. Core Systems

#### World State Manager (`server/world_state.py`)

Manages the separation between hidden and public state:

```python
# Hidden State (not visible to agent)
hidden_world = {
    "hidden_risk_signals": [...],
    "latent_outcomes": {...},
    "artifact_templates": {...},
    "pending_events": [...],
    "campaign_context": {...}
}

# Public State (visible to agent)
public_state = {
    "visible_doc_ids": [...],
    "revealed_artifact_ids": [...],
    "observed_risk_signals": [...],
    "budget_remaining": float,
    "step_count": int
}
```

#### Tools Engine (`server/tools.py`)

Investigation tools available to agents:

| Tool | Purpose | Cost |
|------|---------|------|
| `zoom` | Inspect document region | 0.20 |
| `ocr` | Extract text (fast/accurate) | 0.45/1.10 |
| `lookup_vendor` | Query vendor master | 0.20 |
| `search_ledger` | Find duplicates | 0.35 |
| `inspect_email_thread` | Analyze emails | 0.25 |
| `compare_bank_account` | Validate bank changes | 0.15 |

#### Grading Engine (`server/grading.py`, `server/trajectory_grading.py`)

Task-specific and trajectory-level scoring:

- **Task Scoring**: Accuracy metrics per task type
- **Trajectory Scoring**: Investigation quality, intervention quality, efficiency
- **Calibration**: Contrastive benign twin evaluation
- **Outcomes**: Downstream enterprise impact

#### Outcome Simulator (`server/outcome_simulator.py`)

Simulates downstream consequences of decisions:

| Outcome | Description |
|---------|-------------|
| `safe_payment_cleared` | Correct payment release |
| `unsafe_payment_released` | Fraudulent payment released |
| `fraud_prevented` | Escalation prevented loss |
| `manual_review_created` | Risk contained via review |
| `false_positive_operational_delay` | Clean payment delayed |
| `policy_breach` | Controls bypassed |

### 4. Data Layer

JSON fixtures provide test data:

- **`cases.json`**: Benchmark cases with gold labels
- **`vendors.json`**: Vendor master records
- **`po_records.json`**: Purchase orders
- **`receipts.json`**: Goods receipts
- **`ledger_index.json`**: Payment history
- **`email_threads.json`**: Email communications
- **`policy_rules.json`**: Policy definitions
- **`vendor_history.json`**: Historical changes

## Data Flow

### Episode Lifecycle

```
┌─────────┐     reset()      ┌──────────────────────────────────────┐
│  Start  │─────────────────▶│         Initialization               │
└─────────┘                  │  - Select case                       │
                             │  - Build hidden world                │
                             │  - Initialize public state           │
                             │  - Set budget/steps                  │
                             └──────────────────┬───────────────────┘
                                                │
                                                ▼
                             ┌──────────────────────────────────────┐
                             │       Return Initial Observation     │
                             │  - case_id                           │
                             │  - task_type                         │
                             │  - visible_documents                 │
                             │  - budget_remaining                  │
                             └──────────────────┬───────────────────┘
                                                │
                    ┌───────────────────────────┼───────────────────────────┐
                    │                           │                           │
                    ▼                           ▼                           ▼
           ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
           │Investigation│            │ Intervention│            │  Decision   │
           │   Action    │            │   Action    │            │             │
           └──────┬──────┘            └──────┬──────┘            └──────┬──────┘
                  │                          │                          │
                  ▼                          ▼                          ▼
           ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
           │  Dispatch   │            │  Apply      │            │   Grade     │
           │   Tool      │            │  Control    │            │ Submission  │
           └──────┬──────┘            └──────┬──────┘            └──────┬──────┘
                  │                          │                          │
                  ▼                          ▼                          ▼
           ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
           │Update State │            │   Queue     │            │   Simulate  │
           │ - observed  │            │   Artifact  │            │   Outcome   │
           │   signals   │            │             │            │             │
           │ - budget    │            │             │            │             │
           └──────┬──────┘            └──────┬──────┘            └──────┬──────┘
                  │                          │                          │
                  └──────────────────────────┼──────────────────────────┘
                                             │
                                             ▼
                             ┌──────────────────────────────────────┐
                             │        Return Step Result            │
                             │  - observation                       │
                             │  - reward                            │
                             │  - done                              │
                             │  - info                              │
                             └──────────────────┬───────────────────┘
                                                │
                             ┌──────────────────┴───────────────────┐
                             │                                      │
                             ▼                                      ▼
                    ┌─────────────┐                        ┌─────────────┐
                    │  done=True  │                        │  done=False │
                    │   (End)     │                        │   (Loop)    │
                    └─────────────┘                        └──────┬──────┘
                                                                  │
                                                                  └──────┐
                                                                         │
                                                    (Return to Step) ◀───┘
```

### Action Processing Flow

```
┌─────────────┐
│ Agent sends │
│   action    │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ environment.step │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────┐
│  Validate action │────▶│ Invalid:     │
│  in ALLOWED_     │     │ Return error │
│  ACTIONS         │     └──────────────┘
└────────┬─────────┘
         │ Valid
         ▼
┌──────────────────┐
│ Calculate cost   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Dispatch to:     │
│ - Tool handler   │
│ - Intervention   │
│   handler        │
│ - Decision       │
│   handler        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Process result   │
│ - Extract signals│
│ - Update state   │
│ - Check artifacts│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Calculate reward │
│ - Cost penalty   │
│ - Novel signals  │
│ - PBRS shaping   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Check terminal   │
│ - Max steps?     │
│ - Budget zero?   │
│ - Decision made? │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Return           │
│ observation,     │
│ reward, done,    │
│ info             │
└──────────────────┘
```

## Formal Model

### POMDP Specification

LedgerShield is modeled as a finite-horizon Partially Observable Markov Decision Process (POMDP):

$$
\mathcal{M} = \langle S, A, O, T, \Omega, R, b_0, H \rangle
$$

| Symbol | Definition |
|--------|------------|
| **S** | State space: hidden risk signals, intervention status, pending artifacts, callback state, pressure events |
| **A** | Action space: tools, interventions, submit_decision |
| **O** | Observation space: visible documents, revealed artifacts, risk snapshot, budget, step count |
| **T** | Transition: deterministic tool results + delayed artifact release + pressure event injection |
| **Ω** | Observation function: partial revelation of state |
| **R** | Reward: step costs + novel signal bonuses + PBRS + terminal score |
| **b₀** | Initial belief: case-conditioned distribution over hidden signals |
| **H** | Horizon: max_steps per episode |

### Potential-Based Reward Shaping (PBRS)

The shaping term follows Ng, Harada, and Russell (1999):

$$
F(s, a, s') = \gamma \Phi(s') - \Phi(s)
$$

Where:
- $\gamma = 0.98$ (shaping discount)
- $\Phi(s)$ = readiness potential (risk coverage, artifact coverage, pending resolution)
- Scale factor: 0.18

This ensures policy invariance while providing dense feedback.

### Dec-POMDP Extension

Callback verification introduces a second actor:

```
Agent (Investigator)          Vendor Simulator
        │                             │
        │── request_callback() ──────▶│
        │                             │
        │◀──── artifact_result ───────│
        │        (delayed)            │
```

The agent never observes:
- `vendor_compromised`
- `attacker_has_phone`

Must infer from callback response.

## State Management

### Hidden World State

Managed by `server/world_state.py`:

```python
@dataclass
class HiddenWorld:
    # Risk signals (never revealed directly)
    hidden_risk_signals: list[str]
    latent_fraud_indicators: dict
    
    # Artifacts (revealed via interventions)
    artifact_templates: dict[str, Artifact]
    pending_events: list[PendingEvent]
    
    # Outcomes (used for grading)
    outcome_map: dict[str, Outcome]
    
    # Campaign context (Task E)
    campaign_context: dict
    
    # Pressure events
    pressure_event_schedule: list[PressureEvent]
```

### Public State

Visible to agents:

```python
@dataclass
class LedgerShieldState:
    # Episode metadata
    episode_id: str
    case_id: str
    task_type: str
    
    # Resources
    budget_total: float
    budget_remaining: float
    max_steps: int
    step_count: int
    
    # Visibility
    visible_doc_ids: list[str]
    revealed_artifact_ids: list[str]
    
    # Investigation
    tool_trace: list[dict]
    trajectory: list[dict]
    interventions_taken: list[dict]
    observed_risk_signals: list[str]
    
    # Results
    final_score: float
    final_outcome: dict
    unsafe_outcome: bool
```

### State Transitions

```
┌──────────────┐     Tool Action      ┌──────────────┐
│    State     │────────────────────▶│    State'    │
│      t       │                     │     t+1      │
└──────────────┘                     └──────────────┘
       │                                    ▲
       │ Intervention   ┌──────────┐       │
       │ Action         │  Queue   │       │
       └───────────────▶│ Artifact │───────┘
                        │  Event   │
                        └──────────┘
                              │
                              │ After delay
                              ▼
                        ┌──────────┐
                        │  Reveal  │
                        │ Artifact │
                        └──────────┘
```

## Module Dependencies

```
server/app.py
    └─▶ server/environment.py
        ├─▶ server/world_state.py
        │   ├─▶ server/vendor_simulator.py
        │   └─▶ server/pressure_events.py
        ├─▶ server/tools.py
        │   └─▶ server/schema.py
        ├─▶ server/transition_engine.py
        ├─▶ server/grading.py
        │   ├─▶ server/trajectory_grading.py
        │   └─▶ server/vendor_simulator.py
        ├─▶ server/outcome_simulator.py
        ├─▶ server/risk_rules.py
        └─▶ server/data_loader.py

inference.py
    ├─▶ ledgershield_env.py
    │   └─▶ client.py
    └─▶ server/environment.py (local mode)

benchmark_report.py
    └─▶ server/case_factory.py
        └─▶ server/attack_library.py
```

## Performance Considerations

- **CPU-only**: No GPU required for environment server
- **Memory**: ~500MB baseline (fixture data in memory)
- **Latency**: <100ms per step (local deployment)
- **Throughput**: Supports multiple concurrent episodes
- **Determinism**: Fixed seed = reproducible results

## Security Model

- **No gold leakage**: Hidden state never exposed via API
- **Input validation**: All actions validated against schema
- **Budget enforcement**: Hard limits on investigation cost
- **Deterministic fixtures**: No external data dependencies
