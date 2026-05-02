# LedgerShield Training Report

This is the short entry point for the original OpenEnv-connected SFT run.

The full report lives in [`DOCUMENTATION.md#training-evidence-report`](./DOCUMENTATION.md#training-evidence-report).

## Main Evidence

| Item | Artifact |
|---|---|
| SFT training metrics | [`../artifacts/trl-openenv-hf-a10g-qwen-rich/training_metrics.json`](../artifacts/trl-openenv-hf-a10g-qwen-rich/training_metrics.json) |
| Live OpenEnv trajectories | [`../artifacts/trl-openenv-hf-a10g-qwen-rich/openenv_trajectories.json`](../artifacts/trl-openenv-hf-a10g-qwen-rich/openenv_trajectories.json) |
| SFT examples | [`../artifacts/trl-openenv-hf-a10g-qwen-rich/openenv_sft_examples.jsonl`](../artifacts/trl-openenv-hf-a10g-qwen-rich/openenv_sft_examples.jsonl) |
| Loss history | [`../artifacts/trl-openenv-hf-a10g-qwen-rich/loss_history.csv`](../artifacts/trl-openenv-hf-a10g-qwen-rich/loss_history.csv) |
| Reward eval history | [`../artifacts/trl-openenv-hf-a10g-qwen-rich/reward_eval_history.csv`](../artifacts/trl-openenv-hf-a10g-qwen-rich/reward_eval_history.csv) |
| Plot pack | [`../artifacts/trl-openenv-hf-a10g-qwen-rich/plots/`](../artifacts/trl-openenv-hf-a10g-qwen-rich/plots/) |
| Training code | [`../training/ledgershield_trl_training.py`](../training/ledgershield_trl_training.py) |
| Colab notebook | [`../training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb`](../training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb) |

## Key Result

The original SFT run improves the 0.5B Qwen policy from `0.1283` to `0.4394` on the shared evaluation slice, with `0.0000` unsafe release.

For the final Base -> SFT -> GRPO -> Teacher comparison, use [`../artifacts/exquisite-training/reports/final_policy_matrix.csv`](../artifacts/exquisite-training/reports/final_policy_matrix.csv).
