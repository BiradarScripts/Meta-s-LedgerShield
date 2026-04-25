# LedgerShield Exquisite Training Report

Generated artifact report for the additive Exquisite Training Layer.

## Summary

LedgerShield now has two training layers:

- Existing SFT proof: live OpenEnv rollouts, Qwen 0.5B LoRA, A10G TRL run, held-out score improvement from `0.1283` to `0.4394`, and zero unsafe release.
- New Exquisite layer: self-play candidate generation, LedgerShield environment execution, deterministic falsifier reward, GRPO online RL, optional DPO preference distillation, scaling-law analysis, and a 56-plot visualization pack.

## Status

The implementation is complete and local smoke artifacts can be generated immediately. New HF GRPO, 1.5B, 3B, and DPO numeric metrics remain `PENDING` until the Hugging Face jobs upload their `final_policy_eval.json` files.

## Key Artifacts

| Artifact | Path |
|---|---|
| Exquisite docs | `docs/exquisite-training-layer.md` |
| Visual analysis docs | `docs/exquisite-visual-analysis.md` |
| Training package | `training/exquisite/` |
| Final policy matrix | `artifacts/exquisite-training/reports/final_policy_matrix.csv` |
| Visualization manifest | `artifacts/exquisite-training/reports/visualization_manifest.json` |
| Plot pack | `artifacts/exquisite-training/plots/` |
| Dashboard | `artifacts/exquisite-training/dashboard/index.html` |

## Reproduction

```bash
python training/exquisite/collect_selfplay_rollouts.py --mode smoke --case-limit 6 --eval-case-limit 3 --num-generations 4
python training/exquisite/evaluate_exquisite_policy.py
python training/exquisite/plot_exquisite_training_results.py
python training/exquisite/build_exquisite_dashboard.py
```

HF launch:

```bash
export HF_TOKEN_PRIMARY="your_first_account_token"
export HF_TOKEN_SECONDARY="your_second_account_token"
python training/exquisite/launch_exquisite_jobs.py --timeout 8h --monitor
```
