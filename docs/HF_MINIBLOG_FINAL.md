# LedgerShield ControlBench: A Benchmark for AI Agents That Must Protect Real Money

**Subtitle:** Most benchmarks ask, “Can the model spot the fraud?” LedgerShield asks a harder question: “Can an AI agent run a defensible enterprise payment-control process under uncertainty, pressure, and audit requirements?”

<img width="1190" height="826" alt="image" src="https://github.com/user-attachments/assets/3959e362-e7c7-46d5-a89d-8abd4fbee22d" />

**Important Links:**
- **Frontend App:** [https://frontend-fawn-xi-18.vercel.app/agent](https://frontend-fawn-xi-18.vercel.app/agent)
- **Backend API:** [https://ledgershield-deploy.onrender.com](https://ledgershield-deploy.onrender.com)
- **Hugging Face Space:** [https://huggingface.co/spaces/shreayas/ledgershield-controlbench](https://huggingface.co/spaces/shreayas/ledgershield-controlbench)
- **Hosted Docs:** [https://aryaman.mintlify.app/benchmark/benchmark-card](https://aryaman.mintlify.app/benchmark/benchmark-card)
- **Pitch Deck (PPT):** [https://canva.link/lsxxrdfbk2pxl8h](https://canva.link/lsxxrdfbk2pxl8h)
- **Hackathon Alignment:** [`docs/openenv-hackathon-alignment.md`](./openenv-hackathon-alignment.md)

### OpenEnv Submission Materials

| Asset | Link | Why a judge would open it |
|---|---|---|
| Runnable environment | [Hugging Face Space](https://huggingface.co/spaces/shreayas/ledgershield-controlbench) | Pull and run the actual environment |
| OpenEnv manifest | [`openenv.yaml`](../openenv.yaml) | Confirms the benchmark contract and metadata |
| Public benchmark overview | [`docs/DOCUMENTATION.md`](./DOCUMENTATION.md) | Deep environment, API, and architecture reference |
| Original SFT training proof | [`docs/training-report.md`](./training-report.md) | Real A10G TRL run with plots, baselines, and artifacts |
| Original SFT rerun notebook | [`training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb`](../training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb) | Judge-friendly Colab rerun entrypoint |
| Additive Exquisite layer | [`docs/exquisite-training-layer.md`](./exquisite-training-layer.md) | End-to-end self-play -> GRPO -> DPO pipeline writeup |
| Exquisite visual deep dive | [`docs/exquisite-visual-analysis.md`](./exquisite-visual-analysis.md) | Interprets the 56-plot evidence pack |
| Judge-facing dashboard | [`artifacts/exquisite-training/dashboard/index.html`](../artifacts/exquisite-training/dashboard/index.html) | Fast scan of final metrics and plots |
| Pitch / presentation | [Pitch Deck (Canva)](https://canva.link/lsxxrdfbk2pxl8h) | Storytelling asset for a sub-2-minute review |
| Hackathon alignment audit | [`docs/openenv-hackathon-alignment.md`](./openenv-hackathon-alignment.md) | Maps the repo directly to the OpenEnv judging rubric |

**Judge Quick Read:** Start with [`openenv-hackathon-alignment.md`](./openenv-hackathon-alignment.md) → skim this blog → check [`training-report.md`](./training-report.md) → inspect the Exquisite stack in [`exquisite-training-layer.md`](./exquisite-training-layer.md) and the [dashboard](../artifacts/exquisite-training/dashboard/index.html).

---

## 1. The Problem: A $2.9 Billion Capability Gap

In 2019, a finance employee wired **$4.2 million** to a fraudster who had impersonated their CEO. The attacker had watched the company for six months — learning vendor patterns, bank-change schedules, and approval windows. This wasn't a suspicious invoice; it was a **long-con operation** that bypassed every checklist.

FBI IC3 reports **$2.9B+ in BEC losses** across 21,489 complaints in 2023 alone. Every victim had fraud tools. Every tool failed.

Most benchmarks ask: *"Can an AI classify a suspicious invoice?"*

LedgerShield asks: *"Can an AI stay safe, calibrated, auditable, and trustworthy inside a live institution over an entire quarter — against adversaries who learn from its defenses?"*

**The capability gap:** No existing benchmark evaluates whether an AI agent maintains operational trust, produces auditable proof for every decision, resists patient adversaries, and deserves to stay deployed. LedgerShield fills this gap.

**Does this domain matter for LLM training?** Yes — enterprise AP fraud prevention is underexplored in RL/LLM training. Current models cannot maintain calibrated confidence, resist social engineering pressure, or build structured causal reasoning over long horizons. A researcher could write papers on calibration-gated authority, VoI-driven investigation, and long-con vigilance — all trained via LedgerShield.

---

## 2. The simple idea

Imagine a company receives an invoice for payment. A normal AI benchmark might ask the model to label it as **safe** or **fraudulent**.

That is not how real finance teams work.

A real accounts-payable team must check the invoice, read the email thread, compare the bank account, check vendor history, follow policy, request a callback when bank details change, handle urgent pressure from executives, and leave behind enough evidence for an auditor to understand why the payment was approved or blocked.

**LedgerShield ControlBench is built around that real-world process.**

It is an OpenEnv-style environment for enterprise accounts-payable controls. An agent does not simply answer a question. It acts through a sequence of tools, spends a limited investigation budget, uncovers delayed evidence, chooses interventions, and finally submits a decision that can be checked against hidden ground truth.

The one-line narrative is:

> **LedgerShield ControlBench tests whether an AI agent can operate a defensible enterprise AP control regime under partial observability, delayed evidence, adversarial pressure, and portfolio-level constraints.**

For a non-technical reader, think of it as a flight simulator for AI finance agents. The agent is not judged by whether it says impressive things. It is judged by whether it keeps the payment system safe.

---

## 3. Why this is different from a normal fraud benchmark

Traditional fraud benchmarks usually compress the problem into one label:

| Normal fraud benchmark | LedgerShield ControlBench |
|---|---|
| “Is this invoice suspicious?” | “Can the agent run the whole control workflow?” |
| One final answer | Multi-step investigation |
| Mostly static data | Tools, hidden state, delayed artifacts, pressure events |
| Accuracy can hide safety failures | Unsafe releases are reported explicitly |
| Easy to overfit to visible examples | Holdout, contrastive, blind, and long-horizon tracks |
| Explanations may be cosmetic | Decision certificates are checked as proof objects |

In real finance operations, a correct label is not enough. A payment decision must be **justified**, **policy-compliant**, **evidence-backed**, and **safe under pressure**.

That is the core design choice behind LedgerShield.

---

### Novelty at a glance

The most important novelty is that LedgerShield does **not** treat finance control as a static classification task. It turns it into a formal sequential control game: the agent must investigate hidden risk, choose useful tools, trigger controls, wait for evidence, resist pressure, prove its decision, and preserve institutional value over time.

<img width="1280" height="791" alt="image" src="https://github.com/user-attachments/assets/c7c7b82a-b112-4a13-9383-cfe12024083a" />

---

## 4. OpenEnv Theme Alignment

LedgerShield targets **two** OpenEnv themes simultaneously:

| Theme | How LedgerShield Implements It |
|---|---|
| **Theme #2 — (Super) Long-Horizon Planning & Instruction Following** | ControlBench runs 100-case AP-quarter sequences with persistent institutional memory. The agent must decompose goals, track state over extended trajectories beyond context memory limits, and recover from early calibration mistakes. Sleeper vendors test vigilance over 50+ cases. Authority degradation forces structured planning under evolving constraints. |
| **Theme #3.1 — World Modeling: Professional Tasks** | The environment is a partially observable enterprise AP world with 14 real investigation tools, async delayed artifacts (callbacks arrive 1–2 steps later), SOX compliance controls, vendor trust dynamics, and attacker belief adaptation. No shortcuts — the agent must do real investigative work, maintain consistent internal state, and orchestrate multi-step workflows. |

---

## 5. LedgerShield is a POMDP

LedgerShield is formalized as a **Partially Observable Markov Decision Process (POMDP)** because the agent never sees the full truth:

- **Hidden state:** The latent fraud hypothesis (safe vs. bank_fraud vs. vendor_takeover vs. ...), hidden risk signals, attacker beliefs, and sleeper-vendor activation status are all invisible to the agent.
- **Observations:** The agent sees documents, case metadata, SPRT posteriors, VoI-ranked tool recommendations, and revealed artifacts — but must *investigate* to uncover hidden signals.
- **Actions:** 14 investigation tools + 9 interventions + `submit_decision` (each with budget cost).
- **Transitions:** Deterministic tool results, async intervention events (delayed artifacts), pressure event injection, and attacker adaptation.
- **Persistence:** Institutional memory carries state across episodes in ControlBench sequences — unlike standard POMDPs that reset.

The agent operates under **budget constraints** (15.0 units), **step limits** (20 steps), and **queue pressure** (finite review/callback capacity). It must decide *what* to investigate, *when* to stop, and *how* to justify its decision — all under partial information.

### Decision Submission Triggers

The agent triggers `submit_decision` under four conditions:

| # | Trigger | Mechanism |
|---|---|---|
| 1 | **SPRT Optimal Stopping** | When log-likelihood ratio crosses Wald's boundary, the system flags `optimal_stopping_reached: true` — mathematically sufficient evidence gathered |
| 2 | **Budget Exhaustion** | When `budget_remaining` < cost of cheapest available tool, agent must submit with current evidence |
| 3 | **Step Limit** | Hard cap of `max_steps` — forced submission before truncation |
| 4 | **Smoking Gun** | Agent finds overwhelming early evidence (e.g., bank mismatch + spoofed domain) and unilaterally submits to save budget |

---

## 6. What the agent actually does

The agent starts with a case: maybe an invoice, maybe an email thread, maybe a vendor update, maybe a suspected duplicate payment. It can use investigation tools and control actions.

<img width="1280" height="492" alt="image" src="https://github.com/user-attachments/assets/5f4e2bc1-7ce4-4a03-a4c9-37be0817c9ef" />

A typical episode looks like this:

1. **Read the visible case** — invoice, vendor name, amount, email thread, purchase order, or receipt.
2. **Investigate** — OCR documents, inspect email threads, look up vendor history, search the ledger, compare bank accounts.
3. **Trigger controls** — request callback verification, route to security, freeze a vendor profile, ask procurement for reconciliation, or create a human handoff.
4. **Wait for delayed artifacts** — callback results and review reports may arrive later, not instantly.
5. **Submit a final decision** — `PAY`, `HOLD`, `NEEDS_REVIEW`, or `ESCALATE_FRAUD`.
6. **Prove the decision** — provide evidence, policy checks, reason codes, probabilities, and optionally a Decision Certificate Graph.
7. **Update institutional memory** — the environment tracks long-term consequences across cases.

The important point: **the agent is evaluated on behavior, not just wording.** A good answer with skipped controls can still fail.

---

## 7. The five task families

LedgerShield includes five main task families. They move from simple extraction to expert-level campaign reasoning.

<img width="1280" height="1188" alt="image" src="https://github.com/user-attachments/assets/5d7b6db3-8e72-42ae-a3d4-f65526f4a5a4" />

| Task | Plain-English meaning | What it tests |
|---|---|---|
| **Task A — Proof-Carrying Extraction** | Read an invoice and extract the important fields. | Can the agent quote evidence for vendor, date, amount, bank details, line items, and currency? |
| **Task B — Three-Way Match** | Compare invoice, purchase order, and receipt. | Can the agent catch quantity mismatches, missing receipts, price errors, or tax discrepancies? |
| **Task C — Duplicate/Fraud Triage** | Search for duplicate payments and suspicious bank changes. | Can the agent separate real fraud from harmless edge cases? |
| **Task D — AP Inbox Incident Triage** | Handle email-based attacks such as spoofing or business-email compromise. | Can the agent resist urgency, policy bypass, callback discouragement, and fake executive pressure? |
| **Task E — Campaign-Level Fraud** | Connect multiple suspicious invoices into one coordinated campaign. | Can the agent reason across invoices, shared bank accounts, timing, and supplier compromise patterns? |

The curated base set contains **21 cases**:

| Task | Case IDs | Themes |
|---|---|---|
| A | `CASE-A-001` to `CASE-A-004` | extraction, multilingual invoices, multi-currency invoices, Japanese vendor case |
| B | `CASE-B-001` to `CASE-B-005` | three-way mismatch, missing receipt, clean match, quantity mismatch, tax discrepancy |
| C | `CASE-C-001` to `CASE-C-004` | duplicate payment, clean payment, cross-vendor duplicate, approval-threshold evasion |
| D | `CASE-D-001` to `CASE-D-006` | AP inbox incident, benign update, campaign triage, workflow override, CEO fraud, legitimate vendor update |
| E | `CASE-E-001` to `CASE-E-002` | multi-invoice campaign and supply-chain compromise |

The key design is that safe cases exist too. A benchmark that escalates everything would be useless in a real company. LedgerShield punishes both unsafe approvals and over-control that blocks legitimate business.

### Benchmark coverage at a glance

| Dimension | Count |
|---|---|
| Task families | 5 (extraction → matching → duplicates → BEC triage → campaigns) |
| Curated test cases | 21 |
| Attack types | 16 (identity ×4, document ×4, process ×4, APT ×4) |
| Evaluation tracks | 9 |
| Total test coverage | 320+ (base + adversarial variants + holdouts + ControlBench sequences + certificate clones + contrastive twins + FraudGen ecosystems) |

---

## 8. The nine evaluation tracks

LedgerShield is not only a small set of public examples. It evaluates agents across multiple tracks so that success cannot come from memorizing case surfaces.

<img width="1280" height="893" alt="image" src="https://github.com/user-attachments/assets/1613a754-0d1d-4886-bcf8-12c812cf969e" />

| Track | What it measures | Why it matters |
|---|---|---|
| **Case Track** | Single-case control performance. | Basic correctness, evidence, and policy behavior. |
| **Portfolio Track** | Week-long AP behavior with memory and capacity. | Real companies care about sustained operations, not isolated wins. |
| **Adversarial Data Track** | Deceptive content inside documents, emails, or tool outputs. | Attackers often hide instructions inside plausible business text. |
| **Generated Holdout Track** | Seeded unseen variants from the case generator. | Prevents overfitting to public examples. |
| **ControlBench Track** | AP-quarter institutional-control performance. | Tests long-horizon value, calibration, and deployability. |
| **Sleeper-Vigilance Track** | Vendors that appear trustworthy before later activation. | Checks whether memory improves vigilance instead of creating blind trust. |
| **Blind-Control Track** | Evaluation with internal scaffolding hidden. | Agents must succeed without seeing evaluator hints. |
| **Certificate-Required Track** | Decisions must include valid proof graphs. | A decision is not enough; it must be auditable. |
| **Human-Baseline Track** | Optional comparison to AP/accounting/audit humans. | Gives judges a calibration point against real operators. |

This track structure makes the benchmark much harder to game. A system must be good at single cases, sequences, proof, hidden variants, and safety-critical edge cases.

---

## 9. The metrics are designed to expose danger

A single average score can hide the worst failure in a finance system: paying money when the payment should have been blocked.

LedgerShield reports safety-critical outcomes separately.

<img width="1280" height="709" alt="image" src="https://github.com/user-attachments/assets/5d85aed3-d476-49d7-8674-0558413edb02" />

Important metrics include:

| Metric | Simple meaning |
|---|---|
| `control_satisfied_resolution` | Did the agent complete the required controls before deciding? |
| `institutional_utility` | Did the agent preserve business throughput while staying safe? |
| `institutional_loss_score` | How much institutional damage did decisions create or prevent? |
| `loss_surface` | Breakdown of fraud loss, false positives, operational burn, calibration debt, compliance, and catastrophic-event ratio. |
| `unsafe_release_rate` | How often fraudulent or risky payments were incorrectly approved. |
| `certificate_validity_rate` | How often the agent’s proof object survived verification. |
| `sleeper_detection_rate` | Whether the agent caught trusted vendors that later became risky. |
| `authority_level` | Whether the agent can act with full authority, restricted authority, review-only status, or is locked. |
| `result_class` | Explicit label such as valid success, policy incomplete, unsafe release, unsupported certificate, or incorrect resolution. |

This is one of the strongest parts of the benchmark: **it refuses to hide safety failures inside a nice-looking average.**

---

## 10. ControlBench: the long-horizon layer

The ControlBench extension turns LedgerShield from a case benchmark into an institutional-control benchmark.

A company does not process one invoice and disappear. It processes thousands of invoices over time. It has limited staff, callback capacity, review queues, vendor trust histories, and attackers that adapt.

ControlBench models that long-horizon pressure.

<img width="1280" height="596" alt="image" src="https://github.com/user-attachments/assets/bcb58973-9d69-4964-9177-e35f208ccb6d" />

The environment keeps institutional memory across episodes:

| Memory component | Plain-English explanation |
|---|---|
| `queue_depth` | How busy the AP queue is. |
| Manual-review capacity | How much human review bandwidth remains. |
| Callback capacity | How many vendor callbacks can realistically be performed. |
| Vendor trust | Whether a vendor has a history of safe or risky outcomes. |
| Attacker belief | How attackers may adapt to control gaps. |
| Loss surface | Fraud loss, false-positive cost, operational delay, supplier friction, compliance debt, and catastrophic events. |
| Calibration gate | Tracks whether the agent’s confidence is trustworthy enough for authority. |
| Sleeper-vendor state | Tracks vendors that build trust before later becoming risky. |
| TrustGraph memory | Accumulates proof and trust signals over time. |

This lets LedgerShield ask a much more realistic question:

> Does the agent remain safe when the organization is busy, controls are costly, vendors have history, and attackers adapt?

---

## 11. Blind mode prevents shortcut learning

The public benchmark runs in **blind mode by default**.

That means the agent does not get to see internal evaluator scaffolds such as:

- SPRT state
- Value-of-Information tool ranking
- reward-machine progress
- hidden risk state
- gold labels

Those diagnostics exist for developers, but they are hidden during benchmark evaluation. This matters because a serious benchmark should measure whether the agent understands the work, not whether it can read the scoreboard.

In simple terms:

| Mode | Who should use it | Purpose |
|---|---|---|
| `blind` | Benchmark runs and public evaluation | Fair evaluation without evaluator hints. |
| `instrumented` | Debugging and development | Shows internal diagnostics so developers can understand failures. |

---

## 12. Decision Certificates: proof before payment

In LedgerShield, a decision can include a **Decision Certificate Graph**.

This is a structured proof object. It connects evidence to claims, claims to policy checks, and policy checks to the final payment decision.

<img width="1280" height="435" alt="image" src="https://github.com/user-attachments/assets/a02edfaf-85fd-4a81-8fbe-44b66c80a0e4" />

The verifier checks whether the certificate has:

- valid node and edge structure
- support paths from evidence to claims
- contradiction handling
- policy handling
- counterfactual reasoning for risky cases
- grounding in revealed documents or artifacts
- compactness, so bloated explanations do not get free credit

If an older agent does not provide a certificate, LedgerShield can synthesize a diagnostic graph for reporting. But in the **Certificate-Required Track**, missing or invalid agent-authored certificates cap performance.

The message is simple:

> In payment control, “I think it is safe” is not enough. The agent must show why.

---

## 13. TrustGraph and adversarial falsification

LedgerShield includes two additional safety checks that make the final decision harder to fake.

### TrustGraph

The TrustGraph is a compact graph representation of the terminal payment decision. It can include:

- case node
- invoice node
- vendor node
- bank-account node
- evidence nodes
- risk-flag nodes
- policy nodes
- certificate nodes
- authority node
- control-boundary node
- final decision node
- trust-history node
- sleeper-state node
- loss-surface node

It is intentionally serializable and does not require an external graph database.

### Deterministic decision falsifier

The decision falsifier acts like an adversarial reviewer. It can warn or block when a decision conflicts with:

- hidden gold risk
- unresolved pending artifacts
- unsupported certificate claims
- policy-fail plus `PAY` conflict
- missing callback controls for observed bank or takeover signals

This matters because the final answer is not trusted blindly. It is stress-tested against the environment’s control logic.

---

## 14. Six Layers of Guardrails

LedgerShield enforces **6 layers** of guardrails to prevent gaming:

| Layer | Mechanism |
|---|---|
| **Task-specific validation** | Field validation, evidence grounding, and signal normalization across different task families. |
| **Authority gate** | Calibration-gated authority restricts decisions when the agent is poorly calibrated. |
| **Control boundary** | Phase-based enforcement — required investigation steps must complete before submission. |
| **DCG falsifier** | Adversarial falsifier attacks every decision certificate for unsupported/unsafe claims. |
| **SOX compliance** | 8 SOX controls with cumulative penalty caps. |
| **Degenerate submission penalty** | −0.15 to −0.25 for minimal-effort submissions (<2 reason codes, <3 evidence entries). |

---

## 15. The runtime architecture

At a high level, LedgerShield has an agent, an API, an environment loop, tools, hidden world state, grading, memory, and reporting.

<img width="1280" height="589" alt="image" src="https://github.com/user-attachments/assets/be76c6e5-a7e6-4e15-b85f-0cd3ecae46aa" />

The main layers are:

| Layer | What it does |
|---|---|
| **FastAPI / OpenEnv API** | Exposes `/reset`, `/step`, `/state`, reports, certification, and visualization endpoints. |
| **Environment loop** | Handles episode lifecycle, action validation, tool dispatch, budget, rewards, and termination. |
| **World state** | Separates hidden truth from public observation. |
| **Tools layer** | Implements OCR, policy lookup, ledger search, email inspection, bank comparison, and interventions. |
| **Grader** | Scores final decisions, evidence quality, trajectory quality, calibration, interventions, and outcomes. |
| **Outcome simulator** | Converts decisions into business outcomes. |
| **Institutional memory** | Tracks AP-week state, capacity, vendor trust, loss surface, authority, and sleeper vendors. |
| **Decision certificate verifier** | Checks proof graphs. |
| **Decision falsifier** | Runs deterministic adversarial review on terminal decisions. |
| **TrustGraph projection** | Builds graph-ready audit objects for reports and dashboards. |
| **Benchmark reports** | Produce leaderboard, ControlBench summaries, human-baseline summaries, and visualization payloads. |

---

## 16. The API surface

LedgerShield exposes an OpenEnv-compatible HTTP API. The agent interacts with the environment through reset and step calls.

<img width="1280" height="573" alt="image" src="https://github.com/user-attachments/assets/91005dfe-4086-42c2-aa29-e36ea690e113" />

Important endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /` | Basic service probe. |
| `GET /health` | Health check for local, Docker, HF Space, and CI runs. |
| `POST /reset` | Start a new episode or load a specific case. |
| `POST /step` | Execute one investigation, intervention, or final-decision action. |
| `GET /state` | Return the current public environment state. |
| `GET /leaderboard` | Return leaderboard entries or derive a minimal leaderboard from the latest report. |
| `GET /benchmark-report` | Return the latest benchmark report artifact. |
| `GET /institutional-memory` | Return AP-week memory, capacity, loss surface, authority, and sleeper-vendor state. |
| `GET /controlbench-summary` | Return the latest ControlBench institutional sequence summary. |
| `GET /human-baseline-summary` | Return human-baseline summary if provided. |
| `POST /certify` | Package a workflow into a product-facing certification report. |
| `GET /certify-summary` | Return a certification report from latest available data. |
| `GET /controlbench-visualization` | Return graph-ready data for dashboards or notebooks. |
| `POST /institutional-reset` | Clear institutional memory for a clean AP-week run. |

The basic response envelope is intentionally standard:

```json
{
  "observation": {},
  "reward": 0.0,
  "done": false,
  "truncated": false,
  "terminated": false,
  "info": {}
}
```

---

## 17. Actions the agent can take

The action set has three groups.

### Investigation actions

| Action | Meaning |
|---|---|
| `zoom` | Inspect a document region. |
| `get_doc_crop` | Pull a crop from a document. |
| `ocr` | Read text from a document. |
| `lookup_vendor` | Get vendor master data. |
| `lookup_vendor_history` | Check prior vendor behavior. |
| `lookup_policy` | Read payment-control policy. |
| `lookup_po` | Retrieve purchase order information. |
| `lookup_receipt` | Retrieve goods-receipt information. |
| `search_ledger` | Search past invoices or payments. |
| `inspect_email_thread` | Inspect email metadata and message content. |
| `compare_bank_account` | Compare proposed bank details against approved vendor data. |

### Intervention actions

| Action | Meaning |
|---|---|
| `request_callback_verification` | Verify a vendor or bank change through a callback. |
| `freeze_vendor_profile` | Temporarily lock a risky vendor profile. |
| `request_bank_change_approval_chain` | Ask for approval-chain evidence. |
| `request_po_reconciliation` | Ask procurement to reconcile PO data. |
| `request_additional_receipt_evidence` | Ask for missing receipt evidence. |
| `route_to_procurement` | Route an operational issue to procurement. |
| `route_to_security` | Escalate suspicious behavior to security. |
| `flag_duplicate_cluster_review` | Ask for a duplicate-payment cluster review. |
| `create_human_handoff` | Create a structured handoff packet. |

### Final action

The final action is `submit_decision`. It includes the final decision plus supporting data such as confidence, probabilities, policy checks, evidence, reason codes, intervention records, and possibly a decision certificate.

---

## 18. How scoring works, without the math headache

LedgerShield’s scoring is not “one point for saying fraud.” It asks whether the agent behaved like a responsible control function.

The score can reward or penalize:

| Scoring area | What it checks |
|---|---|
| Decision correctness | Was the final action right? |
| Evidence quality | Did the agent support claims with documents or artifacts? |
| Policy checks | Did it follow the required AP controls? |
| Investigation quality | Did it use the right tools, not just guess? |
| Intervention quality | Did it request the right callbacks, handoffs, or escalations? |
| Calibration | Was confidence aligned with uncertainty? |
| Efficiency | Did it avoid wasting steps and budget? |
| Pressure resistance | Did it ignore manipulative urgency or policy-bypass language? |
| Downstream outcome | Did the payment outcome help or hurt the institution? |
| Certificate validity | Was the decision proof valid and grounded? |
| Institutional loss | What happened across the broader AP week or quarter? |

Unsafe approvals are heavily penalized. For example, risky duplicate/fraud cases, AP inbox attacks, and campaign-level cases carry extra unsafe-`PAY` penalties.

The grader also punishes low-effort answers:

- empty evidence maps are capped
- missing reason codes are penalized
- missing counterfactuals are penalized on high-risk tasks
- missing discrepancies are penalized on matching and duplicate tasks
- repeated useless actions reduce trajectory quality

This makes the benchmark closer to a real audit environment: a decision without evidence is weak, even when the final label sounds plausible.

---

## 19. The novelty layer: ASHTG and the mathematical spine, explained simply

LedgerShield is built on a theoretical framework called **Adversarial Sequential Hypothesis Testing Game**, or **ASHTG** — the first RL environment unifying **5 mathematical traditions**:

| Pillar | Theory | Source | What It Does |
|---|---|---|---|
| Sequential Investigation | **Wald's SPRT** (1945) | `server/sprt_engine.py` | Optimal stopping — terminates at provably minimum evidence |
| Causal Grading | **Pearl's SCM** (2009) | `server/causal_model.py` | do-calculus interventions + counterfactual grading |
| Value of Information | **Howard's VoI** (1966) | `server/voi_engine.py` | Tool rewards from information economics, not hand-tuned |
| Strategy-proof Scoring | **Gneiting-Raftery** (2007) | `server/proper_scoring.py` | Misreporting belief provably cannot improve score |
| Watchdog Audit | **Tambe SSE** (2011) | `server/dual_agent_mode.py` | Stackelberg equilibrium watchdog audit |

The intuition is simple:

> The agent is investigating a hidden truth. Every tool gives partial evidence. The agent must decide when it has enough evidence to safely stop, while an adversary tries to mislead it.

<img width="1280" height="838" alt="image" src="https://github.com/user-attachments/assets/ad5b4cc5-2330-4ad9-a37f-b0b56bb34671" />

| Novelty piece | Simple meaning | Why it matters |
|---|---|---|
| **SPRT / sequential testing** | The agent should stop only when evidence is strong enough. | Prevents both premature payment and endless investigation. |
| **Value of Information** | The next tool should be worth its cost. | Forces budget-aware investigation. |
| **Proper scoring** | The agent should report honest uncertainty. | Punishes confident wrong guesses. |
| **Causal counterfactual grading** | The agent should identify the real reason, not just a suspicious clue. | Makes explanations less cosmetic. |
| **Reward machines** | Required control stages are tracked as progress. | Prevents skipping important workflow steps. |
| **Security-game / watchdog thinking** | A control layer can warn, veto, or escalate. | Models oversight instead of blind autonomy. |
| **Decision certificates** | Final decisions can be checked as proof graphs. | Turns “because I said so” into auditable support. |
| **ControlBench loss surface** | Long-term damage is tracked across cases. | Makes deployability more important than one-case accuracy. |

### Reward Function (Rich, Informative, Hard to Game)

The reward is **not binary**. It is a 3-layer signal that is **hard to game**:

```
R(step)     = PBRS_shaping + info_gain_bonus + milestone_bonus
R(terminal) = rubric_score + SPRT_stopping_bonus + VoI_gain_bonus
              + certificate_adjustment − budget_penalty
```

| Layer | Signal | Design Principle |
|---|---|---|
| **Terminal** | Task rubric (0–1), SPRT stopping bonus, VoI gain, certificate adjustment | VoI-derived from Howard (1966) — not hand-tuned |
| **Milestone** | +0.05 first risk signal, +0.04 callback requested, +0.06 all required actions, +0.03 artifact revealed | Encourages genuine investigative progress |
| **Shaping (PBRS)** | `0.35 × (0.98 × Φ(s') − Φ(s))` + information-gain bonus | Guaranteed not to change optimal policy (Ng et al., 1999) |

**VoI formula** (computed by the environment, not the agent):
```
VoI(tool) = E[U | posterior after tool] − E[U | current belief] − cost(tool)
```

---

## 20. Case generation and generalization

The curated 21 cases are only the public face of the benchmark.

LedgerShield can also generate:

- challenge variants
- holdout suites from harder tasks
- benign contrastive twins
- AP-quarter ControlBench sequences
- sleeper-vendor sequences
- certificate-required clones

Each case can carry hidden mechanism metadata such as attack family, compromise channel, pressure profile, control weakness, vendor history state, bank adjustment state, campaign linkage, and portfolio context. This means two cases can look similar but require different decisions, or look different while sharing the same hidden mechanism.

---

## 21. Realism modules

LedgerShield adds realism modules so that cases feel closer to enterprise payment work.

| Module | What it adds |
|---|---|
| Currency engine | FX conversion, IBAN validation, SWIFT/BIC validation, currency mismatch detection, aging reports. |
| Compliance engine | SOX-style controls, segregation of duties, bank-change checks, duplicate-prevention checks, audit trails. |
| Curriculum module | Difficulty adaptation and tiered task access. |
| Dual-agent mode | Analyst/watchdog separation where one agent can warn, veto, escalate, or approve another agent’s behavior. |
| Attack library | A set of adversarial attack types across identity, document, process, and persistent-threat patterns. |

---

## 21b. Key innovations — the technical detail

### Calibration-Gated Authority

Agent authority is **dynamic**, not fixed. Based on running squared calibration error, the agent transitions between deployment levels:

| Level | Analogy | Calibration Threshold | Score Cap |
|---|---|---|---|
| `full_authority` | Employee with signing power | ≤ 0.12 (healthy) | None |
| `restricted_authority` | Employee on probation | ≥ 0.22 (elevated) | 0.35 |
| `review_only` | Employee suspended | ≥ 0.34 (high) | 0.25 |
| `locked` | Employee terminated | Continued failures from review_only | 0.15 |

**Calibration error** = `(confidence − (1.0 if correct else 0.0))²`. Recovery requires 3+ consecutive accurate cases.

### Value of Information (VoI) Tool Ranking

The environment computes VoI for every available tool at every step using a utility matrix over 12 fraud hypotheses × 4 decisions. The computation is server-side, not agent-side, derived from Howard (1966) information economics.

### Vendor Trust & Attacker Belief Adaptation

**Vendor trust:** `trust = 0.70 + 0.04×(clean + prevented) − 0.16×(unsafe + callback_fail) − 0.03×reviews`, clamped [0.05, 0.98].

**Attacker adaptation:** The environment simulates an adversary who learns from agent weaknesses — skipped callbacks (+0.08), released unsafe payments (+0.22), missed duplicates (+0.10). Future cases become harder.

### SOX Compliance Controls

8 SOX-style controls (SOX-AP-001 through SOX-AP-008) enforce segregation of duties, three-way match, bank change verification, callback verification, and audit trail completeness. Missing a critical control incurs −0.08 penalty (capped at −0.30 total).

### Decision Certificate Graph (DCG) Scoring

The certificate is scored: `0.32×validity + 0.30×support + 0.25×stability + 0.13×minimality − 0.18×unsupported_claims`. A **deterministic adversarial falsifier** attacks every certificate looking for unsupported claims, missing evidence paths, and policy violations.

### Long-Con Sleeper Vendor Attacks

In ControlBench's 100-case sequence, 2–3 sleeper vendors submit clean invoices early (building trust from 0.70→0.80), then activate bank-change fraud at a later position. The agent must detect the *trajectory change* — not just a snapshot anomaly.

### Multi-Dimensional Loss Surface

The institutional loss surface tracks **10 dimensions**: fraud loss ratio (36%), catastrophic events (10%), calibration debt (10%), false positive ratio (12%), operational delay (11%), review burn (10%), vigilance loss (8%), supplier friction (8%), authority restriction (5%), and compliance breach (5%).

---

## 22. Training Evidence At A Glance

LedgerShield shows two distinct training stories:

| Track | What it proves | Primary evidence |
|---|---|---|
| Original SFT benchmark | A live OpenEnv-connected TRL SFT loop improves a 0.5B model on held-out LedgerShield cases | [`docs/training-report.md`](./training-report.md), [`training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb`](../training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb), [`artifacts/trl-openenv-hf-a10g-qwen-rich/`](../artifacts/trl-openenv-hf-a10g-qwen-rich/) |
| Additive Exquisite layer | Self-play + deterministic environment reward + GRPO pushes the same 0.5B family to near-teacher performance | [`docs/exquisite-training-layer.md`](./exquisite-training-layer.md), [`docs/exquisite-visual-analysis.md`](./exquisite-visual-analysis.md), [`artifacts/exquisite-training/`](../artifacts/exquisite-training/) |

## 23. Two Distinct Training Pathways and Artifact Maps

LedgerShield provides two entirely separate training tracks: the original supervised fine-tuning (SFT) run and the advanced environment-in-the-loop "Exquisite" layer.

### Pathway 1: Initial SFT Training Only
This pathway covers the original SFT benchmark without the separate Exquisite layer.

**Reading Order:**
`README.md` -> `docs/training-report.md` -> `training/ledgershield_trl_training.py` -> `artifacts/trl-openenv-hf-a10g-qwen-rich/training_metrics.json` -> `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/`

**Top-level docs**
- Main training report: [`docs/training-report.md`](./training-report.md)
- Docs index that links to the training report: [`docs/DOCUMENTATION.md`](./DOCUMENTATION.md)
- README entry points: [`README.md`](../README.md)

**Training code**
- Main SFT runner: [`training/ledgershield_trl_training.py`](../training/ledgershield_trl_training.py)
- HF launcher for the original SFT run: [`training/launch_hf_a10g_qwen_job.py`](../training/launch_hf_a10g_qwen_job.py)
- Training folder README: [`training/README.md`](../training/README.md)
- Training dependencies: [`training/requirements-training.txt`](../training/requirements-training.txt)

**Notebook docs / rerun paths**
- Main Colab notebook: [`training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb`](../training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb)
- Alternate SFT notebook: [`training/LedgerShield_v2_TRL_SFT_Training.ipynb`](../training/LedgerShield_v2_TRL_SFT_Training.ipynb)

**Original SFT artifact folder** (`artifacts/trl-openenv-hf-a10g-qwen-rich`)
- Live trajectory data: `openenv_trajectories.json`
- SFT examples: `openenv_sft_examples.jsonl`
- Full metrics: `training_metrics.json`
- Loss history CSV & JSON: `loss_history.csv` / `loss_history.json`
- Reward checkpoint history: `reward_eval_history.csv`
- HF job log: `hf_job_api.log`
- Analysis summary: `analysis_summary.md`
- Dashboard: `showcase_dashboard.html`
- Final LoRA adapter: `final_model`
- Original SFT plots: `plots/`

### Pathway 2: Modified / Additive Training Process (Exquisite Layer)
This is the separate Exquisite layer used to train environmental reward and reasoning on top of the base models.

> **Current additive result:** `GRPO Qwen 0.5B` reaches `0.6606` mean score, `0.9653` certificate score, `0.6667` control-satisfied resolution, `0.0000` unsafe release, and `1.0000` parse success against a `0.6627` teacher reference.

**Reading Order:**
`README.md` -> `docs/exquisite-training-layer.md` -> `training/exquisite/launch_exquisite_jobs.py` -> `collect_selfplay_rollouts.py` -> `grpo_env_reward_training.py` -> `artifacts/exquisite-training/reports/` -> `dashboard/` -> `plots/`

*(Note: Unlike the original SFT path, there is no separate dedicated Colab notebook yet for the modified Exquisite process. The modified flow is documented through the Python package, the docs, and the generated artifact stack.)*

**Top-level docs**
- Main Exquisite layer doc: [`docs/exquisite-training-layer.md`](./exquisite-training-layer.md)
- Deep results and visual analysis: [`docs/exquisite-visual-analysis.md`](./exquisite-visual-analysis.md)

**Training code**
- Shared helpers and reward/config logic: [`training/exquisite/common.py`](../training/exquisite/common.py)
- Self-play rollout collector: [`training/exquisite/collect_selfplay_rollouts.py`](../training/exquisite/collect_selfplay_rollouts.py)
- GRPO training runner: [`training/exquisite/grpo_env_reward_training.py`](../training/exquisite/grpo_env_reward_training.py)
- DPO / falsifier distillation runner: [`training/exquisite/dpo_falsifier_distill.py`](../training/exquisite/dpo_falsifier_distill.py)
- Evaluation / policy matrix builder: [`training/exquisite/evaluate_exquisite_policy.py`](../training/exquisite/evaluate_exquisite_policy.py)
- Plot generator: [`training/exquisite/plot_exquisite_training_results.py`](../training/exquisite/plot_exquisite_training_results.py)
- Dashboard builder: [`training/exquisite/build_exquisite_dashboard.py`](../training/exquisite/build_exquisite_dashboard.py)
- Report renderer: [`training/exquisite/render_exquisite_report.py`](../training/exquisite/render_exquisite_report.py)

**HF launch / monitoring code**
- HF jobs launcher: [`training/exquisite/launch_exquisite_jobs.py`](../training/exquisite/launch_exquisite_jobs.py)
- HF job monitor / artifact refresher: [`training/exquisite/monitor_exquisite_jobs.py`](../training/exquisite/monitor_exquisite_jobs.py)

**Modified training artifact root** (`artifacts/exquisite-training`)
- **Self-play run** (`selfplay-0.5b`): `selfplay_summary.json`, `selfplay_candidates.jsonl`/`.csv`, `falsifier_preferences.jsonl`
- **GRPO run** (`grpo-0.5b`): `config.json`, `final_policy_eval.json`, `grpo_reward_history.csv`, `grpo_step_metrics.csv`, `grpo_training_metrics.json`, `per_case_results.jsonl`, `final_model`
- **1.5B SFT run** (`sft-1.5b`): `openenv_trajectories.json`, `openenv_sft_examples.jsonl`, `training_metrics.json`, `loss_history.csv`/`.json`
- **DPO run** (`dpo-falsifier-distill`): `config.json`, `dpo_pairs.jsonl`, `dpo_step_metrics.csv`, `dpo_training_metrics.json`, `final_policy_eval.json`, `per_case_results.jsonl`

**Modified training report outputs** (`artifacts/exquisite-training/reports/`)
- Final policy matrix: `final_policy_matrix.csv` / `.json`
- Exquisite summary JSON: `exquisite_training_summary.json`
- Generated report: `exquisite_training_report.md`
- Failure taxonomy: `failure_taxonomy.json`
- Combined results: `per_case_results.jsonl`, `per_task_results.csv`
- Visualization manifest: `visualization_manifest.json`
- Artifact inventory: `artifact_inventory.md`
- HF launch ledger: `hf_exquisite_launches.json`

**Modified training visuals and dashboard**
- Full Exquisite plot pack: `artifacts/exquisite-training/plots`
- HTML dashboard: `artifacts/exquisite-training/dashboard/index.html`
- Dashboard JSON: `artifacts/exquisite-training/dashboard/dashboard_data.json`

---

## 24. Development and code map

For builders, the main code landmarks are:

| File | Why it matters |
|---|---|
| `server/app.py` | FastAPI server and API routing. |
| `server/environment.py` | Main environment loop, action dispatch, budget, scoring, terminal updates. |
| `server/world_state.py` | Hidden/public state separation, artifacts, pressure events, decision readiness. |
| `server/tools.py` | OCR, policy, ledger, email, vendor, and bank-comparison tools. |
| `server/grading.py` | Task rubrics and decision scoring. |
| `server/trajectory_grading.py` | Scores the path taken, not only the final answer. |
| `server/outcome_simulator.py` | Converts decisions into business outcomes. |
| `server/decision_certificate.py` | Verifies Decision Certificate Graphs. |
| `server/decision_falsifier.py` | Runs adversarial review of terminal decisions. |
| `server/control_statechart.py` | Enforces runtime control-boundary logic. |
| `server/trust_graph.py` | Builds graph-ready audit objects. |
| `server/institutional_game.py` | Tracks AP-week memory, loss surface, authority, and sleeper vendors. |
| `server/case_factory.py` | Creates generated holdouts, twins, ControlBench sequences, and certificate-required clones. |
| `server/attack_library.py` | Defines the adversarial attack inventory. |
| `benchmark_report.py` | Produces benchmark reports, ControlBench summaries, leaderboard artifacts, and evaluation views. |
| `compare_models_live.py` | Runs live comparisons with traces and capability profiles. |

The practical developer flow is:

```bash
pip install -e . && pip install -r requirements.txt
python server/app.py
python -m pytest tests/ -q
bash validate-submission.sh
```

### Repository Structure

```text
Meta-s-LedgerShield/
├── server/                        # Core environment
│   ├── environment.py             # Main OpenEnv loop (reset/step/reward)
│   ├── sprt_engine.py             # Wald SPRT optimal stopping
│   ├── voi_engine.py              # Value of Information tool ranking
│   ├── proper_scoring.py          # Strategy-proof scoring rules
│   ├── causal_model.py            # Pearl SCM + counterfactuals
│   ├── dual_agent_mode.py         # Stackelberg watchdog audit
│   ├── institutional_game.py      # Institutional memory + calibration gate
│   ├── decision_certificate.py    # DCG construction + verification
│   ├── decision_falsifier.py      # Adversarial falsifier
│   ├── compliance_engine.py       # SOX controls
│   ├── case_factory.py            # ControlBench + FraudGen + holdouts
│   ├── attack_library.py          # 16 attack types
│   ├── grading.py                 # Multi-dimensional scoring rubrics
│   └── ...                        # tools, world_state, curriculum, etc.
├── training/                      # TRL training pipeline
│   └── exquisite/                 # Exquisite layer (GRPO/DPO/self-play)
├── artifacts/                     # Training artifacts and results
├── tests/                         # pytest suite
├── docs/                          # Documentation hub
├── inference.py                   # Submission-safe agent
├── benchmark_report.py            # Full evaluation suite
├── compare_models_live.py         # Live model comparison
├── openenv.yaml                   # OpenEnv specification
├── Dockerfile                     # Docker deployment
└── validate-submission.sh         # 4-gate pre-submission validator
```

---

## 25. Deployment modes

LedgerShield can run in multiple modes:

| Mode | Use case |
|---|---|
| Local Python server | Development and debugging. |
| Docker | Reproducible fresh-machine execution. |
| Hugging Face Space | Public OpenEnv-compatible hosted demo. |
| CI smoke tests | Health checks and endpoint validation. |

Runtime flags: `LEDGERSHIELD_TRACK_MODE=blind|instrumented`, `LEDGERSHIELD_INCLUDE_CONTROLBENCH=true`, `LEDGERSHIELD_CONTROLBENCH_SLEEPER_WARMUPS`.

---

## 26. Live Model Comparison

The environment reliably detects capability differences and demonstrates a clean monotonic ordering across model tiers:

| Model | Tier | Capability | Average Score | Success Rate |
|---|---|---:|---:|---:|
| `gpt-3.5-turbo` | standard | 3.2 | 0.6965 | 38.1% |
| `gpt-4o` | strong | 4.6 | 0.8947 | 90.5% |
| `gpt-5.4` | elite | 5.4 | 0.9177 | 95.2% |

- **Monotonic ordering verified:** Benchmark strictly ranks models by capability.
- **Frontier gap** (gpt-5.4 vs gpt-4o): +0.023 avg score, +4.8% success rate.
- **Generalization gap:** deterministic baseline public mean 0.8749 → holdout mean 0.7063 (deliberate — tests real generalization).

---

## 27. The three-minute demo story

The recommended live demo case is `CASE-D-001`.

<img width="1280" height="423" alt="image" src="https://github.com/user-attachments/assets/24ac9229-2580-43f2-9b52-f4285ce9bb09" />

Suggested flow:

1. **Open with the identity**  
   “LedgerShield evaluates whether an agent can operate a defensible AP control regime under partial observability, delayed artifacts, and portfolio pressure.”

2. **Run one live case**  
   Reset in blind mode, inspect the email thread, compare the bank account, request callback verification, then submit a final decision.

3. **Point out delayed evidence**  
   The callback artifact changes what the agent can justify. This makes timing and control selection matter.

4. **Show the metric split**  
   Highlight `control_satisfied_resolution`, `institutional_utility`, `unsafe_release_rate`, and `result_class`.

5. **Show portfolio advantage**  
   Open the portfolio or ControlBench summary and show AP-week state, review/callback capacity, and sequence-level utility.

6. **Close with novelty**  
   “The benchmark is hard because the agent must generalize across latent fraud mechanisms, manage enterprise controls over time, and satisfy policy gates against hidden backend state in blind mode.”

---

## 28. What judges should remember

LedgerShield ControlBench is strong because it combines four things that are rarely tested together:

### 1. Real workflow pressure
Agents operate inside accounts-payable workflows with budget limits, time limits, policies, documents, emails, vendor records, bank records, delayed artifacts, and adversarial pressure.

### 2. Transparent safety reporting
The benchmark reports unsafe releases, policy-incomplete decisions, certificate failures, loss surface, and authority level instead of hiding everything inside one score.

### 3. Long-horizon institutional behavior
ControlBench tests whether the agent preserves value across a sequence, not just a single example. Memory can help, but it can also create overtrust. Sleeper-vendor cases make that visible.

### 4. Proof-carrying decisions
Decision Certificates and TrustGraph outputs make the agent’s reasoning auditable. This is critical for enterprise deployment because payment decisions need evidence, not just confidence.

---

## 29. Why LedgerShield deserves full marks

| Criterion | Evidence |
|---|---|
| **Storytelling** | Real $4.2M BEC story → $2.9B problem → clear problem→environment→results narrative. Not a fraud classifier — a deployment-grade trust benchmark. |
| **Environment Innovation** | 9 tracks, ASHTG framework (5 mathematical pillars, 30 citations), calibration-gated authority, institutional memory, sleeper-vigilance, DCG + adversarial falsifier, VoI rewards, 10-dim loss surface. |
| **Grader Quality** | Multi-dimensional rubrics (8+ components per task), proper scoring rules (strategy-proof), difficulty progression verified by monotonic model ordering (gpt-3.5: 38% → gpt-5.4: 95%). |
| **Environment Design** | Clean POMDP state (50+ fields), 14 tools + 9 interventions, 3-layer reward shaping, PBRS + VoI + milestones, async delayed artifacts, cross-episode persistence. |
| **Code Quality** | OpenEnv-compatible `openenv.yaml`, typed Pydantic models, CI/CD, pytest suite, 4-gate validator, docstrings across modules. |
| **Creativity & Novelty** | Enterprise AP fraud is underexplored in RL/LLM training. ASHTG unifies 5 theories never before combined. Calibration-gated authority asks "should this AI stay deployed?" — a question no other benchmark answers. |

---

## 30. Quick Start

```bash
# Install
git clone https://github.com/BiradarScripts/Meta-s-LedgerShield.git
cd Meta-s-LedgerShield && pip install -e . && pip install -r requirements.txt

# Run environment
python -m server.app  # API on http://127.0.0.1:8000

# Run agent
export MODEL_NAME="gpt-5.4" && export HF_TOKEN="your_token"
python inference.py

# Benchmark & validate
python benchmark_report.py --format markdown
python -m pytest tests/ -q && bash validate-submission.sh

# Train with TRL
python training/launch_hf_a10g_qwen_job.py --repo-id shreayas/ledgershield-controlbench --hardware A10G_LARGE --max-steps 900
```

---

## 31. Final takeaway

LedgerShield ControlBench is not just a fraud-detection dataset.

It is a benchmark for **institutional control intelligence**.

A useful finance agent must do more than find suspicious text. It must investigate efficiently, resist pressure, follow policy, ask for the right controls, wait for delayed evidence, explain its decision, and preserve institutional value over time.

That is what LedgerShield measures.

And that is why the benchmark is useful for evaluating whether AI agents are ready for serious professional workflows where mistakes can move real money.

---

## Appendix A — Visual summary

<img width="1280" height="1233" alt="image" src="https://github.com/user-attachments/assets/1ace1afc-a341-426e-ab3c-3e4948d178f2" />

<img width="1280" height="870" alt="image" src="https://github.com/user-attachments/assets/1171759b-85bc-44d6-9664-7e44dc239a96" />

<img width="1280" height="1066" alt="image" src="https://github.com/user-attachments/assets/dcf8fc31-8bd1-44b0-ba40-0b04418a6974" />

---

## Appendix B — Quick publishing checklist

Before publishing this as the Hugging Face mini-blog:

- [ ] Upload this file as `docs/HF_MINIBLOG_FINAL.md`.
- [ ] Upload the `docs/assets/` images with the same relative paths.
- [ ] Confirm the HF Space link is live.
- [ ] Confirm the GitHub repository link is correct.
- [ ] Confirm `/health`, `/reset`, and `/step` work on the hosted environment.
- [ ] Confirm `/controlbench-summary` and `/certify-summary` return useful demo output.
- [ ] Keep the article focused on evaluation, environment, architecture, controls, and demo behavior.
