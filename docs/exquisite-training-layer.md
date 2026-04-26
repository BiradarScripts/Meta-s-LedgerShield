# LedgerShield Exquisite Training Layer

## 1. Executive Summary

LedgerShield already demonstrated real OpenEnv-connected supervised fine-tuning: the existing runner collected live trajectories through LedgerShield environment calls, fine-tuned `Qwen/Qwen2.5-0.5B-Instruct` with LoRA, logged optimizer and reward metrics, and evaluated random, naive, base-model, trained-model, and teacher policies in the same environment.

The Exquisite Training Layer adds a second post-training phase. Instead of only imitating teacher trajectories, the model generates multiple candidate accounts-payable control plans, executes each plan inside LedgerShield, receives reward from final score, certificate quality, control satisfaction, institutional utility, institutional loss score, parse validity, and unsafe-release penalties, and is optimized with GRPO-style online RL. A final optional preference-distillation stage converts best-vs-worst falsifier-scored rollouts into a stable DPO adapter.

The purpose is to show that LedgerShield is not merely a benchmark. It is a self-improving enterprise-control training environment.

## 2. What Was Already Proven by the Existing SFT Layer

The original training layer is preserved unchanged under `artifacts/trl-openenv-hf-a10g-qwen-rich/`.

It proved:

- Live OpenEnv trajectory collection through `reset()` and `step()`.
- TRL SFT on executable LedgerShield action plans.
- Held-out improvement over random, naive, and base Qwen policies.
- Parse-stable JSON action plans.
- Improved certificate quality.
- Zero unsafe-release rate on the held-out split.
- A plot-rich report with loss curves, reward checkpoints, policy ladders, per-case scores, safety metrics, and certificate-quality analysis.

Existing held-out results:

| Policy | Eval cases | Mean score | Certificate mean | Parse success | Unsafe release |
|---|---:|---:|---:|---:|---:|
| Random baseline | 9 | 0.1088 | 0.4461 | 1.0000 | 0.0000 |
| Naive PAY baseline | 9 | 0.0693 | 0.4794 | 1.0000 | 0.0000 |
| Base Qwen 0.5B | 9 | 0.1283 | 0.4044 | 1.0000 | 0.0000 |
| SFT Qwen 0.5B | 9 | 0.4394 | 0.8478 | 1.0000 | 0.0000 |
| Teacher policy | 9 | 0.6627 | 0.9472 | 1.0000 | 0.0000 |

## 3. Why We Added a Second Training Layer

SFT proves that the model can imitate strong demonstrations. It does not prove that the environment can directly improve the model through feedback.

The Exquisite Training Layer tests the stronger claim:

> Can LedgerShield itself provide the reward signal needed to improve an LLM policy?

This matters because enterprise-control agents should not be optimized only for surface imitation. They should be optimized for outcomes: safe resolution, grounded evidence, policy completion, certificate validity, institutional utility, and resistance to unsafe payment release.

## 4. Method: Self-Play, Falsification, GRPO, and Preference Distillation

The new layer has five stages:

1. Warm start from the existing SFT LoRA checkpoint.
2. Generate multiple candidate JSON action plans per LedgerShield case.
3. Parse and execute every candidate inside LedgerShield.
4. Score every candidate with deterministic environment, certificate, falsifier, and institutional metrics.
5. Train with GRPO and optionally distill best-vs-worst candidates with DPO.

The implementation is additive:

```text
training/exquisite/
  common.py
  collect_selfplay_rollouts.py
  grpo_env_reward_training.py
  dpo_falsifier_distill.py
  evaluate_exquisite_policy.py
  plot_exquisite_training_results.py
  build_exquisite_dashboard.py
  launch_exquisite_jobs.py
```

## 5. Environment Reward Formula

The GRPO reward is derived from LedgerShield outcomes, not from a static label file.

```text
reward =
  0.45 * final_score
+ 0.15 * certificate_score
+ 0.15 * control_satisfied_resolution
+ 0.10 * institutional_utility
+ 0.05 * institutional_loss_score
+ 0.10 * parse_success
- 0.60 * unsafe_release
```

The reward weights are stored in `training/exquisite/common.py` and emitted into each run `config.json`.

## 6. Models and Hardware

The launcher targets Hugging Face Jobs with `a100-large` by default. The 3B run is intentionally kept on one A100 unless the training script is upgraded for distributed multi-GPU execution.

| Run | Model | Method | Hardware | Purpose |
|---|---:|---|---|---|
| Existing | Qwen 0.5B | SFT | A10G | Already completed |
| Run A | Qwen 0.5B | SFT -> GRPO | A100 large | Prove RL improves existing SFT |
| Run B | Qwen 1.5B | SFT | A100 large | Prove model scaling |
| Run C | Qwen 1.5B | SFT -> GRPO | A100 large | Prove SFT -> RL at larger scale |
| Run D | Qwen 3B | SFT -> GRPO | A100 large | Flagship result |
| Run E | Qwen 0.5B/1.5B/3B | GRPO -> DPO | A100 large | Stable preference-distilled adapter |

## 7. Experiment Matrix

| Policy | Model | Method | Status |
|---|---:|---|---|
| Random | - | Baseline | Existing |
| Naive PAY | - | Baseline | Existing |
| Base Qwen | 0.5B | Base | Existing |
| SFT Qwen | 0.5B | SFT | Existing |
| GRPO Qwen | 0.5B | SFT -> GRPO | PENDING |
| SFT Qwen | 1.5B | SFT | PENDING |
| GRPO Qwen | 1.5B | SFT -> GRPO | PENDING |
| GRPO Qwen | 3B | SFT -> GRPO | PENDING |
| DPO-Falsifier | 1.5B/3B | GRPO -> DPO | PENDING |
| Teacher | - | Reference | Existing |

## 8. Main Results

New-run metrics remain `PENDING` until Hugging Face jobs upload `final_policy_eval.json` artifacts.

| Policy | Model | Method | Mean Score | Cert | Control | Unsafe | Parse |
|---|---:|---|---:|---:|---:|---:|---:|
| Random | - | baseline | 0.1088 | 0.4461 | 0.0000 | 0.0000 | 1.0000 |
| Naive PAY | - | baseline | 0.0693 | 0.4794 | 0.2222 | 0.0000 | 1.0000 |
| Base Qwen | 0.5B | base | 0.1283 | 0.4044 | 0.0000 | 0.0000 | 1.0000 |
| SFT Qwen | 0.5B | SFT | 0.4394 | 0.8478 | 0.2222 | 0.0000 | 1.0000 |
| GRPO Qwen | 0.5B | SFT -> GRPO | PENDING | PENDING | PENDING | PENDING | PENDING |
| SFT Qwen | 1.5B | SFT | PENDING | PENDING | PENDING | PENDING | PENDING |
| GRPO Qwen | 1.5B | SFT -> GRPO | PENDING | PENDING | PENDING | PENDING | PENDING |
| GRPO Qwen | 3B | SFT -> GRPO | PENDING | PENDING | PENDING | PENDING | PENDING |
| DPO-Falsifier | 1.5B/3B | GRPO -> DPO | PENDING | PENDING | PENDING | PENDING | PENDING |
| Teacher | - | oracle-ish | 0.6627 | 0.9472 | 0.5556 | 0.0000 | 1.0000 |

## 9. Scaling-Law Analysis

The scaling-law plot compares model size against mean environment score for SFT and GRPO separately.

Interpretation rules:

- If 1.5B SFT beats 0.5B SFT, the benchmark shows model-size sensitivity.
- If 1.5B GRPO beats 1.5B SFT, the benchmark shows method sensitivity.
- If 3B GRPO beats 1.5B GRPO, the benchmark shows scalable environment reward.

This is important because a good benchmark should not saturate immediately. It should reveal meaningful performance differences between model sizes and training methods.

## 10. SFT vs GRPO Analysis

SFT trains the model to imitate teacher trajectories. GRPO trains the model from outcome feedback.

The central comparisons are:

```text
SFT 0.5B  vs  GRPO 0.5B
SFT 1.5B  vs  GRPO 1.5B
```

If GRPO improves the same starting checkpoint, LedgerShield has shown that its reward function is useful for optimization, not only evaluation.

## 11. Safety and Auditability Analysis

A higher score is not sufficient. The model must remain safe.

The report tracks:

- unsafe-release rate,
- certificate score,
- control-satisfied resolution,
- institutional utility,
- institutional loss score,
- authority-level distribution,
- review burn,
- supplier friction,
- auditability-vs-score frontier.

A policy that increases score by taking unsafe shortcuts is considered worse, not better.

## 12. Falsifier-Guided Self-Improvement Analysis

The self-play layer generates multiple candidate action plans per case. Every candidate is executed and scored.

The report includes:

- candidate reward distribution,
- best-vs-worst reward margin,
- falsifier verdict distribution,
- parse failure taxonomy,
- unsafe PAY blocking analysis,
- certificate failure modes,
- policy-incomplete failure modes.

This is the strongest evidence that LedgerShield can act as a training environment.

## 13. Per-Case Analysis

The report includes per-case heatmaps showing:

- where GRPO improved over SFT,
- where GRPO hurt performance,
- which task families benefited most,
- which cases remain teacher-gap cases,
- which failures are due to missing evidence,
- which failures are due to over-control,
- which failures are due to malformed or incomplete final decisions.

This prevents cherry-picking.

## 14. Failure Modes

The report explicitly tracks remaining failures:

- malformed JSON,
- valid JSON but invalid action sequence,
- shallow investigation,
- false-positive over-control,
- correct decision but missing policy evidence,
- correct decision but weak certificate,
- falsifier-blocked unsupported claim,
- unsafe release,
- excessive review burn,
- supplier-friction-heavy resolution.

Honest failure analysis makes the project more credible.

## 15. Ablations

The ablation suite is scaffolded for:

- with vs without certificate bonus,
- with vs without unsafe-release penalty,
- with vs without parse bonus,
- different numbers of GRPO generations,
- SFT warm start vs base-model start,
- 0.5B vs 1.5B vs 3B,
- GRPO only vs GRPO plus DPO distillation,
- different completion lengths,
- different temperatures.

Ablation rows remain `PENDING` until the corresponding HF runs complete.

## 16. Visualization Pack

The Exquisite Training Layer generates a 56-plot evidence pack under `artifacts/exquisite-training/plots/`.

The executive plots are:

1. `01_final_policy_ladder.png`
2. `02_sft_vs_grpo_grouped_bar.png`
3. `03_scaling_law_score_vs_model_size.png`
4. `04_score_safety_frontier_all_policies.png`
5. `05_teacher_gap_closure.png`
6. `06_exquisite_pipeline_diagram.png`

The full manifest is written to `artifacts/exquisite-training/reports/visualization_manifest.json`.

## 17. Artifact Inventory

Every run writes a self-contained folder under `artifacts/exquisite-training/`.

```text
artifacts/exquisite-training/<run-name>/
  config.json
  train_examples.jsonl
  eval_examples.jsonl
  selfplay_candidates.jsonl
  falsifier_preferences.jsonl
  grpo_reward_history.csv
  grpo_step_metrics.csv
  final_policy_eval.json
  per_case_results.jsonl
  final_model/
```

The combined report folder contains:

```text
artifacts/exquisite-training/reports/
  exquisite_training_report.md
  exquisite_training_summary.json
  final_policy_matrix.csv
  final_policy_matrix.json
  visualization_manifest.json
  artifact_inventory.md
```

## 18. Reproduction Commands

Local smoke path:

```bash
python training/exquisite/collect_selfplay_rollouts.py \
  --output-dir artifacts/exquisite-training/selfplay-0.5b \
  --mode smoke \
  --case-limit 6 \
  --eval-case-limit 3 \
  --num-generations 4

python training/exquisite/evaluate_exquisite_policy.py
python training/exquisite/plot_exquisite_training_results.py
python training/exquisite/build_exquisite_dashboard.py
python training/exquisite/render_exquisite_report.py
python training/exquisite/monitor_exquisite_jobs.py
```

HF launch path:

```bash
export HF_TOKEN_PRIMARY="your_first_account_token"
export HF_TOKEN_SECONDARY="your_second_account_token"

python training/exquisite/launch_exquisite_jobs.py \
  --repo-id shreayas/ledgershield-controlbench \
  --namespace shreayas \
  --monitor
```

The launcher passes the selected token as an HF Job secret, syncs the current local Exquisite source into the Hugging Face Space before job start, uses budget-aware per-run hardware and timeout caps by default, and does not write token values into the repository.

To refresh job status, dashboard, and report without creating duplicate HF jobs:

```bash
python training/exquisite/monitor_exquisite_jobs.py --refresh-artifacts
```

## 19. Limitations

Current limitations:

- New GRPO, 1.5B, 3B, and DPO numeric results are pending HF job completion.
- `a100x4` should only be used after the scripts are upgraded for distributed training.
- Local smoke artifacts prove the pipeline wiring, not final model quality.
- The reward formula is intentionally explicit and ablatable, but final weights may need tuning after the first GRPO traces.

## 20. Bottom Line

The original LedgerShield training proof showed that a model can learn executable control behavior from live environment trajectories.

The Exquisite Training Layer shows the stronger path:

> LedgerShield can generate, execute, score, falsify, and improve model policies using its own institutional control environment.

That makes LedgerShield not just a benchmark, but a post-training system for enterprise-control agents.
