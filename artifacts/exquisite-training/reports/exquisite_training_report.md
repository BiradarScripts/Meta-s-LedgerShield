# LedgerShield Exquisite Training Report

Generated at `2026-04-26T05:25:05.950355+00:00`.

## Summary

LedgerShield now has two stacked training layers:

- Existing SFT proof: live OpenEnv rollouts, Qwen 0.5B LoRA, A10G TRL run, held-out score improvement from `0.1283` to `0.4394`, and zero unsafe release.
- Exquisite layer: self-play candidate generation, LedgerShield environment execution, deterministic falsifier reward, GRPO online RL, optional DPO preference distillation, scaling-law analysis, and a 56-plot visualization pack.

The current best numeric policy is `Teacher` with mean score `0.6627`.

## Status

- Policy rows completed: `8` of `8`
- New-policy rows pending artifact sync: `0`
- Self-play candidates recorded: `72`
- Plots generated: `56`
- Live runs still active: `0`
- Artifact-complete runs: `4`
- Planned GPU hours: `12.0`
- Planned max cost (based on timeout caps): `$25.00`
- Live report exclusions: `grpo-1.5b, grpo-3b-flagship`

## Source Sync

- Synced at: `2026-04-26T01:56:54.743965+00:00`
- Source branch: `main`
- Synced folders: `server, training, docs`
- Synced files: `__init__.py, README.md, Dockerfile, benchmark_report.py, client.py, inference.py, ledgershield_env.py, llm_utils.py, models.py, openenv.yaml, openenv_compat.py, pyproject.toml, requirements.txt, task_c_guardrails.py, task_d_guardrails.py, uv.lock, validate-submission.sh`

## Policy Matrix

| policy | model | method | mean_score | certificate_score | control_satisfied | unsafe_release | parse_success | status |
|---|---|---|---|---|---|---|---|---|
| Random | - | baseline | 0.1088 | 0.4461 | 0.0000 | 0.0000 | 1.0000 | completed |
| Naive PAY | - | baseline | 0.0693 | 0.4794 | 0.2222 | 0.0000 | 1.0000 | completed |
| Base Qwen | 0.5B | base | 0.1283 | 0.4044 | 0.0000 | 0.0000 | 1.0000 | completed |
| SFT Qwen | 0.5B | SFT | 0.4394 | 0.8478 | 0.2222 | 0.0000 | 1.0000 | completed |
| GRPO Qwen | 0.5B | SFT->GRPO | 0.6606 | 0.9653 | 0.6667 | 0.0000 | 1.0000 | completed |
| SFT Qwen | 1.5B | SFT | 0.4798 | 0.7992 | 0.0000 | 0.0000 | 1.0000 | completed |
| DPO-Falsifier | 1.5B/3B | GRPO->DPO | 0.4503 | 0.8408 | 0.2222 | 0.0000 | 1.0000 | completed |
| Teacher | - | oracle-ish | 0.6627 | 0.9472 | 0.5556 | 0.0000 | 1.0000 | completed |

## Execution Footprint

| name | hardware | public_status | public_note | timeout | hourly_cost_usd | max_cost_usd |
|---|---|---|---|---|---|---|
| selfplay-0.5b | a10g-large | COMPLETE | artifact-complete | 2h | 1.5 | 3.0 |
| grpo-0.5b | a100-large | COMPLETE | artifact-complete | 4h | 2.5 | 10.0 |
| dpo-falsifier-distill | a10g-large | COMPLETE | artifact-complete | 3h | 1.5 | 4.5 |
| sft-1.5b | a100-large | COMPLETE | artifact-complete | 3h | 2.5 | 7.5 |

## Key Artifacts

- `Exquisite docs`: `docs/exquisite-training-layer.md`
- `Visual analysis docs`: `docs/exquisite-visual-analysis.md`
- `Training package`: `training/exquisite/`
- `Policy matrix`: `artifacts/exquisite-training/reports/final_policy_matrix.csv`
- `Visualization manifest`: `artifacts/exquisite-training/reports/visualization_manifest.json`
- `Dashboard`: `artifacts/exquisite-training/dashboard/index.html`

## Reproduction

```bash
python training/exquisite/collect_selfplay_rollouts.py --mode smoke --case-limit 6 --eval-case-limit 2 --num-generations 4
python training/exquisite/evaluate_exquisite_policy.py
python training/exquisite/plot_exquisite_training_results.py
python training/exquisite/build_exquisite_dashboard.py
python training/exquisite/render_exquisite_report.py
```

HF launch with source sync and token fallback:

```bash
export HF_TOKEN_PRIMARY="..."
export HF_TOKEN_SECONDARY="..."
python training/exquisite/launch_exquisite_jobs.py --monitor
```
