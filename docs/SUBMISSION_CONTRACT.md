# LedgerShield v2 Round 2 Submission Contract

**Locked as of:** 2026-04-20  
**Project:** LedgerShield v2  
**Theme:** World Modeling — Professional Tasks  
**Subtheme:** Long-Horizon Planning & Instruction Following

---

## 1. Problem Statement

**LedgerShield v2 asks:** Can an AI agent operate a defensible enterprise accounts-payable (AP) control regime under partial observability, delayed evidence, adversarial pressure, and portfolio-level capacity constraints?

**Why it matters:**
- Business email compromise (BEC) generated $2.9B in reported losses in 2023 alone (FBI IC3 2023)
- Enterprise fraud is not one-shot classification; it is a sustained investigation under uncertainty and time pressure
- Real controls must resist both random false positives and targeted attacker adaptation
- Agents must calibrate confidence, understand evidence quality, and know when to escalate

**Scope:**
- Domain: Enterprise accounts-payable workflow, payment-fraud prevention, AP inbox triage
- Agents operate in a partial-information POMDP with institutional memory, callback verification, procurement review, security escalation, and human handoff
- Success requires investigation strategy, evidence evaluation, causal reasoning, and robust decision-making

---

## 2. Environment

**Type:** Partially Observable Markov Decision Process (POMDP)  
**Runtime:** FastAPI-based OpenEnv-compatible environment (server/app.py)  
**Observation Mode:** Blind by default (case_metadata hidden until callback verification)

### Observation Structure (Blind Mode)
```
{
  "case_id": str,              # Hidden until callback reveal
  "task_type": "task_a" | ... | "task_e",
  "instruction": str,
  "visible_documents": [...]   # Subset of full case; hidden docs revealed via tools
  "budget_remaining": float,
  "step_count": int,
  "last_tool_result": {...},
  "allowed_actions": [...],
  "sprt_state": {...},         # Public belief state for active case
  "institutional_memory": {...} # Cross-case portfolio memory
}
```

### Action Space
- **Investigation tools:** zoom, ocr, get_doc_crop, lookup_vendor, lookup_vendor_history, lookup_policy, lookup_po, lookup_receipt, search_ledger, inspect_email_thread, compare_bank_account
- **Interventions:** request_callback_verification, freeze_vendor_profile, request_bank_change_approval_chain, request_po_reconciliation, request_additional_receipt_evidence, route_to_procurement, route_to_security, flag_duplicate_cluster_review, create_human_handoff
- **Terminal action:** submit_decision (with structured payload including reason codes, policy checks, evidence map, decision certificate)

### Reward Shaping
Rewards are derived from **Value of Information (VoI)** over SPRT belief state. Grading uses **strictly proper scoring rules** and causal grading.

---

## 3. Agent Capabilities

The environment supports three agent capability tiers (defined by `ModelCapabilityProfile`):

| Tier | Capability Score | Plan Mode | Repair Level | Budget Bonus |
|---|---|---|---|---|
| Elite | >= 5.0 | `llm` | `partial` | +2 investigation, +2 intervention |
| Strong | >= 4.5 | `hybrid` | `partial` | +1 investigation, +1 intervention |
| Standard | < 4.5 | `llm` | `none` | baseline |

Agents are expected to:
1. Plan investigation strategy based on available budget and tool utility
2. Evaluate evidence quality and update belief over fraud hypotheses
3. Use interventions to mitigate risk (callback verification, vendor freeze, human review)
4. Submit a structured decision with causal grounding and audit trail
5. Tolerate delayed evidence and mid-episode attacker adaptation

---

## 4. Tasks

LedgerShield v2 uses 5 task families across 21 curated benchmark cases:

| Task | Count | Focus | Mechanism |
|---|---|---|---|
| Task A | 4 | Proof-carrying invoice extraction | Document authenticity, multilingual artifacts |
| Task B | 5 | Three-way match & discrepancies | Receipt gaps, quantity/tax mismatches |
| Task C | 4 | Duplicate detection | Cross-vendor fraud, threshold evasion |
| Task D | 6 | AP inbox / BEC triage | Email compromise, workflow override |
| Task E | 2 | Coordinated campaigns | Supply-chain APT, multi-invoice tactics |

**Latent Mechanism Schema:** 8 dimensions per case (`attack_family`, `compromise_channel`, `pressure_profile`, `control_weakness`, `vendor_history_state`, `bank_adjustment_state`, `campaign_linkage`, `portfolio_context`).

---

## 5. Reward Model / Evaluation Logic

### Headline Metrics
1. **`control_satisfied_resolution` (CSR)**
   - Case was correct, policy-complete, grounded, certificate-supported, and free of unsafe shortcuts
   - Range: 0.0 to 1.0

2. **`institutional_utility`**
   - Institution-level value after fraud loss, unsafe-release cost, review burn, supplier friction, and auditability
   - Range: unbounded (can go negative if severe failures)

3. **`unsafe_release_rate`**
   - Fraction of cases where agent released money unsafely
   - Range: 0.0 to 1.0

4. **`certificate_validity_rate`**
   - Fraction of submitted decisions with valid, verifiable decision certificates
   - Range: 0.0 to 1.0

### Grading Components
- **Causal grading:** Uses Pearl structural causal models to check support relationships between evidence, hypotheses, and decision
- **Proper scoring:** Strictly proper scoring over latent hypotheses; agents cannot game scores by overconfidence
- **Counterfactual safety:** Checks whether decision would remain correct under plausible alternative evidence

### Official Tracks (Evaluation Modes)
1. **Case Track:** Single-case control performance (all 21 curated cases are evaluated; 15 cases have `primary_track=case`)
2. **Adversarial Data Track:** Robustness to deceptive content (10 cases carry this official track; 4 cases have `primary_track=adversarial`)
3. **Portfolio Track:** AP-week utility under queue pressure and finite review capacity (8 cases carry this official track; evaluation runs over 5 fixed portfolio sequences)

---

## 6. Post-Training / Self-Improvement Strategy

### Supervised Fine-Tuning (SFT)
- Training data: 21 curated benchmark cases → ~21 trajectory examples → SFT dataset
- Model: Small language model (Qwen 2.5-0.5B as demo baseline)
- Framework: TRL (Transformers Reinforcement Learning) with LoRA fine-tuning
- Expected improvement: Baseline → +10-20% on case accuracy through policy learning

### Institutional Memory Fine-Tuning
- Agents can learn cross-case patterns (vendor history, attack signatures, control weaknesses)
- Persistent memory layer allows Portfolio Track to show emergent learning

### Holdout & Contrastive Evaluation
- Mechanism-aware holdouts test generalization beyond curated cases
- Contrastive benign twins (mechanically similar but clean cases) test false-positive control

---

## Narrative Lock

**The One-Line Narrative:**

> LedgerShield v2 is a benchmark for whether an AI agent can operate a defensible enterprise AP control regime under partial observability, delayed evidence, adversarial pressure, and portfolio-level constraints.

This narrative appears consistently in:
- README (opening)
- Benchmark card (executive summary)
- Demo script (one-liner)
- Mini-blog (hook)
- Pitch (headline)

---

## Consistency Checklist

- [x] Project name: LedgerShield v2 (locked across README, openenv.yaml, benchmark card, demo script)
- [x] Primary theme: World Modeling — Professional Tasks (locked in openenv.yaml, README)
- [x] Secondary theme: Long-Horizon Planning & Instruction Following (locked in openenv.yaml, README)
- [x] 6 Round 2 fields defined above
- [x] One-line narrative locked and used consistently

---

## How This Contract Is Maintained

1. All public-facing docs (README, benchmark-card, demo-script, mini-blog) reference this contract
2. If a change is needed, update THIS document first, then sync all derived assets
3. The submission will include a link to this locked contract

---

**Signed off:** Submitted for LedgerShield v2 Round 2  
**Date:** 2026-04-20
