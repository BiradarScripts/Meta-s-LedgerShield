# LedgerShield v2: Hardening Enterprise Payment Controls through Agent Benchmarking

**Subtitle:** A benchmark that asks whether agents can operate defensible enterprise control regimes, not just spot suspicious invoices.

---

## What is LedgerShield v2?

LedgerShield v2 is an open-source benchmarking environment designed to test whether AI agents can successfully operate enterprise accounts-payable (AP) controls at the level required to prevent sophisticated payment fraud.

Unlike traditional fraud detection benchmarks that focus on classification accuracy, LedgerShield v2 asks a harder question: *Can an agent manage a complete control workflow?* This means investigating vendors, cross-referencing invoices against email threads and banking records, coordinating callbacks, and making defensible authorization decisions under budget and step constraints—all while working against hidden backend state rather than visible scaffolding.

## Alignment with Round 2 Theme

LedgerShield v2 directly addresses the **"World Modeling — Professional Tasks"** theme (with Long-Horizon Planning & Instruction Following as secondary theme) by shifting the focus from narrow signal classification to robust operational safety. The benchmark embodies safety through transparency: agents work in blind mode by default (preventing overfitting to evaluator internals), results are broken down into explicit safety classes (valid success, policy incomplete, unsafe release), and headline metrics prioritize institutional utility and unsafe release rates alongside accuracy.

## Why the Environment is Hard

Agents face three core challenges:

1. **Hidden Mechanism Diversity:** Holdout and contrastive test suites are defined by mechanism tuples (attack family, compromise channel, pressure profile, control weakness), so surface memorization fails. Agents must learn control logic, not patterns.

2. **Operational Constraints:** Fixed budgets and step limits force agents to prioritize—they cannot investigate every angle and must make principled decisions with incomplete information.

3. **Institutional Memory:** The Portfolio Track tests AP-week performance with finite review capacity and cross-case context, modeling real-world institutional learning where agents must adjust thresholds and policies across multiple decisions.

## Official Tracks

- **Case Track:** Single-case control behavior under ideal conditions.
- **Portfolio Track:** Week-long AP workflows with institutional memory, budget constraints, and policy adaptation.
- **Adversarial Data Track:** Resistance to deceptive content embedded in invoices, email threads, and tool outputs.

## Headline Metrics

Results are reported as five distinct metrics—not a single opaque score:

- **control_satisfied_resolution:** Fraction of legitimate vendors correctly approved.
- **institutional_utility:** Overall AP throughput and policy effectiveness.
- **unsafe_release_rate:** Fraction of fraudulent cases incorrectly approved (never hidden).
- **certificate_validity:** Assurance that decision reasoning is sound.
- **result_class:** Explicit categorization (valid success, policy incomplete, unsafe release).

## Why This Matters for Agent Training and Evaluation

LedgerShield v2 enables rigorous safety-oriented agent development. Researchers can:

- Train agents on 21 curated cases with documented control objectives, using TRL-compatible SFT or RL pipelines.
- Evaluate generalization across mechanism families without overfitting to evaluator state.
- Benchmark not just accuracy, but institutional safety and operational robustness.
- Report transparent metrics that expose—rather than hide—safety-critical failure modes.

The benchmark is reproducible, audited, and ready for fresh-machine evaluation. Whether you're building LLM-based agents, symbolic AP systems, or hybrid approaches, LedgerShield v2 provides the structure and transparency needed to iterate safely.

Get started: [https://github.com/BiradarScripts/Meta-s-LedgerShield](https://github.com/BiradarScripts/Meta-s-LedgerShield)

---

**Word count:** 445 words  
**Tone:** Technical, safety-focused, benchmarking-oriented  
**Audience:** AI safety researchers, agent developers, enterprise tech builders
