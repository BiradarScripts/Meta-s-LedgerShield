# LedgerShield Judge Quickstart

Use this path when you have 10 minutes and want to verify the project without reading the whole repository.

## 1. Read the headline result

- Root entry point: [`../README.md`](../README.md)
- Final policy matrix: [`../artifacts/exquisite-training/reports/final_policy_matrix.csv`](../artifacts/exquisite-training/reports/final_policy_matrix.csv)
- Exquisite report: [`../artifacts/exquisite-training/reports/exquisite_training_report.md`](../artifacts/exquisite-training/reports/exquisite_training_report.md)

The main comparable ladder is:

| Policy | Mean score | Unsafe release |
|---|---:|---:|
| Base Qwen 0.5B | 0.1283 | 0.0000 |
| SFT Qwen 0.5B | 0.4394 | 0.0000 |
| GRPO Qwen 0.5B | 0.6606 | 0.0000 |
| Teacher reference | 0.6627 | 0.0000 |

## 2. Inspect the plots

- Policy ladder: [`../artifacts/exquisite-training/plots/01_final_policy_ladder.png`](../artifacts/exquisite-training/plots/01_final_policy_ladder.png)
- GRPO reward curve: [`../artifacts/exquisite-training/plots/08_grpo_reward_curve_smoothed.png`](../artifacts/exquisite-training/plots/08_grpo_reward_curve_smoothed.png)
- Unsafe release by policy: [`../artifacts/exquisite-training/plots/37_unsafe_release_rate_by_policy.png`](../artifacts/exquisite-training/plots/37_unsafe_release_rate_by_policy.png)
- Certificate score by policy: [`../artifacts/exquisite-training/plots/38_certificate_score_by_policy.png`](../artifacts/exquisite-training/plots/38_certificate_score_by_policy.png)
- Control-satisfied resolution by policy: [`../artifacts/exquisite-training/plots/39_control_satisfied_resolution_by_policy.png`](../artifacts/exquisite-training/plots/39_control_satisfied_resolution_by_policy.png)

## 3. Verify the environment

```bash
pip install -e .
pip install -r requirements.txt
python -m pytest tests/ -q
python benchmark_report.py --format markdown --skip-write --skip-leaderboard
```

## 4. Run the OpenEnv server

```bash
python -m server.app
```

Then open the live docs at `http://localhost:8000/docs`.

## 5. Regenerate the final reports

```bash
python training/exquisite/evaluate_exquisite_policy.py \
  --artifact-root artifacts/exquisite-training \
  --output-dir artifacts/exquisite-training/reports

python training/exquisite/plot_exquisite_training_results.py \
  --artifact-root artifacts/exquisite-training
```

## 6. Read deeper only if needed

- Full technical documentation: [`DOCUMENTATION.md`](./DOCUMENTATION.md)
- Training evidence report: [`DOCUMENTATION.md#training-evidence-report`](./DOCUMENTATION.md#training-evidence-report)
- Exquisite training layer: [`DOCUMENTATION.md#exquisite-training-layer`](./DOCUMENTATION.md#exquisite-training-layer)
- Exquisite visual analysis: [`DOCUMENTATION.md#exquisite-visual-analysis`](./DOCUMENTATION.md#exquisite-visual-analysis)
