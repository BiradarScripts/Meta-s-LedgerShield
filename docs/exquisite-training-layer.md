# LedgerShield Exquisite Training Layer

This is the short entry point for the additive self-play -> falsifier reward -> GRPO/DPO training stack.

The full report lives in [`DOCUMENTATION.md#exquisite-training-layer`](./DOCUMENTATION.md#exquisite-training-layer), with plot-by-plot interpretation in [`DOCUMENTATION.md#exquisite-visual-analysis`](./DOCUMENTATION.md#exquisite-visual-analysis).

## Main Evidence

| Item | Artifact |
|---|---|
| Final policy matrix | [`../artifacts/exquisite-training/reports/final_policy_matrix.csv`](../artifacts/exquisite-training/reports/final_policy_matrix.csv) |
| Master report | [`../artifacts/exquisite-training/reports/exquisite_training_report.md`](../artifacts/exquisite-training/reports/exquisite_training_report.md) |
| Self-play candidates | [`../artifacts/exquisite-training/selfplay-0.5b/selfplay_candidates.jsonl`](../artifacts/exquisite-training/selfplay-0.5b/selfplay_candidates.jsonl) |
| GRPO reward history | [`../artifacts/exquisite-training/grpo-0.5b/grpo_reward_history.csv`](../artifacts/exquisite-training/grpo-0.5b/grpo_reward_history.csv) |
| GRPO final eval | [`../artifacts/exquisite-training/grpo-0.5b/final_policy_eval.json`](../artifacts/exquisite-training/grpo-0.5b/final_policy_eval.json) |
| DPO pairs | [`../artifacts/exquisite-training/dpo-falsifier-distill/dpo_pairs.jsonl`](../artifacts/exquisite-training/dpo-falsifier-distill/dpo_pairs.jsonl) |
| DPO metrics | [`../artifacts/exquisite-training/dpo-falsifier-distill/dpo_step_metrics.csv`](../artifacts/exquisite-training/dpo-falsifier-distill/dpo_step_metrics.csv) |
| Plot pack | [`../artifacts/exquisite-training/plots/`](../artifacts/exquisite-training/plots/) |
| Dashboard | [`../artifacts/exquisite-training/dashboard/index.html`](../artifacts/exquisite-training/dashboard/index.html) |
| Training scripts | [`../training/exquisite/`](../training/exquisite/) |

## Main Result

GRPO is the flagship result: `SFT Qwen 0.5B` improves from `0.4394` to `GRPO Qwen 0.5B` at `0.6606`, nearly matching the `0.6627` teacher reference while preserving `0.0000` unsafe release.

DPO/preference distillation is implemented and artifact-complete, but in this artifact pack it scores `0.4503`, below the GRPO policy. That makes it supporting evidence for the training stack, not the headline result.
