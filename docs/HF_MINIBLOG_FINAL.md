# LedgerShield ControlBench: Training Agents To Survive Enterprise Payment Controls

LedgerShield ControlBench asks whether an AI agent can operate a defensible enterprise accounts-payable control regime, not just classify a suspicious invoice. In each episode the agent sees partial evidence, calls investigation tools, manages budget pressure, applies policy controls, and submits an auditable payment decision that is checked against hidden backend state.

The domain is deliberately operational. Real payment fraud is not a clean label-prediction problem. A safe AP analyst must notice vendor takeover signals, reconcile invoices against purchase orders and receipts, verify bank-account changes, resist executive-pressure emails, and explain the decision in a way that survives audit. LedgerShield turns that workflow into an OpenEnv-compatible benchmark with `reset`, `step`, `state`, FastAPI deployment, Docker packaging, and a Hugging Face Space.

The environment is novel because it combines blind partial observability, generated holdouts, institutional memory, calibration-gated authority, proof-carrying decision certificates, deterministic falsification, TrustGraph audit projection, and a multi-dimensional institutional loss surface. The reward does not just say correct or incorrect. It rewards evidence gathering, useful interventions, policy completion, certificate quality, institutional utility, and zero unsafe payment release.

We also ran real training. The final run used Hugging Face Jobs `a10g-large` hardware with `Qwen/Qwen2.5-0.5B-Instruct`, collected 45 live trajectories through LedgerShield `reset()` and `step()` calls, trained on 36 cases, evaluated on 9 held-out cases, and ran 900 TRL SFT optimizer steps with LoRA.

The trained Qwen LoRA improved held-out mean score from `0.1283` for base Qwen and `0.1088` for a random baseline to `0.4394`, while maintaining `1.0000` parse success and `0.0000` unsafe release. Reward checkpoint evaluation peaked at `0.5090` on the held-out checkpoint subset. The teacher policy remains higher at `0.6627`, which is the honest gap for future RL or rejection-sampling work.

All training evidence is linked from the root README and the full report: [`training-report.md`](./training-report.md). The committed artifacts include loss curves, reward curves, baseline-vs-trained plots, per-case scores, safety metrics, result-class distributions, the LoRA adapter, the full HF job log, and the CSV/JSON metrics needed to audit the run.

LedgerShield matters because enterprise AI agents will not be judged only by task accuracy. They will be judged by whether they preserve money, trust, auditability, and institutional control under adversarial pressure. This benchmark gives researchers a runnable environment where those capabilities can be trained and measured.
