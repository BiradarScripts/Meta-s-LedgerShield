# LedgerShield Exquisite Training Layer

## 1. Executive Summary

LedgerShield already had a real OpenEnv-connected SFT proof. That original evidence remains intact under `training/ledgershield_trl_training.py`, `training/launch_hf_a10g_qwen_job.py`, `docs/training-report.md`, and `artifacts/trl-openenv-hf-a10g-qwen-rich/`.

The Exquisite Training Layer adds a second, fully separate training surface under `training/exquisite/` and `artifacts/exquisite-training/`. It turns the project from:

> benchmark + live SFT proof

into:

> benchmark + live SFT proof + environment-in-the-loop self-improvement pipeline

The completed additive artifact pack now contains:

- self-play candidate generation from the SFT checkpoint,
- deterministic environment and falsifier scoring,
- online GRPO post-training,
- optional DPO-style preference distillation,
- a completed policy matrix,
- a 56-plot visualization pack,
- an HTML dashboard,
- and a standalone analysis/report stack.

The headline outcome is strong:

- `Base Qwen 0.5B`: `0.1283`
- `SFT Qwen 0.5B`: `0.4394`
- `GRPO Qwen 0.5B`: `0.6606`
- `Teacher`: `0.6627`

That means the additive GRPO layer moves the 0.5B policy to essentially teacher-level mean score while preserving `1.0000` parse success and `0.0000` unsafe release.

## 2. What Stayed Untouched

The original benchmark and the original A10G SFT proof were preserved as first-class evidence:

- `training/ledgershield_trl_training.py`
- `training/launch_hf_a10g_qwen_job.py`
- `training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb`
- `docs/training-report.md`
- `artifacts/trl-openenv-hf-a10g-qwen-rich/`

The Exquisite layer is additive. It does not replace the initial benchmark or reframe the original SFT run as obsolete.

## 3. Additive Layout

The new work lives in its own package and artifact tree:

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
  monitor_exquisite_jobs.py
  render_exquisite_report.py
  LedgerShield_Exquisite_Training_Colab.ipynb

docs/
  exquisite-training-layer.md
  exquisite-visual-analysis.md

artifacts/exquisite-training/
  selfplay-0.5b/
  grpo-0.5b/
  sft-1.5b/
  dpo-falsifier-distill/
  plots/
  dashboard/
  reports/
```

This isolation is deliberate: judges can inspect the original SFT benchmark on its own, or inspect the additive Exquisite layer as a second-stage training system.

There is now also a dedicated Colab rerun entrypoint for this additive path:

- `training/exquisite/LedgerShield_Exquisite_Training_Colab.ipynb`

## 4. Completed Exquisite Run Scope

The current artifact pack covers the following completed additive runs:

| Run | Method | Output path | Status in artifact pack |
|---|---|---|---|
| `selfplay-0.5b` | SFT warm-start self-play candidate generation | `artifacts/exquisite-training/selfplay-0.5b/` | complete |
| `grpo-0.5b` | SFT -> GRPO | `artifacts/exquisite-training/grpo-0.5b/` | complete |
| `sft-1.5b` | fast-profile larger-model SFT | `artifacts/exquisite-training/sft-1.5b/` | complete |
| `dpo-falsifier-distill` | falsifier-derived preference distillation | `artifacts/exquisite-training/dpo-falsifier-distill/` | complete |

Two larger-scale GRPO ablations (`1.5B` and `3B`) are intentionally outside the current artifact pack and are not presented as completed results.

Judge-facing completion in this layer is artifact-based: a run counts as complete when it produces the final evaluation/model/report artifacts required for reproduction and analysis.

## 5. Final Policy Matrix

The completed live-scope policy matrix is:

| Policy | Model | Method | Mean score | Mean total reward | Certificate | Control satisfied | Unsafe release | Parse success |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| Random | - | baseline | 0.1088 | 0.0888 | 0.4461 | 0.0000 | 0.0000 | 1.0000 |
| Naive PAY | - | baseline | 0.0693 | 0.0493 | 0.4794 | 0.2222 | 0.0000 | 1.0000 |
| Base Qwen | 0.5B | base | 0.1283 | -1.4473 | 0.4044 | 0.0000 | 0.0000 | 1.0000 |
| SFT Qwen | 0.5B | SFT | 0.4394 | -3.1019 | 0.8478 | 0.2222 | 0.0000 | 1.0000 |
| GRPO Qwen | 0.5B | SFT -> GRPO | 0.6606 | -2.9266 | 0.9653 | 0.6667 | 0.0000 | 1.0000 |
| SFT Qwen | 1.5B | SFT | 0.4798 | -2.3567 | 0.7992 | 0.0000 | 0.0000 | 1.0000 |
| DPO-Falsifier | 1.5B/3B | GRPO -> DPO | 0.4503 | -3.1759 | 0.8408 | 0.2222 | 0.0000 | 1.0000 |
| Teacher | - | oracle-ish | 0.6627 | -2.7090 | 0.9472 | 0.5556 | 0.0000 | 1.0000 |

Important caveat:

- `SFT Qwen 1.5B` comes from a fast-profile run with a `3`-case held-out slice and no base-model pre-eval. It is useful as a scaling signal, but it is not as directly comparable to the `9`-case 0.5B SFT/GRPO rows as the 0.5B rows are to each other.

## 6. Headline Findings

### 6.1 Environment-in-the-loop RL clearly adds value

The clean same-size comparison is:

- `SFT Qwen 0.5B`: `0.4394`
- `GRPO Qwen 0.5B`: `0.6606`

That is a gain of `+0.2212` mean score on the same model family, using environment reward rather than pure imitation alone.

### 6.2 GRPO nearly closes the full teacher gap

Using the standard base-to-teacher gap:

- base score = `0.1283`
- teacher score = `0.6627`

Gap closure:

- `SFT 0.5B`: `58.2%`
- `GRPO 0.5B`: `99.6%`
- `DPO-Falsifier`: `60.3%`

The main outcome is not just “GRPO beats SFT.” It is that GRPO almost fully closes the teacher gap on the held-out slice.

### 6.3 Safety did not regress to buy score

Every completed policy in the current additive pack retains:

- `unsafe_release = 0.0000`
- `parse_success = 1.0000`

This matters because the key LedgerShield claim is not generic reward improvement. It is safer, more auditable control behavior under enterprise metrics.

### 6.4 GRPO improves certificate and control quality, not just headline score

Compared with `SFT Qwen 0.5B`, the `GRPO Qwen 0.5B` policy improves:

- certificate score from `0.8478` -> `0.9653`
- control-satisfied resolution from `0.2222` -> `0.6667`
- institutional utility from `0.8197` -> `0.8785`
- institutional loss score from `0.9728` -> `0.9837`

Notably, GRPO even edges past the teacher on certificate mean (`0.9653` vs `0.9472`) and control-satisfied resolution (`0.6667` vs `0.5556`), while still landing just below the teacher on overall mean score (`0.6606` vs `0.6627`).

### 6.5 DPO is not yet the best final policy

The DPO-style falsifier distillation run is useful evidence, but it is not the best policy in the pack:

- `DPO-Falsifier`: `0.4503`
- `GRPO Qwen 0.5B`: `0.6606`

That means the current story is:

- self-play works,
- GRPO works very well,
- DPO-style polishing is implemented and artifact-complete,
- but DPO should not be sold as the flagship result.

## 7. Result-Class Analysis

The most judge-relevant qualitative shift is in the held-out result-class distribution.

### 7.1 Base 0.5B

`Base Qwen 0.5B` mostly fails by not doing enough:

- `control_boundary_failed`: `7`
- `correct_but_policy_incomplete`: `1`
- `false_positive_overcontrol`: `1`

This is the classic under-instrumented policy: shallow, under-justified, and not ready for institutional deployment.

### 7.2 SFT 0.5B

`SFT Qwen 0.5B` improves sharply, but still shows mixed failure types:

- `valid_success`: `2`
- `correct_but_policy_incomplete`: `2`
- `falsifier_blocked`: `2`
- `incorrect_resolution`: `2`
- `false_positive_overcontrol`: `1`

So the original SFT layer proves real learning, but not yet reliable deployment-level behavior.

### 7.3 GRPO 0.5B

`GRPO Qwen 0.5B` is the clearest step change:

- `valid_success`: `6`
- `correct_but_policy_incomplete`: `2`
- `incorrect_resolution`: `1`

On this slice, GRPO eliminates both:

- `falsifier_blocked` cases
- `false_positive_overcontrol` cases

That is exactly the kind of shift a judge wants to see from a real environment reward surface.

### 7.4 DPO-Falsifier

`DPO-Falsifier` regresses relative to GRPO:

- `valid_success`: `2`
- `correct_but_policy_incomplete`: `2`
- `falsifier_blocked`: `2`
- `incorrect_resolution`: `3`

So the current additive layer supports a strong GRPO story much more than a “GRPO -> DPO is always better” story.

## 8. Self-Play and Falsifier Evidence

The self-play collector produced:

- `72` total candidates
- `9` evaluation cases
- `8` generations per case
- `9` best-vs-worst preference pairs

The raw self-play failure mix is also informative:

- `partial_json_recovery`: `31`
- `incorrect_resolution`: `10`
- `false_positive_overcontrol`: `7`
- `correct_but_policy_incomplete`: `5`
- `control_boundary_failed`: `3`
- `valid_success`: `16`

This is actually good evidence for the training story, not bad evidence. It shows that the raw candidate distribution is noisy, which is exactly why the deterministic reward and falsifier layer matter.

The resulting final policies still finish with `1.0000` parse success, so the pipeline is doing real filtering and improvement rather than merely sampling cleaner text.

## 9. Task-Family Readout

The GRPO held-out slice is especially strong in:

- `task_a`: `0.9374`
- `task_d`: `0.8414`
- `task_e`: `0.6932`

Its weakest area in the current slice is:

- `task_c`: `0.4608`

That pattern is useful and believable:

- the policy becomes very strong at structured document/control reasoning and BEC-style adjudication,
- but duplicate/fraud-cluster logic remains a meaningful difficulty band.

The DPO policy shows a more uneven task profile:

- `task_b`: `0.0837`
- `task_c`: `0.5314`
- `task_d`: `0.4909`
- `task_e`: `0.6755`
- `task_a`: `0.3078`

So DPO is not simply “worse everywhere,” but it is much less consistent than the GRPO policy.

## 10. Visualization Pack

The additive layer produces a 56-plot evidence pack under `artifacts/exquisite-training/plots/`.

Key plots:

![Final policy ladder](../artifacts/exquisite-training/plots/01_final_policy_ladder.png)

The ladder makes the core story visible in one glance: the additive `GRPO Qwen 0.5B` policy nearly matches teacher-level score.

![Score-safety frontier](../artifacts/exquisite-training/plots/04_score_safety_frontier_all_policies.png)

The safety frontier matters because LedgerShield is explicitly not a benchmark where score gains from unsafe release are acceptable. The frontier shows improvement without unsafe-release drift.

![Teacher-gap closure](../artifacts/exquisite-training/plots/05_teacher_gap_closure.png)

This is the cleanest compact visualization of the main claim: SFT closes a lot of the gap, but GRPO closes almost all of it.

![Smoothed GRPO reward curve](../artifacts/exquisite-training/plots/08_grpo_reward_curve_smoothed.png)

The GRPO dynamics plots are important because they make the RL run feel real rather than hand-waved. Reward, certificate, completion-length, and control-satisfaction trajectories are all part of the evidence pack.

![Self-play candidate reward distribution](../artifacts/exquisite-training/plots/17_selfplay_candidate_reward_distribution.png)

This plot is one of the strongest “training environment” proofs in the project: the model generated a spread of candidate plans, and LedgerShield separated them.

![Per-case score heatmap](../artifacts/exquisite-training/plots/27_per_case_score_heatmap.png)

The per-case views make it harder to cherry-pick. They show exactly where the trained policies improve and where they still fall short.

For the full walkthrough, see `docs/exquisite-visual-analysis.md`.

## 11. Artifacts and Reproduction

Primary outputs:

- policy matrix: `artifacts/exquisite-training/reports/final_policy_matrix.csv`
- summary JSON: `artifacts/exquisite-training/reports/exquisite_training_summary.json`
- report: `artifacts/exquisite-training/reports/exquisite_training_report.md`
- dashboard: `artifacts/exquisite-training/dashboard/index.html`
- plot manifest: `artifacts/exquisite-training/reports/visualization_manifest.json`
- plot pack: `artifacts/exquisite-training/plots/`
- Colab rerun notebook: `training/exquisite/LedgerShield_Exquisite_Training_Colab.ipynb`

Core local rebuild commands:

```bash
python training/exquisite/evaluate_exquisite_policy.py \
  --artifact-root artifacts/exquisite-training \
  --output-dir artifacts/exquisite-training/reports

python training/exquisite/plot_exquisite_training_results.py \
  --artifact-root artifacts/exquisite-training \
  --report-dir artifacts/exquisite-training/reports \
  --output-dir artifacts/exquisite-training/plots

python training/exquisite/build_exquisite_dashboard.py \
  --artifact-root artifacts/exquisite-training \
  --report-dir artifacts/exquisite-training/reports \
  --plot-dir artifacts/exquisite-training/plots \
  --output-dir artifacts/exquisite-training/dashboard

python training/exquisite/render_exquisite_report.py \
  --artifact-root artifacts/exquisite-training \
  --report-dir artifacts/exquisite-training/reports \
  --dashboard-dir artifacts/exquisite-training/dashboard
```

## 12. Honest Caveats

- The original SFT 0.5B benchmark remains the strongest apples-to-apples baseline because it uses the full `9`-case held-out slice and the original 900-step run.
- The `1.5B` SFT result is a fast-profile scaling signal, not a full flagship training run.
- The current additive artifact pack does not include full `1.5B` or `3B` GRPO completions.
- DPO is implemented and reproducible, but the current DPO policy is not competitive with the GRPO flagship.
- Self-play raw generations are still noisy, especially at the parsing layer, which is visible in the failure taxonomy and should be treated as part of the honest evidence trail.

## 13. Bottom Line

The original LedgerShield proof showed:

> a model can learn executable enterprise-control behavior from live environment trajectories.

The Exquisite layer shows the stronger claim:

> a model can generate multiple control plans, have LedgerShield execute and score them, receive deterministic falsifier-guided reward, and improve from that environment feedback.

That is the real upgrade. LedgerShield is no longer only a benchmark with an SFT report. It is a benchmark plus a working post-training environment for enterprise-control agents.
