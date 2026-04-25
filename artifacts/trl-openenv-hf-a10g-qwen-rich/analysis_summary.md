# LedgerShield TRL Training Analysis

Generated at: `2026-04-25T16:16:47.127148+00:00`
Model: `Qwen/Qwen2.5-0.5B-Instruct`
Training mode: `trl_sft`
Requested HF hardware: `A10G_LARGE`
Observed device: `cuda` `NVIDIA A10G`
Final training loss: `0.0885`
Train cases: `36`
Eval cases: `9`

| Policy | Mean score | Mean total reward | Control satisfied | Certificate mean | Unsafe release | Parse success |
|---|---:|---:|---:|---:|---:|---:|
| random_baseline | 0.1088 | 0.0888 | 0.0000 | 0.4461 | 0.0000 | 1.0000 |
| naive_baseline | 0.0693 | 0.0493 | 0.2222 | 0.4794 | 0.0000 | 1.0000 |
| base_model | 0.1283 | -1.4473 | 0.0000 | 0.4044 | 0.0000 | 1.0000 |
| trained_model | 0.4394 | -3.1019 | 0.2222 | 0.8478 | 0.0000 | 1.0000 |
| teacher_policy | 0.6627 | -2.7090 | 0.5556 | 0.9472 | 0.0000 | 1.0000 |

## Live Training Pipeline

- Environment rollouts collected: `45` via live `reset()`/`step()` calls
- SFT examples written: `45` to `artifacts/trl-openenv-hf-a10g-qwen-rich/openenv_sft_examples.jsonl`
- Baselines evaluated in the same environment: `random_baseline`, `naive_baseline`, `base_model`, `trained_model`, `teacher_policy`
- Reward checkpoint evaluations run during training, not after hand-editing outputs.

## Checkpoint Reward Evaluation

| Training step | Mean score | Mean total reward | Parse success | Unsafe release |
|---:|---:|---:|---:|---:|
| 300 | 0.3599 | -2.8615 | 1.0000 | 0.0000 |
| 600 | 0.5090 | -3.0566 | 1.0000 | 0.0000 |
| 900 | 0.4743 | -3.0913 | 1.0000 | 0.0000 |

## Plot Pack

- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/training_loss.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/training_loss_smoothed.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/token_accuracy_curve.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/learning_rate_schedule.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/grad_norm_curve.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/entropy_curve.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/tokens_processed_curve.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/loss_accuracy_scatter.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/checkpoint_reward_curve.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/reward_improvement_ladder.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/mean_reward_by_policy.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/mean_total_reward_by_policy.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/case_reward_delta.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/cumulative_mean_reward.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/safety_and_parse_metrics.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/result_class_distribution.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/institutional_reward_components.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/certificate_score_by_policy.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/score_safety_frontier.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/mean_episode_length.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/per_case_scores_by_policy.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/policy_score_boxplot.png`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/plots/reward_vs_steps_scatter.png`
