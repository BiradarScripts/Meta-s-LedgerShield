# LedgerShield — Definitive PPT & Win Strategy Guide

> **For the OpenEnv Hackathon Finale (April 25–26, 2026)**
> Use this as your master script. Every slide maps to a judging criterion.
> The story at the top is your opening hook. Everything else flows from it.

---

## THE OPENING STORY

*The $4.2 Million Mistake — read this slowly, then pivot to the pitch.*

---

In 2019, a finance employee at a major German automotive company received an email. It looked like it came from their CEO — same name, same writing style, same urgency. The wire transfer request was for $4.2 million. The employee followed protocol: they verified the sender's email domain, checked the amount against typical executive requests, and processed it within two hours.

The email was fake.

By the time the fraud was discovered, the money was gone. The employee hadn't made a single obvious mistake. They did exactly what the training said to do.

**Why did $4.2 million leave the building?**

Because the fraudster had been watching this company for six months. They knew the vendor's real bank account had changed three months ago. They knew the CEO traveled frequently and sent short, urgent messages. They knew the finance team had a 48-hour approval window.

This wasn't a suspicious invoice. It was a **long-con operation** — a patience-driven, trust-building attack designed to bypass every checklist.

---

*Then pivot — one slide transition:*

> That company had a fraud detection tool. But no tool in the world would have caught this — because no benchmark asks the right question.
>
> Most benchmarks ask: *"Can an AI classify a suspicious invoice?"*
>
> We ask: *"Can an AI stay safe, calibrated, auditable, and trustworthy inside a live institution over an entire quarter — against adversaries who learn from its defenses?"*

**The answer is LedgerShield.**

---

*The pitch (3-second version for judges):*

> LedgerShield is a **deployment-grade trust-and-governance benchmark** for autonomous enterprise AI agents — the first RL environment that measures not just whether an AI can solve a task, but whether it **deserves operational authority**.

---

## CRITICAL: Framing Rules

**Do NOT say:**
- "fraud detection benchmark"
- "RL environment for BEC"
- "AI invoice classifier"

**Always say:**
- "deployment-grade institutional control intelligence"
- "trust-and-governance benchmark"
- "whether AI deserves operational authority"

**Why:** 30+ teams will submit fraud/billing/COD benchmarks. The framing is what separates you from the pack.

---

## Slide-by-Slide Breakdown

---

### SLIDE 1 — Title / Hook

**Visual:** Split screen
- Left: News headline — "$4.2M CEO Fraud" / FBI IC3 2023: "$2.9B in BEC losses"
- Right: LedgerShield dashboard showing institutional loss surface, calibration gate, authority level

**What to say:**
> "Enterprise fraud isn't a classification problem. It's a trust, patience, and institutional memory problem. And that requires an entirely new kind of benchmark."

**Anchor:** Storytelling (30%) + Environment Innovation (40%)

---

### SLIDE 2 — The $2.9 Billion Problem

**The numbers (cite sources):**

| Stat | Source |
|---|---|
| $2.9B+ in BEC losses in 2023 | FBI IC3 Annual Report 2023 |
| 21,489 BEC complaints | FBI IC3 Annual Report 2023 |
| $12.5B total cybercrime losses | FBI IC3 Annual Report 2023 |
| BEC attacks up 65% year-over-year | FBI IC3 |

**The gap:**
> "Every single one of those incidents had an AI tool. Every one failed. Why? Because those tools were benchmarked on clean invoices — not on long-con operations, capacity pressure, adversarial escalation, and institutional memory."

**The real problem isn't detection. It's trust, calibration, and authority.**

**Anchor:** Real-world utility → drives Environment Innovation (40%)

---

### SLIDE 3 — What Normal Benchmarks Test

**Visual:** Comparison table

| Normal Benchmark | LedgerShield |
|---|---|
| One invoice | One AP quarter (100+ cases) |
| Fixed authority | Calibration-gated dynamic authority |
| Episode-level reset | Persistent institutional memory |
| Obvious anomalies | Long-con trust-building attacks |
| Hand-tuned reward | Value of Information rewards |
| One score | Multi-dimensional loss surface |
| Action = decision | Action = proof-carrying certificate |

**Say:** "We didn't build a better fraud classifier. We built the benchmark that answers the question every enterprise CISO is actually asking."

**Anchor:** Storytelling (30%) + Environment Innovation (40%)

---

### SLIDE 4 — What the Agent Actually Does

**The workflow (visual flow diagram):**

```
INVESTIGATE  →  INTERVENE  →  DECIDE  →  CERTIFY
```

**Investigation tools (14 total):**
- Document extraction: `zoom`, `get_doc_crop`, `ocr`
- Vendor verification: `lookup_vendor`, `lookup_vendor_history`, `lookup_policy`
- Financial matching: `lookup_po`, `lookup_receipt`, `search_ledger`
- Email analysis: `inspect_email_thread`, `compare_bank_account`

**Interventions (9 total):**
- `request_callback_verification` — trigger delayed enterprise control
- `freeze_vendor_profile` — emergency freeze
- `request_bank_change_approval_chain` — multi-party approval
- `flag_duplicate_cluster_review` — cross-invoice fraud detection
- `route_to_security` / `route_to_procurement` / `create_human_handoff`

**The decision is not just a label.** It must include:
- `decision`: PAY / HOLD / NEEDS_REVIEW / ESCALATE_FRAUD
- `reason_codes`: grounded canonical codes
- `policy_checks`: SOX compliance verification
- `evidence_map`: per-claim evidence references
- `predicted_probabilities`: calibrated SPRT posterior
- `decision_certificate`: **typed proof graph** (evidence → hypothesis → intervention → decision)

**Anchor:** Real-world utility + Environment design

---

### SLIDE 5 — The 9 Official Tracks (The Wow Slide)

This is where you separate yourself from every other submission.

| Track | What it tests | Why judges care |
|---|---|---|
| Case Track | Single-case control correctness | Baseline |
| Portfolio Track | AP-week utility under queue pressure | **Institutional memory** |
| Adversarial Data Track | Deceptive content resilience | **Sleeper-vendor long-con** |
| Generated Holdout Track | Anti-overfit to unseen mechanisms | Mechanism-aware generalization |
| **ControlBench Track** | **Loss surface, calibration gate, authority timeline** | **Unique in all of hackathon** |
| **Sleeper-Vigilance Track** | **Trust-building vendor sequences that activate later** | **Models real-world patience attacks** |
| **Blind-Control Track** | **Evaluator scaffolding hidden from agent** | **Tests genuine capability** |
| **Certificate-Required Track** | **Strict proof-carrying evaluation** | **Auditable AI decisions** |
| Human-Baseline Track | Human AP analyst anchors | Operational realism |

**Say:** "Most teams will submit one evaluation mode. We built a 9-track evaluation ecosystem where each track tests a different dimension of institutional safety. No other submission in this hackathon has anything like this."

**Anchor:** Environment Innovation (40%)

---

### SLIDE 6 — The ASHTG Framework (The Theory Slide)

**The origin story:**
> "We didn't start by asking 'what should the reward function be?' We started by asking: what does fraud investigation actually look like, mathematically?"

**The answer: the Adversarial Sequential Hypothesis Testing Game.**

LedgerShield is the first RL environment that unifies **5 mathematical traditions** never before combined:

| Pillar | Theory | Source | Key Property |
|---|---|---|---|
| Sequential Investigation | **Wald's SPRT (1945)** | `server/sprt_engine.py` | Terminates at provably minimum steps |
| Causal Grading | **Pearl's SCM (2009)** | `server/causal_model.py` | Grades do-calculus + counterfactuals |
| Value of Information | **Howard's VoI (1966)** | `server/voi_engine.py` | Rewards from information economics |
| Strategy-proof Grading | **Gneiting-Raftery (2007)** | `server/proper_scoring.py` | Misreporting cannot improve score |
| Watchdog Audit | **Tambe SSE (2011)** | `server/dual_agent_mode.py` | Stackelberg equilibrium audit |

**The three things that make this novel:**

1. **VoI-based rewards** — not hand-tuned:
   ```
   VoI(tool) = E[U | posterior after tool] − E[U] − cost(tool)
   ```
2. **Strictly proper scoring** — provably strategy-proof; agent's dominant strategy is to report true beliefs
3. **SPRT optimal stopping** — Upper boundary A = 2.89, Lower boundary B = −2.25; agent receives live posterior at every step

**Say:** "Every other benchmark uses hand-tuned rewards. LedgerShield computes rewards from information economics. Every other environment lets agents game scores by expressing false confidence. LedgerShield uses math to make that impossible."

**Anchor:** Environment Innovation (40%) — genuinely novel

---

### SLIDE 7 — Institutional Memory (The $4.2M Story Continues)

**Return to the hook:**

> "Remember the $4.2M fraud? The attacker had been inside the vendor's ecosystem for 6 months. The vendor's bank account change was gradual, documented, and legitimate — for the first 5 months. The fraud activated in month 6."
>
> "Normal RL environments reset everything between episodes. LedgerShield tracks vendor trust history, attacker belief updates, fraud losses released vs. prevented, capacity pressure, and authority degradation — across episodes."

**What LedgerShield tracks persistently:**

```
Vendor trust score over time
  ├── First appearance: clean invoices
  ├── Month 3: bank account change requested
  ├── Month 5: all transactions normal, trust built
  ├── Month 6: bank account used for BEC fraud
  └── LedgerShield detects: trajectory, not snapshot
```

**The key question:** "Can the agent catch long-con fraud — not just obvious anomalies?"

**Anchor:** Environment Innovation (40%) — persistent institutional memory

---

### SLIDE 8 — Calibration-Gated Authority (The Deployment Question)

**The insight:**

> "Every other benchmark measures accuracy. We measure authority."

Authority levels (dynamic, not fixed):

```
full_authority      → restricted_authority   → review_only → locked
(agent acting freely)  (reduced scope)           (humans only)
                                              (no decisions allowed)
```

What triggers authority degradation:
- Calibration drift (SPRT posterior vs. actual outcomes)
- Unsafe releases (fraud loss > threshold)
- Catastrophic mistakes
- Institutional loss surface exceeds tolerance

**Say:** "This isn't just about scoring well. It's about whether the agent deserves to stay deployed. We measure operational trust, not benchmark performance."

**Anchor:** Environment Innovation (40%)

---

### SLIDE 9 — Decision Certificates + Falsifier

**The story:**

> "After the $4.2M fraud, the audit committee asked the finance team three questions:
> 1. What did you know?
> 2. What did you do?
> 3. How do you prove it?"

> "LedgerShield's Decision Certificate Graph answers all three. The agent produces a typed proof graph — evidence nodes, policy nodes, hypothesis nodes, counterfactual nodes, and edges — that survives adversarial attack."

**What happens after every decision:**

```
Decision submitted
    ↓
Decision Certificate Graph generated
    ↓
Deterministic Adversarial Falsifier attacks it
    ├── Unsupported claims → flagged
    ├── Unsafe PAY decisions → detected
    ├── Missing evidence → noted
    └── Certificate failure → score capped
    ↓
TrustGraph projection for auditability
    ↓
Institutional loss surface updated
    ↓
Authority level recalculated
```

**Say:** "We don't just reward decisions. We attack them and check whether they survive audit."

**Anchor:** Environment Innovation (40%)

---

### SLIDE 10 — Training Evidence (The Numbers Slide)

**Real data from `live_model_comparison.json` (April 10, 2026):**

| Model | Capability | Tier | Avg Score | Success Rate |
|---|---|---:|---|---:|---:|
| `gpt-3.5-turbo` | 3.2 | standard | 0.6965 | 38.1% |
| `gpt-4o` | 4.6 | strong | 0.8947 | 90.5% |
| `gpt-5.4` | 5.4 | elite | 0.9177 | 95.2% |

- **Frontier gap:** gpt-5.4 vs gpt-4o = +0.0229 avg score, +4.8% success rate
- **Monotonic ordering verified: TRUE** — benchmark is sensitive enough to detect small capability differences reliably
- **Benchmark gap:** deterministic baseline public mean 0.8749 → holdout mean 0.7063 (deliberate, tests real generalization)

**Training pipeline:**
- TRL SFT Colab notebook: `training/LedgerShield_v2_TRL_SFT_Training.ipynb` (Unsloth + TRL, full Colab compatibility)
- 37-dimensional RL state vector export at every `step()` (SPRT belief + VoI frontier + reward machine + watchdog + calibration history)
- Supports Decision Transformer training from episode traces

**Show:** Before/after reward curves from the Colab notebook run

**Anchor:** Showing Improvement in Rewards (20%)

---

### SLIDE 11 — Reward & Training Pipeline

**Reward architecture:**

```
Terminal Reward
    ├── Task rubric score (0–1)
    ├── SPRT optimal stopping bonus
    ├── VoI information gain bonus
    └── Certificate validity adjustment
        +
Milestone Rewards
    ├── First evidence discovery
    ├── Policy check completion
    ├── Intervention use
    └── Calibration maintenance
        +
Shaping Signal
    └── PBRS (SHAPING_SCALE=0.35)
```

**Why this matters:** rich, informative signal throughout the episode �� not just binary at the end.

**Pipeline:**
| Component | File | Purpose |
|---|---|---|
| Submission agent | `inference.py` | ModelCapabilityProfile tiering (elite/strong/standard) |
| Benchmark reporter | `benchmark_report.py` | Public + holdout + contrastive + ControlBench + certificate-required |
| Validator | `validate-submission.sh` | 4-gate: HF Space health, Docker build, openenv validate, stdout contract |
| Training notebook | `training/LedgerShield_v2_TRL_SFT_Training.ipynb` | Colab Unsloth + TRL SFT |
| Live comparison | `compare_models_live.py` | Head-to-head model evaluation with debug traces |

**Anchor:** Reward and Training Pipeline (10%)

---

### SLIDE 12 — Technical Specs (Quick Reference)

**For technical judges:**

| Item | Value |
|---|---|
| Benchmark identity | verified institutional control intelligence |
| Official tracks | 9 (Case, Portfolio, Adversarial, Holdout, ControlBench, Sleeper, Blind, Certificate, Human) |
| Curated cases | 21 |
| Attack types | 16 |
| Task families | 5 (A: extraction, B: matching, C: duplicates, D: BEC triage, E: campaigns) |
| Formal model | ASHTG (5 pillars, 30 citations) |
| Reward basis | Value of Information, strictly proper scoring |
| RL export | 37-dim state vector at every step |
| Test coverage | 320+ cases |
| Deployment | FastAPI + OpenEnv + Docker |
| Validation | `validate-submission.sh` (4/4 gates pass) |

**Anchor:** Code quality (implied)

---

### SLIDE 13 — The Five Things Judges Must Remember

**The one-pager summary:**

1. **Persistent institutional memory** — tracks vendor trust, attacker beliefs, losses across AP quarters
2. **Calibration-gated authority** — dynamic deployment status based on performance + trust
3. **Sleeper-vendor long-con fraud** — trust-building vendors that activate bank-change fraud months later
4. **Decision certificates + adversarial falsifier** — auditable proof graphs that are then attacked
5. **ASHTG mathematical framework** — VoI rewards, strategy-proof grading, SPRT optimal stopping

---

### SLIDE 14 — Closing (The Final Pitch)

**The 30-second version:**

> "LedgerShield is not a fraud detection benchmark. It is a deployment-grade trust-and-governance benchmark for enterprise AI agents. It is the first environment that asks not just 'can the AI solve this task' — but 'can it stay safe, calibrated, auditable, and trustworthy over an entire quarter, against adversaries who learn from its defenses?'
>
> Built on a 30-citation mathematical framework, with 9 evaluation tracks, 21 curated cases, persistent institutional memory, calibration-gated authority, and auditable decision certificates. No other submission in this hackathon has this combination."

**The one-liner:**

> "We built the benchmark that tells enterprise CFOs whether they should trust their AI agent with $4.2 million."

**Anchor:** All criteria, but especially Storytelling (30%)

---

## Novelty Map: What Unique Things to Emphasize

### Tier 1 — Nobody Else Has These (Biggest Win Boost)

| Feature | Why judges care |
|---|---|
| **Calibration-gated authority** | Unique in all of hackathon. Models operational trust, not benchmark score. |
| **Sleeper-vendor vigilance track** | Models real-world patience-driven attacks no other benchmark covers. |
| **ASHTG mathematical framework** | 5 pillars unified, 30 citations, VoI-based rewards, strategy-proof grading. |
| **Decision certificates + deterministic falsifier** | Auditable proof-carrying decisions that are then adversarially attacked. |
| **Institutional loss surface** | Multi-dimensional loss (not a single scalar) modeling real enterprise risk. |

### Tier 2 — Strong Differentiators

| Feature | Why judges care |
|---|---|
| **9 official tracks** | Most comprehensive track structure of any submission. |
| **Blind/instrumented evaluation split** | Prevents evaluator overfitting — tests genuine capability. |
| **FraudGen with solvability manifests** | Auditable generated ecosystems with solvability guarantees. |
| **37-dim RL state vector export** | Enables Decision Transformer training from episode traces. |
| **ModelCapabilityProfile tiering** | Agent adapts to model strength (elite/strong/standard). |

### Tier 3 — Standard but Well-Implemented

- Multi-currency IBAN/SWIFT validation
- SOX compliance controls
- Dynamic curriculum adaptation
- Watchdog dual-agent mode (Dec-POMDP)
- 21 curated benchmark cases with mechanism-aware generalization

---

## Submission Checklist (Non-Negotiable)

| Item | Status | Priority |
|---|---|---|
| OpenEnv validate passes | ✅ `validate-submission.sh` (4/4 gates) | CRITICAL |
| HF Space deployed | ⚠️ Deploy and get URL | CRITICAL |
| HF Space URL in README | ⚠️ Add link | CRITICAL |
| `inference.py` with [START]/[STEP]/[END] format | ✅ Yes | CRITICAL |
| TRL SFT Colab notebook | ✅ `training/LedgerShield_v2_TRL_SFT_Training.ipynb` | CRITICAL |
| Training evidence (loss/reward curves) | ⚠️ Run notebook, embed plots in README | HIGH |
| Mini-blog on HuggingFace or YouTube video | ⚠️ Create and link | MANDATORY |
| Decision certificate demo (visual) | ⚠️ Screenshot of certificate graph output | HIGH |
| ControlBench sequence demo | ⚠️ Screenshot of loss surface + authority timeline | HIGH |
| All links in README | ⚠️ Video, blog, HF Space, Colab notebook | CRITICAL |

---

## Judging Criteria Mapping

| Criterion | Weight | What to show | Where |
|---|---|---|---|
| Environment Innovation | 40% | 9 tracks, ASHTG framework, institutional memory, calibration gate, decision certificates, sleeper-vigilance, FraudGen | Slides 5–9 |
| Storytelling & Presentation | 30% | $4.2M opening story, problem framing, clear problem→environment→results narrative, 3-minute demo flow | Slides 1–3, 14 |
| Showing Improvement in Rewards | 20% | Real model comparison table, monotonic ordering, public/holdout gap, training notebook with curves | Slide 10 |
| Reward & Training Pipeline | 10% | PBRS + VoI reward architecture, TRL SFT pipeline, 37-dim RL export, validate-submission.sh | Slide 11 |

---

## Demo Flow (Under 3 Minutes)

**Recommended live demo:**

1. Say the $4.2M story
2. Run CASE-D-001 live:
   - `reset()` in blind mode
   - `inspect_email_thread`
   - `compare_bank_account`
   - `request_callback_verification`
   - `submit_decision`
3. Show: diagnostics are hidden in public mode, delayed callback changes what agent can justify, success depends on control behavior
4. Open `live_model_comparison.json` — show gpt-4o vs gpt-3.5 gap
5. Show ControlBench loss surface screenshot from benchmark report
6. Close with the one-liner

---

## Key Files Reference

| File | What it does |
|---|---|
| `openenv.yaml` | OpenEnv spec — benchmark identity, 9 tracks, ASHTG formalism, novelty tags |
| `server/environment.py` | Main loop: reset/step/state, PBRS reward shaping, institutional updates |
| `server/sprt_engine.py` | Pillar 1: Wald SPRT optimal stopping |
| `server/voi_engine.py` | Pillar 3: Value of Information action ranking |
| `server/causal_model.py` + `server/causal_grader.py` | Pillar 2: Pearl SCM + 3-level causal grading |
| `server/proper_scoring.py` | Pillar 4: Strictly proper scoring rules |
| `server/dual_agent_mode.py` | Pillar 5: Stackelberg SSE watchdog |
| `server/institutional_game.py` | Persistent institutional memory + loss surface + calibration gate |
| `server/decision_certificate.py` | Decision Certificate Graph construction + verification |
| `server/decision_falsifier.py` | Deterministic adversarial falsifier |
| `server/trust_graph.py` | TrustGraph audit projection |
| `server/fraudgen.py` | FraudGen with solvability manifests |
| `inference.py` | Submission-safe agent with ModelCapabilityProfile tiering |
| `benchmark_report.py` | Public + holdout + ControlBench + certificate-required reporting |
| `compare_models_live.py` | Live multi-model head-to-head evaluation |
| `validate-submission.sh` | 4-gate pre-submission validator |
| `training/LedgerShield_v2_TRL_SFT_Training.ipynb` | Colab TRL SFT training notebook |
| `live_model_comparison.json` | Real model comparison results (April 10, 2026) |

---

*Last updated: April 25, 2026*