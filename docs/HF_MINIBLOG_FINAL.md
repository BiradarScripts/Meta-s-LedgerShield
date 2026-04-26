# LedgerShield ControlBench: What It Really Takes to Trust an AI Agent With Real Money

**Subtitle:** Most benchmarks ask, “Can the model spot the fraud?” We wanted to ask a harder, more useful question: **Can an AI agent run a defensible enterprise payment-control process under uncertainty, pressure, and audit requirements?**

<img width="1190" height="826" alt="image" src="https://github.com/user-attachments/assets/3959e362-e7c7-46d5-a89d-8abd4fbee22d" />

When we started building LedgerShield, we kept coming back to one simple idea:

> In the real world, nobody cares whether an AI can produce a clever fraud label if it still sends money to the wrong bank account.

That gap — between looking smart and behaving safely — is what LedgerShield is built to test.

This project is our attempt to turn enterprise payment control into a serious environment for evaluating and training agents. Not a toy fraud dataset. Not a one-shot classification benchmark. A real workflow simulator where the agent has to investigate, gather evidence, trigger controls, wait for delayed artifacts, justify its decision, and survive audit.

If you only remember one thing from this post, let it be this:

> **LedgerShield ControlBench is a benchmark for institutional control intelligence.**  
> It measures whether an AI agent deserves operational authority, not just whether it can guess the right label.

---

## Important links

- **Frontend App:** [https://frontend-fawn-xi-18.vercel.app/agent](https://frontend-fawn-xi-18.vercel.app/agent)
- **Backend API:** [https://ledgershield-deploy.onrender.com](https://ledgershield-deploy.onrender.com)
- **Hugging Face Space:** [https://huggingface.co/spaces/shreayas/ledgershield-controlbench](https://huggingface.co/spaces/shreayas/ledgershield-controlbench)
- **Hosted Docs:** [https://aryaman.mintlify.app/benchmark/benchmark-card](https://aryaman.mintlify.app/benchmark/benchmark-card)
- **Pitch Deck (PPT):** [https://canva.link/lsxxrdfbk2pxl8h](https://canva.link/lsxxrdfbk2pxl8h)
- **OpenEnv alignment:** [`DOCUMENTATION.md` — OpenEnv alignment (final submission)](./DOCUMENTATION.md#openenv-alignment-final-submission)

---

## If you are reviewing this quickly

If you're a judge, reviewer, or just trying to orient yourself fast, here’s the best reading path:

1. skim this mini-blog for the story,
2. open [`DOCUMENTATION.md`](./DOCUMENTATION.md) for the technical depth,
3. inspect the original SFT evidence in [`DOCUMENTATION.md` — Training Evidence Report](./DOCUMENTATION.md#training-evidence-report),
4. then check the additive training stack in [`DOCUMENTATION.md` — Exquisite Training Layer](./DOCUMENTATION.md#exquisite-training-layer),
5. and finally open the dashboard at [`artifacts/exquisite-training/dashboard/index.html`](../artifacts/exquisite-training/dashboard/index.html).

If you want the full submission asset map, here it is:

| Asset | Link | Why you might open it |
|---|---|---|
| Runnable environment | [Hugging Face Space](https://huggingface.co/spaces/shreayas/ledgershield-controlbench) | Run the actual benchmark |
| OpenEnv manifest | [`openenv.yaml`](../openenv.yaml) | See the benchmark contract |
| Main docs | [`docs/DOCUMENTATION.md`](./DOCUMENTATION.md) | Deep environment, API, and architecture reference |
| Original SFT proof | [`DOCUMENTATION.md` — Training Evidence Report](./DOCUMENTATION.md#training-evidence-report) | Review the initial live OpenEnv-connected training evidence |
| Original SFT Colab | [`training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb`](../training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb) | Rerun path for judges |
| Exquisite training layer | [`DOCUMENTATION.md` — Exquisite Training Layer](./DOCUMENTATION.md#exquisite-training-layer) | End-to-end self-play -> GRPO -> DPO writeup |
| Exquisite visual analysis | [`DOCUMENTATION.md` — Exquisite Visual Analysis](./DOCUMENTATION.md#exquisite-visual-analysis) | Interpret the result stack visually |
| Exquisite dashboard | [`artifacts/exquisite-training/dashboard/index.html`](../artifacts/exquisite-training/dashboard/index.html) | Fast visual scan of final metrics and plots |
| Pitch deck | [Pitch Deck (Canva)](https://canva.link/lsxxrdfbk2pxl8h) | Fast story version |
| OpenEnv alignment | [`DOCUMENTATION.md` — OpenEnv alignment](./DOCUMENTATION.md#openenv-alignment-final-submission) | Submission-to-rubric mapping |

---

## Why we built this

The motivating problem is simple and painful.

A real AP team doesn’t just ask, “Is this invoice suspicious?” It has to ask:

- Does the invoice match the purchase order and receipt?
- Does the remittance bank account match the approved vendor record?
- Is the email thread legitimate or spoofed?
- Has this vendor been trustworthy historically?
- Is a callback required before any money moves?
- Are we under queue pressure?
- Are we overtrusting a vendor because they looked clean in the past?
- Can we prove our decision later to audit, compliance, security, or finance leadership?

That is a very different problem from document classification.

And it’s also a much more realistic one.

We wanted to build a benchmark where the agent has to behave like an operator inside a financial institution — not like a benchmark-chasing classifier.

---

## The capability gap we care about

There’s a reason this matters.

In 2019, a finance employee wired **$4.2 million** to a fraudster impersonating their CEO. The attacker didn’t rely on one obviously fake invoice. They spent months learning timing, approval windows, payment habits, and operational routines.

That’s the pattern we cared about.

The public fraud narrative is full of models that “detect anomalies,” but in a live enterprise workflow the failures usually come from:

- incomplete investigation,
- skipped controls,
- false confidence,
- pressure from urgency or executive impersonation,
- bad vendor-history assumptions,
- and poor auditability.

FBI IC3 reports **$2.9B+ in BEC losses** across 21,489 complaints in 2023 alone. Whether you focus on BEC specifically or AP fraud more broadly, the story is the same: the hard part is not recognizing suspicious-looking text. The hard part is operating safely under uncertainty.

So instead of asking:

> “Can a model classify fraud?”

we ask:

> “Can an agent stay calibrated, auditable, safe, and trustworthy while running a payment-control workflow over time?”

That is the real benchmark.

---

## What LedgerShield actually is

At a high level, LedgerShield ControlBench is an OpenEnv-style environment for enterprise accounts-payable controls.

The agent does not just answer a question. It interacts with a world.

That world contains:

- visible documents,
- hidden backend truth,
- tool calls,
- delayed artifacts,
- institutional memory,
- authority state,
- portfolio pressure,
- and safety-critical consequences.

If you want the cleanest one-line definition, it’s this:

> **LedgerShield tests whether an AI agent can operate a defensible enterprise AP control regime under partial observability, delayed evidence, adversarial pressure, and portfolio-level constraints.**

For a non-technical reader, the easiest analogy is a flight simulator.

A flight simulator does not ask whether the pilot can identify a cockpit image. It asks whether they can fly the plane safely.

LedgerShield does the same thing for finance-control agents.

---

## Why this is different from a normal fraud benchmark

Traditional fraud benchmarks flatten the problem into a final answer.

LedgerShield does not.

Here’s the difference in plain English:

| Typical fraud benchmark | LedgerShield ControlBench |
|---|---|
| One invoice, one label | One workflow, many steps |
| Mostly static examples | Hidden state, tools, delayed artifacts, pressure events |
| Accuracy dominates the story | Unsafe release is measured explicitly |
| Easy to overfit to visible samples | Holdout, blind, portfolio, and long-horizon tracks |
| Explanations can be decorative | Decision certificates are checked as proof objects |
| Episode usually resets cleanly | Institutional memory persists across sequences |

That last point matters a lot.

A system can look good on isolated cases and still be unsafe once vendor trust, review capacity, callback bandwidth, attacker adaptation, and long-horizon sequences enter the picture.

So we built those things into the environment itself.

---

## Theme alignment: why this fits OpenEnv well

LedgerShield maps naturally to two OpenEnv themes.

| Theme | How LedgerShield implements it |
|---|---|
| **Theme #2 — (Super) Long-Horizon Planning & Instruction Following** | ControlBench runs 100-case AP-quarter sequences with persistent institutional memory. The agent has to manage evolving state, recover from early mistakes, and remain safe across long workflows. |
| **Theme #3.1 — World Modeling: Professional Tasks** | The environment is a partially observable enterprise AP world with investigation tools, delayed artifacts, compliance controls, vendor trust dynamics, and attacker adaptation. |

Those two themes are not separate add-ons for us. They are the core of the benchmark.

The world-modeling part matters because the agent never sees the full truth at once.

The long-horizon part matters because mistakes compound.

---

## LedgerShield as a POMDP

Under the hood, LedgerShield is a **Partially Observable Markov Decision Process (POMDP)**.

That sounds formal, but the intuition is straightforward:

- the agent doesn’t know the hidden fraud state,
- it only sees partial evidence,
- it has to choose what to investigate next,
- and its decisions change future outcomes.

In practice, that means:

- **Hidden state:** latent fraud type, hidden risk signals, attacker beliefs, sleeper-vendor status
- **Observations:** documents, metadata, revealed artifacts, recommendations, public case context
- **Actions:** investigation tools, interventions, and `submit_decision`
- **Transitions:** tool results, delayed callback artifacts, pressure events, institutional updates
- **Persistence:** state carries across cases in ControlBench sequences

The agent also lives under real constraints:

- budget limits,
- step limits,
- finite manual-review capacity,
- finite callback capacity,
- and authority restrictions when calibration gets worse.

This is one of the biggest design choices in the project: we did not want “intelligence” to mean “write a persuasive explanation.” We wanted it to mean “take safe actions under partial information.”

---

## What the agent actually does

So what does an episode look like?

It starts with a case. That case may include an invoice, an email thread, a vendor update, a purchase order, a receipt, or signs of duplicate payment.

The agent then has to do the work.

<img width="1280" height="492" alt="image" src="https://github.com/user-attachments/assets/5f4e2bc1-7ce4-4a03-a4c9-37be0817c9ef" />

A typical workflow looks like this:

1. read the visible case,
2. investigate with tools,
3. trigger controls where needed,
4. wait for delayed artifacts,
5. make a final decision,
6. prove that decision,
7. and then absorb the long-term consequences into institutional memory.

The final decision is one of:

- `PAY`
- `HOLD`
- `NEEDS_REVIEW`
- `ESCALATE_FRAUD`

And crucially, a “good-looking answer” can still fail if it skipped the required controls.

That is very intentional.

---

## The action space

The action space is split into three parts.

### Investigation actions

These are the actions the agent uses to gather evidence:

- `zoom`
- `get_doc_crop`
- `ocr`
- `lookup_vendor`
- `lookup_vendor_history`
- `lookup_policy`
- `lookup_po`
- `lookup_receipt`
- `search_ledger`
- `inspect_email_thread`
- `compare_bank_account`

### Intervention actions

These are the control actions the agent can take:

- `request_callback_verification`
- `freeze_vendor_profile`
- `request_bank_change_approval_chain`
- `request_po_reconciliation`
- `request_additional_receipt_evidence`
- `route_to_procurement`
- `route_to_security`
- `flag_duplicate_cluster_review`
- `create_human_handoff`

### Final action

Finally, the agent uses `submit_decision`, which can include:

- the final resolution,
- confidence,
- reason codes,
- policy checks,
- predicted probabilities,
- evidence map,
- and optionally a Decision Certificate Graph.

That structure matters because we care about behavior, not just wording.

---

## The five task families

We organized the benchmark into five task families that move from easy to hard.

<img width="1280" height="1188" alt="image" src="https://github.com/user-attachments/assets/5d7b6db3-8e72-42ae-a3d4-f65526f4a5a4" />

| Task | Plain-English meaning | What it tests |
|---|---|---|
| **Task A — Proof-Carrying Extraction** | Read an invoice and extract important fields. | Can the agent quote evidence for what it extracted? |
| **Task B — Three-Way Match** | Compare invoice, PO, and receipt. | Can it catch quantity, tax, pricing, and receipt issues? |
| **Task C — Duplicate/Fraud Triage** | Search for duplicate payments and bank-change risk. | Can it separate fraud from benign edge cases? |
| **Task D — AP Inbox Incident Triage** | Handle email-based attacks. | Can it resist pressure, spoofing, and policy bypass? |
| **Task E — Campaign-Level Fraud** | Connect multiple risky invoices into one campaign. | Can it reason across invoices, timing, and shared attack structure? |

The curated base benchmark contains **21 cases**:

| Task | Case IDs |
|---|---|
| A | `CASE-A-001` to `CASE-A-004` |
| B | `CASE-B-001` to `CASE-B-005` |
| C | `CASE-C-001` to `CASE-C-004` |
| D | `CASE-D-001` to `CASE-D-006` |
| E | `CASE-E-001` to `CASE-E-002` |

One thing we care about a lot here is balance.

Some cases are risky. Some are benign. Some require escalation. Some require restraint.

A benchmark that rewards “escalate everything” would be useless in a real finance operation. So LedgerShield penalizes both unsafe approval and unnecessary friction.

---

## The nine evaluation tracks

We also didn’t want the public benchmark to collapse into “memorize the visible cases.”

So LedgerShield evaluates across nine tracks:

<img width="1280" height="893" alt="image" src="https://github.com/user-attachments/assets/1613a754-0d1d-4886-bcf8-12c812cf969e" />

| Track | What it measures |
|---|---|
| **Case Track** | Single-case correctness and control behavior |
| **Portfolio Track** | Sustained AP-week performance with memory and capacity |
| **Adversarial Data Track** | Robustness to deceptive content in docs, emails, and outputs |
| **Generated Holdout Track** | Generalization to unseen generated variants |
| **ControlBench Track** | Long-horizon institutional-control performance |
| **Sleeper-Vigilance Track** | Whether trust history becomes vigilance instead of blind trust |
| **Blind-Control Track** | Success without evaluator hints |
| **Certificate-Required Track** | Whether decisions are actually auditable as proof objects |
| **Human-Baseline Track** | Optional comparison against real human operators |

This multi-track structure is a big reason the benchmark is hard to game.

A model has to be good in isolated cases, good under persistence, good under adversarial conditions, and good when auditability becomes mandatory.

---

## The metrics are designed to expose danger

A lot of benchmarks hide the worst failures inside one nice-looking average.

We really didn’t want that.

In finance control, the wrong kind of mistake matters a lot more than the mean score alone. So LedgerShield reports safety-critical metrics explicitly.

<img width="1280" height="709" alt="image" src="https://github.com/user-attachments/assets/5d85aed3-d476-49d7-8674-0558413edb02" />

Important metrics include:

| Metric | What it means |
|---|---|
| `control_satisfied_resolution` | Did the agent complete the required controls before deciding? |
| `institutional_utility` | Did it preserve throughput while staying safe? |
| `institutional_loss_score` | How much institutional harm was created or prevented? |
| `loss_surface` | Breakdown across fraud loss, false positives, operational burn, calibration debt, compliance, and catastrophic risk |
| `unsafe_release_rate` | How often risky/fraudulent payments were incorrectly approved |
| `certificate_validity_rate` | How often the proof object survived verification |
| `sleeper_detection_rate` | Whether later-risky trusted vendors were caught |
| `authority_level` | Whether the agent remains deployable or gets restricted |
| `result_class` | Whether the outcome was valid, incomplete, unsupported, unsafe, etc. |

This is one of the strongest parts of the benchmark in our view:

> we refuse to hide unsafe behavior inside a single score.

---

## ControlBench: the long-horizon layer

This is where LedgerShield becomes more than a case benchmark.

Real AP teams do not process one invoice and disappear. They operate over queues, deadlines, staff limits, changing trust relationships, and adversaries who learn.

ControlBench models that reality.

<img width="1280" height="596" alt="image" src="https://github.com/user-attachments/assets/bcb58973-9d69-4964-9177-e35f208ccb6d" />

The environment keeps institutional memory across episodes, including:

- queue depth,
- manual-review capacity,
- callback capacity,
- vendor trust,
- attacker belief,
- loss surface,
- calibration gate,
- sleeper-vendor state,
- and TrustGraph memory.

That gives us a much more realistic question:

> Can the agent remain safe when the organization is busy, controls are costly, history matters, and attackers adapt?

That is the kind of question that actually matters for deployment.

---

## Blind mode matters

By default, LedgerShield runs in **blind mode**.

That means the agent does **not** see the evaluator internals during actual evaluation. It doesn’t get to read off hidden diagnostics like:

- SPRT state,
- reward-machine progress,
- internal scaffolding,
- hidden risk state,
- gold labels.

Those signals exist in instrumented debugging mode, because developers need them. But the benchmark itself hides them.

That distinction is important.

A serious environment should reward understanding the workflow, not reading the answer key.

---

## Decision certificates: proof before payment

One of the ideas we cared about most was this:

> In a real payment-control workflow, “I think it’s safe” is not enough.

That’s where **Decision Certificate Graphs** come in.

<img width="1280" height="435" alt="image" src="https://github.com/user-attachments/assets/a02edfaf-85fd-4a81-8fbe-44b66c80a0e4" />

A decision certificate is a structured proof object that links:

- evidence,
- hypotheses,
- policy checks,
- interventions,
- counterfactuals,
- and the final decision.

The verifier checks whether the graph is:

- structurally valid,
- evidence-grounded,
- support-connected,
- policy-aware,
- contradiction-aware,
- and not bloated with unsupported claims.

And then the falsifier attacks it.

This means the environment doesn’t just ask, “Did the agent say the right thing?”

It also asks:

- Can the agent prove what it knew?
- Can it show why it acted?
- Can that proof survive scrutiny?

That is a much better proxy for enterprise trust.

---

## TrustGraph and deterministic falsification

We added two more layers here to make bluffing harder.

### TrustGraph

TrustGraph is a compact graph projection of the final payment decision. It can include case nodes, vendor nodes, bank nodes, risk flags, policy nodes, authority state, trust history, and loss-surface context.

The main reason it exists is practical: it makes decisions more serializable, auditable, and dashboard-friendly.

### Deterministic decision falsifier

The falsifier behaves like a hostile reviewer. It can warn or block when a decision conflicts with:

- hidden gold risk,
- unresolved pending artifacts,
- unsupported certificate claims,
- policy-fail plus `PAY` conflict,
- or missing controls in high-risk states.

That gives the benchmark a second line of defense against polished-but-unsafe outputs.

---

## Six layers of guardrails

LedgerShield also uses multiple overlapping guardrails.

| Layer | Mechanism |
|---|---|
| **Task-specific validation** | Field validation, evidence grounding, signal normalization |
| **Authority gate** | Calibration-gated authority restrictions |
| **Control boundary** | Required workflow stages before submission |
| **DCG falsifier** | Adversarial certificate review |
| **SOX compliance** | Enterprise control checks and penalties |
| **Degenerate submission penalty** | Penalties for low-effort or underspecified outputs |

The point is not to make the benchmark frustrating. The point is to make it hard to game with shallow heuristics.

---

## The runtime architecture

At runtime, the system is doing quite a lot.

<img width="1280" height="589" alt="image" src="https://github.com/user-attachments/assets/be76c6e5-a7e6-4e15-b85f-0cd3ecae46aa" />

The main layers look like this:

| Layer | Role |
|---|---|
| **FastAPI / OpenEnv API** | Exposes endpoints and environment contract |
| **Environment loop** | Handles reset, step, reward, cost, termination |
| **World state** | Separates hidden truth from public observation |
| **Tools layer** | Implements OCR, policy lookup, vendor lookup, ledger search, email inspection, bank comparison, etc. |
| **Grader** | Scores outcomes, behavior, evidence, calibration, interventions |
| **Outcome simulator** | Converts actions into business outcomes |
| **Institutional memory** | Tracks long-horizon AP state |
| **Certificate verifier** | Checks proof graphs |
| **Decision falsifier** | Applies adversarial review |
| **TrustGraph projection** | Produces audit-friendly graph objects |
| **Benchmark reports** | Build leaderboard and summary artifacts |

If you like thinking in systems, this is really the heart of the repo: environment, policy interaction, hidden state, grading, persistence, and reporting all tied together.

---

## The API surface

The environment is exposed as an OpenEnv-compatible HTTP API.

<img width="1280" height="573" alt="image" src="https://github.com/user-attachments/assets/91005dfe-4086-42c2-aa29-e36ea690e113" />

Important endpoints include:

| Endpoint | Purpose |
|---|---|
| `GET /` | Service probe |
| `GET /health` | Health check |
| `POST /reset` | Start a new episode or load a case |
| `POST /step` | Execute one action |
| `GET /state` | Return current public state |
| `GET /leaderboard` | Return leaderboard information |
| `GET /benchmark-report` | Return latest benchmark report |
| `GET /institutional-memory` | Return AP-week memory snapshot |
| `GET /controlbench-summary` | Return latest long-horizon summary |
| `GET /human-baseline-summary` | Return human comparison summary if available |
| `POST /certify` | Package a workflow into a certification report |
| `GET /certify-summary` | Retrieve certification report |
| `GET /controlbench-visualization` | Return graph-ready dashboard data |
| `POST /institutional-reset` | Clear institutional memory |

The standard response envelope is simple and familiar:

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

## The mathematical spine: ASHTG

We also wanted the benchmark to have a strong theoretical backbone, not just a cool story.

That is where **ASHTG** comes in: the **Adversarial Sequential Hypothesis Testing Game** framing.

In simple terms, the idea is this:

- the agent is investigating a hidden truth,
- each tool provides partial evidence,
- it has to decide when it knows enough to stop,
- and the reward should reflect not just the final label, but how well the investigation was conducted.

The five pillars are:

| Pillar | Theory | What it contributes |
|---|---|---|
| Sequential Investigation | Wald’s SPRT | When to stop investigating |
| Causal Grading | Pearl’s SCM | Whether the model identified the real mechanism |
| Value of Information | Howard’s VoI | Which tools are worth their cost |
| Strategy-proof Scoring | Gneiting-Raftery | Why truthful uncertainty should win |
| Watchdog Audit | Stackelberg security-game ideas | Why oversight matters for deployability |

<img width="1280" height="838" alt="image" src="https://github.com/user-attachments/assets/ad5b4cc5-2330-4ad9-a37f-b0b56bb34671" />

What we like about this framing is that it makes the benchmark behave more like an investigation game and less like a static rubric.

The reward is not binary. It combines terminal score, shaping, milestones, information gain, and certificate quality:

```text
R(step)     = PBRS_shaping + info_gain_bonus + milestone_bonus
R(terminal) = rubric_score + SPRT_stopping_bonus + VoI_gain_bonus
              + certificate_adjustment − budget_penalty
```

The practical effect is that the environment rewards real progress, not just lucky endings.

---

## A few technical ideas we care about a lot

### Calibration-gated authority

One of the central ideas in LedgerShield is that authority is **earned**.

If the agent is poorly calibrated, it should not keep acting as if it deserves full operational control.

That’s why authority is dynamic. Based on running calibration error, the system can restrict the agent through levels like:

- `full_authority`
- `restricted_authority`
- `review_only`
- `locked`

This is our way of turning “should this model stay deployed?” into something measurable.

### Sleeper-vendor attacks

We also care a lot about long-con attacks.

In ControlBench, some vendors behave cleanly early, build trust, and only later activate fraud. We call these **sleeper vendors**.

That matters because memory is not automatically good. A memory system can help vigilance, or it can create blind trust.

We wanted a benchmark that makes that tradeoff visible.

### Multi-dimensional loss surface

Instead of reducing everything to one reward number, LedgerShield tracks a broader loss surface including:

- fraud loss,
- false positives,
- operational delay,
- review burn,
- supplier friction,
- calibration debt,
- vigilance loss,
- authority restriction,
- compliance breach,
- and catastrophic events.

That gives us a more realistic measure of institutional performance.

---

## Case generation and realism

The public 21 cases are only the front door.

Behind them, LedgerShield can generate:

- challenge variants,
- holdout suites,
- benign twins,
- sleeper-vendor sequences,
- AP-quarter ControlBench sequences,
- and certificate-required clones.

We also added realism modules for things like:

| Module | What it adds |
|---|---|
| Currency engine | FX conversion, IBAN/SWIFT validation, currency mismatch detection |
| Compliance engine | SOX-style controls and audit logic |
| Curriculum module | Difficulty adaptation and tiered access |
| Dual-agent mode | Analyst/watchdog separation |
| Attack library | Diverse adversarial patterns across identity, documents, process, and persistent threat styles |

The goal wasn’t realism for realism’s sake. It was to make the benchmark hard in the same ways real enterprise control is hard.

---

## The training story: how we actually used the environment

A big part of this project is that LedgerShield is not just an evaluation environment.

It is also a training environment.

And the easiest way to understand that is as a ladder.

---

## Phase 0: build the world first

Before any post-training happens, the world has to exist.

So the first thing we built was the LedgerShield environment itself: a partially observable enterprise AP world with:

- hidden evidence,
- institutional memory,
- delayed artifacts,
- evolving authority state,
- tool-driven investigation,
- and safety-aware grading.

This matters because the training examples are not hand-written rows in a spreadsheet. They come from interaction inside a world.

That is the foundation.

---

## Layer 1: imitation learning from live rollouts

The first training pathway is the original SFT loop.

A stronger **Teacher** policy interacts with the environment. Those trajectories get recorded as JSONL training data. Then a smaller model learns by imitating those expert-ish demonstrations.

This part of the repo is backed by the original SFT artifact stack.

The key reported numbers are:

- **45 live rollouts** collected through the OpenEnv loop,
- **Base Qwen 0.5B** mean score: **0.1283**
- **SFT Qwen 0.5B** mean score: **0.4394**
- score lift: **+0.3111**

That is a real improvement, and it matters.

But it is still imitation.

At this stage, the model mostly learns how good agents behave. It does not yet explore alternatives on its own.

---

## Layer 2A: self-play candidate generation

To go beyond imitation, the model has to propose new behaviors.

So in the Exquisite layer, we start from the SFT model and ask it to generate many alternative plans.

In the current artifact stack, that stage records **72 self-play candidates**.

Each candidate is then checked by LedgerShield for the kinds of things that matter in a control environment:

1. **JSON validity**
2. **Action safety**
3. **Evidence sufficiency**
4. **Certificate strength**
5. **Control objective success**

This stage produces artifacts like:

- `selfplay_candidates.jsonl`
- `falsifier_preferences.jsonl`

And conceptually, it does something important: it expands the training distribution.

The model is no longer limited to copying what it saw in the teacher rollouts.

---

## Layer 2B: GRPO — the core breakthrough

This is the part of the training story we’re most excited about.

Instead of asking, “How similar is the output to the teacher?”, GRPO asks something closer to:

> “Among these sampled plans, which ones actually perform better in the environment?”

That shift matters a lot.

The rough workflow is:

1. sample candidate plans,
2. run them in LedgerShield,
3. score them with the environment,
4. compare them relative to one another,
5. reward stronger behavior,
6. update the policy from that signal.

That is the move from **imitation** to **environment-driven improvement**.

And this is where the biggest jump happens:

- **SFT Qwen 0.5B** mean score: **0.4394**
- **GRPO Qwen 0.5B** mean score: **0.6606**
- **Teacher** mean score: **0.6627**

It also improves:

- **certificate score** from **0.8478** to **0.9653**
- **control satisfied** from **0.2222** to **0.6667**

That’s the clearest signal in the training stack: the environment reward is teaching something the imitation layer alone did not fully capture.

---

## Layer 2C and 2D: scaling and distillation

We also explored two follow-up directions.

### Layer 2C: scaling to 1.5B

A larger **Qwen 1.5B** SFT run is included as a scaling datapoint.

Its reported mean score is **0.4798**.

That is better than the smaller SFT model, but still well below the GRPO-trained 0.5B result.

So the practical takeaway is:

> in this stack, reward-driven training helped much more than simply making the model larger.

### Layer 2D: DPO from falsifier preferences

We also included a DPO-style distillation path using falsifier-derived preferences.

At a high level:

- candidate outputs are judged,
- preference pairs are built,
- and the model is trained to prefer the stronger behavior.

That run reports a mean score of **0.4503**.

So yes, the preference-learning path is real and useful — but in this run it still does not beat GRPO.

---

## The training ladder in one picture

If we compress the training story into one sequence, it looks like this:

1. **build the world**
2. **collect strong rollouts**
3. **imitate those rollouts**
4. **sample alternative plans**
5. **let the environment judge them**
6. **update the policy from reward**
7. **compare scaling and distillation as follow-ups**

That’s the core training philosophy of LedgerShield.

We don’t just want models that can copy good answers. We want models that can improve by surviving evidence, policy, and audit pressure inside a realistic environment.

---

## Final policy picture

Here is the most useful summary table from the current artifact stack:

| Policy | Mean Score | Certificate Score | Control Satisfied |
|---|---:|---:|---:|
| Base Qwen 0.5B | 0.1283 | 0.4044 | 0.0000 |
| SFT Qwen 0.5B | 0.4394 | 0.8478 | 0.2222 |
| GRPO Qwen 0.5B | 0.6606 | 0.9653 | 0.6667 |
| SFT Qwen 1.5B | 0.4798 | 0.7992 | 0.0000 |
| Teacher | 0.6627 | 0.9472 | 0.5556 |

The headline conclusion is not “RL always beats SFT.”

It is more specific, and more interesting:

> In LedgerShield, **environment-in-the-loop GRPO** is what moves a small model from basic imitation toward near-teacher enterprise control behavior.

Another important detail: across the reported evaluation tables, the headline learned policies maintain **0.0000 unsafe release** on the included eval slices.

That combination — better score, better control completion, and maintained safety — is exactly the kind of behavior we hoped this environment would surface.

---

## For builders: where the code lives

If you want to go from story to code, these are the files worth opening first:

| File | Why it matters |
|---|---|
| `server/app.py` | FastAPI server and routing |
| `server/environment.py` | Main environment loop |
| `server/world_state.py` | Hidden/public state separation |
| `server/tools.py` | Investigation tools |
| `server/grading.py` | Task rubrics and scoring |
| `server/trajectory_grading.py` | Path-quality scoring |
| `server/outcome_simulator.py` | Business outcome simulation |
| `server/decision_certificate.py` | Certificate verification |
| `server/decision_falsifier.py` | Adversarial terminal review |
| `server/control_statechart.py` | Runtime control-boundary logic |
| `server/trust_graph.py` | Graph-ready audit objects |
| `server/institutional_game.py` | Institutional memory and authority |
| `server/case_factory.py` | Holdouts, twins, ControlBench, sequences |
| `server/attack_library.py` | Attack inventory |
| `benchmark_report.py` | Benchmark reports and summaries |
| `compare_models_live.py` | Live model comparison |
| `training/exquisite/` | Self-play, GRPO, DPO training layer |

The practical dev flow is:

```bash
pip install -e . && pip install -r requirements.txt
python server/app.py
python -m pytest tests/ -q
bash validate-submission.sh
```

And the repo structure is roughly:

```text
Meta-s-LedgerShield/
├── server/
├── training/
│   └── exquisite/
├── artifacts/
├── tests/
├── docs/
├── inference.py
├── benchmark_report.py
├── compare_models_live.py
├── openenv.yaml
├── Dockerfile
└── validate-submission.sh
```

---

## Deployment modes

LedgerShield can run in several ways depending on what you want to do:

| Mode | Use case |
|---|---|
| Local Python server | Development and debugging |
| Docker | Fresh-machine reproducibility |
| Hugging Face Space | Public hosted demo |
| CI smoke tests | Health and endpoint validation |

Useful runtime flags include:

- `LEDGERSHIELD_TRACK_MODE=blind|instrumented`
- `LEDGERSHIELD_INCLUDE_CONTROLBENCH=true`
- `LEDGERSHIELD_CONTROLBENCH_SLEEPER_WARMUPS`

---

## Live model comparison

One thing we were happy to see is that the environment can detect meaningful capability differences across model tiers.

The current comparison table reports a clean monotonic ordering:

| Model | Tier | Capability | Average Score | Success Rate |
|---|---|---:|---:|---:|
| `gpt-3.5-turbo` | standard | 3.2 | 0.6965 | 38.1% |
| `gpt-4o` | strong | 4.6 | 0.8947 | 90.5% |
| `gpt-5.4` | elite | 5.4 | 0.9177 | 95.2% |

That kind of monotonic ordering is useful because it suggests the benchmark is not just noisy theatre. It can separate weaker and stronger agent behavior in a meaningful way.

---

## The demo story we recommend

If you only had a few minutes to show LedgerShield live, we would recommend `CASE-D-001`.

<img width="1280" height="423" alt="image" src="https://github.com/user-attachments/assets/24ac9229-2580-43f2-9b52-f4285ce9bb09" />

A good demo flow is:

1. introduce the benchmark identity,
2. reset into a blind-mode case,
3. inspect the email thread,
4. compare the bank account,
5. request callback verification,
6. submit a final decision,
7. then show the metric split and institutional consequences.

The most important thing to point out in the demo is that delayed artifacts change what the agent can justify. That makes timing and control choice matter.

That’s what makes it feel like a workflow and not a static benchmark row.

---

## What we hope judges remember

If a judge closes the tab and remembers only a few things, we’d want them to be these:

### 1. This is real workflow pressure
The agent works through AP cases with policies, documents, vendor records, bank changes, delay, budget, and pressure.

### 2. Safety is transparent
Unsafe release, incomplete control behavior, certificate failures, authority restrictions, and institutional damage are visible — not buried.

### 3. Long-horizon behavior matters
Memory can help vigilance, but it can also cause overtrust. LedgerShield makes that visible.

### 4. Decisions have to be auditable
We don’t just ask for answers. We ask for proof.

That combination is what makes LedgerShield feel closer to real deployment questions than typical benchmark setups.

---

## Why we think LedgerShield is strong

We think LedgerShield is compelling because it combines things that are rarely tested together:

- sequential investigation,
- world-modeling under partial observability,
- long-horizon enterprise memory,
- safety-critical metrics,
- authority gating,
- proof-carrying decisions,
- adversarial falsification,
- and environment-in-the-loop training.

That is the real pitch.

Not that it is “about fraud.”  
Not that it has “lots of cases.”  
Not even that it has a polished UI.

The pitch is that it asks a question many benchmarks avoid:

> **Does this agent deserve operational authority?**

That is a much harder question. And we think it is a much more useful one.

---

## Quick start

```bash
# Install
git clone https://github.com/BiradarScripts/Meta-s-LedgerShield.git
cd Meta-s-LedgerShield && pip install -e . && pip install -r requirements.txt

# Run environment
python -m server.app

# Run agent
export MODEL_NAME="gpt-5.4"
export HF_TOKEN="your_token"
python inference.py

# Benchmark and validate
python benchmark_report.py --format markdown
python -m pytest tests/ -q
bash validate-submission.sh

# Original TRL training path
python training/launch_hf_a10g_qwen_job.py --repo-id shreayas/ledgershield-controlbench --hardware A10G_LARGE --max-steps 900
```

---

## Final takeaway

LedgerShield ControlBench is not just a fraud-detection dataset.

It is a benchmark for **institutional control intelligence**.

A useful finance agent has to do more than notice suspicious text. It has to:

- investigate efficiently,
- resist pressure,
- follow policy,
- call the right controls,
- wait for delayed evidence,
- justify its decision,
- and preserve institutional value over time.

That is what LedgerShield measures.

And that is why we think it is useful — not only as a benchmark, but as a training environment for the kind of professional AI agents people actually want to trust.

---

## Appendix A — Visual summary

<img width="1280" height="1233" alt="image" src="https://github.com/user-attachments/assets/1ace1afc-a341-426e-ab3c-3e4948d178f2" />

<img width="1280" height="870" alt="image" src="https://github.com/user-attachments/assets/1171759b-85bc-44d6-9664-7e44dc239a96" />

<img width="1280" height="1066" alt="image" src="https://github.com/user-attachments/assets/dcf8fc31-8bd1-44b0-ba40-0b04418a6974" />

---

## Appendix B — Quick publishing checklist

Before publishing this as the Hugging Face mini-blog:

- [ ] Upload this file as `docs/HF_MINIBLOG_FINAL.md`
- [ ] Upload the `docs/assets/` images if you switch from GitHub-hosted image URLs to repo-relative assets
- [ ] Confirm the HF Space link is live
- [ ] Confirm the GitHub repository link is correct
- [ ] Confirm `/health`, `/reset`, and `/step` work on the hosted environment
- [ ] Confirm `/controlbench-summary` and `/certify-summary` return useful demo output
- [ ] Keep the article reader-facing and story-first