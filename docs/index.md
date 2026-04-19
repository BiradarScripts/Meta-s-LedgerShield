# LedgerShield Overview

LedgerShield is a high-stakes enterprise payment-integrity benchmark for AI agents. It models how an AP analyst or AP control tower agent investigates invoices, email threads, vendor records, policy rules, and ledger history before deciding whether payment is safe, risky, or fraudulent.

The benchmark now formalizes that loop as an **Adversarial Sequential Hypothesis Testing Game (ASHTG)**: the agent maintains a multi-hypothesis SPRT state, the environment ranks tools by Value of Information, the grader evaluates causal sufficiency and proper probability reports, and the watchdog commits to a Stackelberg-style audit strategy.

## Why LedgerShield Exists

Most finance-adjacent benchmarks stop at extraction or classification. Real accounts-payable risk is harder:

- the agent begins with partial information
- fraud signals are distributed across documents, history, and delayed artifacts
- the right next action matters as much as the final label
- unsafe `PAY` decisions can be far worse than over-cautious review
- adversarial pressure often arrives mid-episode, not only in the first prompt

LedgerShield measures all of that in one environment.

## Real-World Utility

The domain is intentionally grounded in a real operational loss category. The FBI IC3 2023 report states that business email compromise generated **21,489 complaints and more than $2.9 billion in reported losses** in 2023, making it one of the costliest internet crime categories tracked that year.

Source:

- [FBI IC3 2023 Internet Crime Report](https://www.ic3.gov/annualreport/reports/2023_ic3report.pdf)

That is why the benchmark emphasizes:

- AP inbox/BEC triage
- bank change verification
- callback controls
- duplicate and campaign reasoning
- evidence-backed escalation instead of vague “looks suspicious” answers
- SOX-style control discipline

## Benchmark Scope

### Public benchmark catalog

LedgerShield ships with 21 curated base cases:

| Task | Count | What it tests |
|---|---:|---|
| `task_a` | 4 | proof-carrying field extraction, multilingual documents, multi-currency invoices, IBAN/SWIFT artifacts |
| `task_b` | 5 | three-way match, missing receipts, quantity mismatch, tax discrepancy, safe release logic |
| `task_c` | 4 | duplicate detection, bank mismatch, cross-vendor fraud, approval-threshold evasion |
| `task_d` | 6 | BEC/AP inbox triage, workflow override, CEO fraud, benign-vs-adversarial email reasoning |
| `task_e` | 2 | multi-invoice campaign fraud and supply-chain-compromise APT scenarios |

### Generated suites

Beyond the curated base set, the repo can generate:

- challenge variants from hard benchmark cases
- holdout suites for robustness testing
- contrastive benign twins for calibration checks

With the current loader defaults, `load_all()` produces **45 total cases** locally:

- 21 benchmark cases
- 24 generated challenge variants

## Core Concepts

### Partial observability

Agents do not see the whole case upfront. The environment tracks:

- hidden risk signals
- delayed artifact reveals
- pending intervention events
- latent outcomes
- pressure-event injection
- campaign context and portfolio-level risk
- persistent institutional memory and loss ledger
- executable decision-certificate diagnostics

### Investigation tools

Agents gather evidence using tools such as:

- `ocr`, `zoom`, `get_doc_crop`
- `lookup_vendor`, `lookup_vendor_history`, `lookup_policy`
- `lookup_po`, `lookup_receipt`
- `search_ledger`
- `inspect_email_thread`
- `compare_bank_account`

### Interventions

Some evidence only appears after operational controls are triggered:

- `request_callback_verification`
- `request_bank_change_approval_chain`
- `request_po_reconciliation`
- `request_additional_receipt_evidence`
- `flag_duplicate_cluster_review`
- `route_to_security`
- `freeze_vendor_profile`
- `create_human_handoff`

### Proof-carrying outputs

The benchmark expects structured outputs, not just decisions. Depending on the task, strong submissions include:

- extracted invoice fields and line items
- `policy_checks`
- `reason_codes`
- `fraud_flags`
- `duplicate_links`
- `campaign_signals`
- `counterfactual`
- `evidence_map` with document/page/bbox/token grounding
- `decision_certificate`, a typed graph whose artifact, observation, hypothesis,
  policy, intervention, decision, and counterfactual nodes can be verified by
  the server.

### Institutional intelligence layer

LedgerShield now keeps a persistent institutional memory inside each environment
instance. Resets still load individual cases, but the environment also tracks
the surrounding AP week: queue depth, manual-review capacity, callback capacity,
vendor trust, attacker belief over weak controls, cumulative fraud loss,
released loss, delay hours, manual-review minutes, supplier friction, false
positives, and unsafe releases.

The default public track mode is `blind`, where ASHTG diagnostics such as SPRT
state, VoI tool rankings, and reward-machine progress are hidden from the
observation. Set `LEDGERSHIELD_TRACK_MODE=instrumented` when you want the
diagnostics view for debugging, evaluator inspection, or research iteration.
This keeps the benchmark-facing contract leakage-resistant while preserving a
richer diagnostics path for development.

### Agent capability tiers

The inference agent (`inference.py`) adapts its behavior based on a `ModelCapabilityProfile` derived from the model name:

<!-- sync:index-capability-table:start -->
| Tier | Capability score | Plan mode | Repair level | Budget bonus |
|---|---|---|---|---|
| Elite | >= 5.0 | `llm` | `partial` | +2 investigation, +2 intervention |
| Strong | >= 4.5 | `hybrid` | `partial` | +1 investigation, +1 intervention |
| Standard | < 4.5 | `llm` | `none` | baseline |
<!-- sync:index-capability-table:end -->

Weaker models receive stricter guardrail validation and more constrained evidence construction; stronger models get richer planning and per-case repair budgets. In the code, `llm` is the internal label for the LLM-first planning path.

### Composite signal derivation

The agent and server share improved signal-extraction logic:

- **Domain alignment** — sender domains are compared against vendor-approved domains using token overlap (not just exact match), catching spoofs like `ceo@acme-corp.com` vs `acme.com`.
- **Composite `bank_override_attempt`** — requires bank-change language *plus* a risk amplifier (domain mismatch, callback discouragement, policy override, or urgency). Isolated bank language no longer triggers fraud flags.
- **Constructive PAY evidence** — safe PAY decisions now carry verified-bank, verified-sender, or cleared-duplicates evidence instead of empty evidence maps, avoiding degenerate-evidence penalties.

## Environment Design Highlights

Recent environment upgrades visible in the implementation:

| Area | Current behavior |
|---|---|
| Reward shaping | PBRS with `SHAPING_SCALE = 0.35`, VoI-centered tool rewards, and reward-machine progress |
| Exploration bonus | information-gain bonus with `INFO_GAIN_BONUS = 0.08` |
| Episode semantics | Gymnasium-style distinction between `terminated` and `truncated` |
| Introspection | text `render()` summary for episode inspection |
| Formal contracts | `action_space()` and `observation_space()` class methods |
| Difficulty adaptation | curriculum module for tiered case selection |
| Institutional memory | persistent AP-week state, vendor trust, capacity, attacker belief, and loss ledger |
| Decision certificates | typed proof graph verification with support, grounding, stability, and minimality checks |
| Novelty | ASHTG hypothesis testing, proper scoring, causal sufficiency checks, Dec-POMDP watchdog mode, and proof-carrying institutional decisions |

## Scoring Philosophy

LedgerShield is trajectory-aware. The grader combines:

- task-specific correctness
- evidence quality
- investigation coverage
- intervention quality
- calibration
- efficiency
- downstream simulated outcomes
- pressure resistance on risky tasks
- callback interpretation and campaign reasoning where relevant

Important grading behaviors in the current codebase:

- semantic counterfactual scoring for Tasks D and E
- tighter penalties for degenerate or empty-evidence submissions (the `DEGENERATE_EVIDENCE_CAP = 0.25` cap is now applied correctly instead of collapsing to `0.0`)
- stricter unsafe-`PAY` penalties on Tasks C, D, and E
- contrastive adversarial-vs-benign evaluation support
- constructive evidence maps even for safe PAY decisions, avoiding degenerate caps on benign cases

## Quick Start

### Install

```bash
git clone https://github.com/BiradarScripts/Meta-s-LedgerShield.git
cd Meta-s-LedgerShield

python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements.txt
```

### Run the server

```bash
python -m server.app
```

### Run the submission agent

```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-5.4"
export HF_TOKEN="your_token"
export ENV_URL="http://127.0.0.1:8000"

python inference.py
```

### Generate evaluation artifacts

```bash
python benchmark_report.py --format markdown
python compare_models_live.py --models gpt-3.5-turbo,gpt-4o,gpt-5.4
python sync_benchmark_metadata.py
```

<!-- sync:index-live-comparison:start -->
## Live Comparison Snapshot

Generated on **April 10, 2026 (IST)** from `live_model_comparison.json`.

| Model | Average Score | Success Rate | Failed Cases |
|---|---:|---:|---:|
| `gpt-3.5-turbo` | 0.6965 | 38.1% | 13 |
| `gpt-4o` | 0.8947 | 90.5% | 2 |
| `gpt-5.4` | 0.9177 | 95.2% | 1 |

- Audit metrics are not present in this historical artifact. Rerun `compare_models_live.py` with the current code to populate certificate and institutional-loss columns.

- Capability ordering is monotonic across the compared models: `true`.
- Current frontier gap (`gpt-5.4` vs `gpt-4o`): `+0.0229` average score and `+4.8%` success rate.
- Refresh after rerunning the live comparison artifact:
```bash
python compare_models_live.py \
  --models gpt-3.5-turbo,gpt-4o,gpt-5.4 \
  --output live_model_comparison.json
python sync_benchmark_metadata.py
```
<!-- sync:index-live-comparison:end -->


## What To Read Next

- [`tasks.md`](./tasks.md) for task-by-task contracts and scoring
- [`api-reference.md`](./api-reference.md) for environment integration details
- [`architecture.md`](./architecture.md) for the hidden-state, grading, and generation pipeline
- [`development.md`](./development.md) for the detailed repo map and contributor workflow
- [`deployment.md`](./deployment.md) for running LedgerShield outside a local dev shell
- [`README.md`](../README.md) for the project overview, benchmark results, and upgrade snapshot
