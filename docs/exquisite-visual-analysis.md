# LedgerShield Exquisite Results And Visual Analysis

This document is the judge-facing deep dive for the additive Exquisite Training Layer. It explains what the completed plot pack and result artifacts actually show, which claims are strongly supported, and which claims should still be treated as future work.

## 1. What The Visual Pack Proves

The Exquisite evidence pack is not just decorative reporting. It is meant to answer five concrete questions:

1. Did the environment-in-the-loop training layer improve policy quality beyond the original SFT benchmark?
2. Did it preserve safety, parse stability, and auditability?
3. Did the model really generate multiple candidates that were separated by environment reward?
4. Does the policy improvement hold up at the per-case and per-task level?
5. What still breaks, and where should a reviewer remain skeptical?

The answer from the current completed artifact pack is:

- `yes` for the `0.5B SFT -> GRPO` comparison,
- `yes` for safety preservation,
- `yes` for self-play + falsifier evidence,
- `partly` for scaling, because the `1.5B` result is a fast-profile slice rather than a full flagship run,
- and `no` for any claim that DPO currently beats GRPO.

## 2. Headline Outcome

The core matrix is:

| Policy | Mean score | Certificate | Control satisfied | Unsafe release | Parse success |
|---|---:|---:|---:|---:|---:|
| Base Qwen 0.5B | 0.1283 | 0.4044 | 0.0000 | 0.0000 | 1.0000 |
| SFT Qwen 0.5B | 0.4394 | 0.8478 | 0.2222 | 0.0000 | 1.0000 |
| GRPO Qwen 0.5B | 0.6606 | 0.9653 | 0.6667 | 0.0000 | 1.0000 |
| DPO-Falsifier | 0.4503 | 0.8408 | 0.2222 | 0.0000 | 1.0000 |
| Teacher | 0.6627 | 0.9472 | 0.5556 | 0.0000 | 1.0000 |

The single most important result is that `GRPO Qwen 0.5B` lands at `0.6606`, essentially matching the teacher at `0.6627`.

## 3. Final Policy Ladder

![Final policy ladder](../artifacts/exquisite-training/plots/01_final_policy_ladder.png)

### Interpretation

This is the most compressed summary of the project:

- base model: low score, weak certificate, almost no control-satisfied wins
- original SFT: large step forward, but still clearly behind teacher
- GRPO: nearly matches teacher-level mean score
- DPO: lands back near the SFT regime rather than preserving the GRPO jump

This ladder is what turns the story from “we fine-tuned a model on benchmark trajectories” into “the environment reward itself changed the ranking of policies.”

## 4. Teacher-Gap Closure

![Teacher-gap closure](../artifacts/exquisite-training/plots/05_teacher_gap_closure.png)

Using `Base Qwen 0.5B` as the starting point and `Teacher` as the reference ceiling:

- `SFT Qwen 0.5B` closes `58.2%` of the gap
- `GRPO Qwen 0.5B` closes `99.6%` of the gap
- `DPO-Falsifier` closes `60.3%` of the gap

### Why this matters

This is stronger evidence than raw score alone, because it shows that the additive RL layer is not merely adding a few points. It is accounting for almost the entire remaining distance between the base model and the teacher reference on the held-out slice.

## 5. Score-Safety Frontier

![Score-safety frontier](../artifacts/exquisite-training/plots/04_score_safety_frontier_all_policies.png)

LedgerShield is not a benchmark where we accept score gains bought by risky releases. The right move on this frontier is:

- move to the right on mean score,
- do not move upward on unsafe release.

That is exactly what the completed additive pack shows:

- all completed policies remain at `0.0000` unsafe release
- parse success remains `1.0000`
- the GRPO policy is strictly to the right of the original 0.5B SFT policy

That means the score gain is not a fragile “unsafe shortcut” artifact.

## 6. SFT vs GRPO

![SFT vs GRPO grouped bar](../artifacts/exquisite-training/plots/02_sft_vs_grpo_grouped_bar.png)

The cleanest same-size comparison is:

- `SFT Qwen 0.5B`: `0.4394`
- `GRPO Qwen 0.5B`: `0.6606`

That is a `+0.2212` jump.

### What changed qualitatively

The result-class distribution is what makes this feel real.

`SFT Qwen 0.5B`:

- `valid_success`: `2`
- `correct_but_policy_incomplete`: `2`
- `falsifier_blocked`: `2`
- `incorrect_resolution`: `2`
- `false_positive_overcontrol`: `1`

`GRPO Qwen 0.5B`:

- `valid_success`: `6`
- `correct_but_policy_incomplete`: `2`
- `incorrect_resolution`: `1`

The GRPO policy removes the `falsifier_blocked` and `false_positive_overcontrol` buckets entirely on the held-out slice. That is the strongest qualitative sign that the environment reward is pushing the policy toward more institutionally acceptable behavior, not just higher scalar reward.

## 7. Certificate And Control Quality

![Certificate score by policy](../artifacts/exquisite-training/plots/38_certificate_score_by_policy.png)

![Control-satisfied resolution by policy](../artifacts/exquisite-training/plots/39_control_satisfied_resolution_by_policy.png)

Two numbers matter here:

- certificate score: `0.8478 -> 0.9653`
- control-satisfied resolution: `0.2222 -> 0.6667`

Both are more meaningful than raw score because they measure whether the decision was:

- properly justified,
- policy-complete,
- grounded in evidence,
- and clean enough to survive LedgerShield’s audit logic.

The fact that GRPO slightly exceeds the teacher on both of these dimensions is interesting. The clean interpretation is not “GRPO is globally better than the teacher.” The better interpretation is:

> on this slice, the GRPO policy learned a very certificate-heavy, control-heavy style that the environment rewards strongly.

The teacher still edges it on overall mean score.

## 8. Training Dynamics

![Smoothed GRPO reward curve](../artifacts/exquisite-training/plots/08_grpo_reward_curve_smoothed.png)

![GRPO certificate score over time](../artifacts/exquisite-training/plots/14_grpo_certificate_score_over_time.png)

![GRPO control satisfaction over time](../artifacts/exquisite-training/plots/15_grpo_control_satisfaction_over_time.png)

These plots are valuable because RL claims are easy to overstate if all you show is a final checkpoint.

The completed GRPO artifact pack includes:

- `grpo_reward_history.csv`
- `grpo_step_metrics.csv`
- `grpo_training_metrics.json`
- final adapter weights
- final held-out evaluation

### What the dynamics suggest

- reward did not collapse into a degenerate unsafe regime
- certificate quality remained strong enough to finish above the SFT baseline
- control-satisfaction behavior improved rather than drifting downward
- completion lengths moved around, which suggests the model was genuinely exploring different action-plan depths rather than emitting a frozen fixed-length template

This is not proof of global RL stability, but it is strong enough to support the claim that a real GRPO run happened and produced a coherent final policy.

## 9. Self-Play And Falsifier Evidence

![Self-play candidate reward distribution](../artifacts/exquisite-training/plots/17_selfplay_candidate_reward_distribution.png)

![Falsifier verdict distribution](../artifacts/exquisite-training/plots/20_falsifier_verdict_distribution.png)

![Parse failure taxonomy](../artifacts/exquisite-training/plots/22_parse_failure_taxonomy.png)

The self-play collector produced:

- `72` candidates
- `9` cases
- `8` generations per case
- `9` best-vs-worst preference pairs

Raw self-play noise is visible:

- `partial_json_recovery`: `31`
- `incorrect_resolution`: `10`
- `false_positive_overcontrol`: `7`
- `correct_but_policy_incomplete`: `5`
- `control_boundary_failed`: `3`
- `valid_success`: `16`

### Why that noise is actually useful evidence

If the candidate pool were unrealistically clean, the project would look synthetic. The noisy candidate distribution is exactly what you expect from real self-play over a structured action format.

The interesting part is what happens after the reward layer:

- raw candidate generation is messy
- the final GRPO policy is not messy
- final parse success returns to `1.0000`

That is a concrete sign that the reward environment is separating good behavior from bad behavior rather than just re-reporting demonstration quality.

## 10. Per-Case And Per-Task Analysis

![Per-case score heatmap](../artifacts/exquisite-training/plots/27_per_case_score_heatmap.png)

![Hardest cases before/after](../artifacts/exquisite-training/plots/35_hardest_cases_before_after.png)

![Cases where GRPO hurt](../artifacts/exquisite-training/plots/36_cases_where_grpo_hurt.png)

The GRPO held-out task-family means are:

- `task_a`: `0.9374`
- `task_c`: `0.4608`
- `task_d`: `0.8414`
- `task_e`: `0.6932`

### What this says

- The policy is very strong when it can combine structured document reading with policy/control reasoning.
- It is also strong on BEC-style and intervention-heavy task D behavior.
- Duplicate/fraud-cluster task C remains the weakest band in the current slice.

That pattern is plausible and valuable. It shows the policy is not uniformly “good at everything,” which makes the result more believable and more useful.

## 11. Scaling Signal

![Scaling law score vs model size](../artifacts/exquisite-training/plots/03_scaling_law_score_vs_model_size.png)

The current scaling claim should be stated carefully.

What the artifact pack does support:

- `SFT Qwen 1.5B` achieved `0.4798`
- that is above the `0.4394` `SFT Qwen 0.5B` number

What it does **not** fully support:

- a clean apples-to-apples model-size scaling law over the same held-out slice
- a finished `1.5B` or `3B` GRPO comparison

Why:

- the `1.5B` SFT run is a fast-profile run
- it uses a `3`-case held-out slice
- it skipped base-model pre-eval
- it is best read as “promising scaling signal,” not “final scaling-law conclusion”

This is still worth showing, but it should be framed honestly.

## 12. DPO Readout

![DPO after GRPO ablation](../artifacts/exquisite-training/plots/56_dpo_after_grpo_ablation.png)

The DPO run is artifact-complete and useful, but it is not the flagship.

Its main numbers:

- `mean_score`: `0.4503`
- `certificate_score`: `0.8408`
- `control_satisfied`: `0.2222`
- `unsafe_release`: `0.0000`
- `parse_success`: `1.0000`

Its result classes:

- `valid_success`: `2`
- `correct_but_policy_incomplete`: `2`
- `falsifier_blocked`: `2`
- `incorrect_resolution`: `3`

### Interpretation

The current DPO layer is better interpreted as:

- proof that preference distillation is wired end to end,
- proof that best-vs-worst falsifier pairs can be turned into a final adapter,
- but not proof that DPO improves on the GRPO policy.

That is still useful evidence. It just should not be oversold.

## 13. What The Analysis Supports

The current additive evidence pack strongly supports the following claims:

- LedgerShield now has a real environment-in-the-loop post-training pipeline.
- Self-play candidate generation is real and non-trivial.
- The deterministic falsifier and environment reward surface are doing meaningful sorting work.
- GRPO materially improves the 0.5B SFT policy.
- That improvement does not come from unsafe release.
- The additive layer belongs in a separate folder/docs/artifact lane from the original benchmark, and it already stands on its own as a judge-facing story.

## 14. What The Analysis Does Not Support

The current artifact pack does **not** justify these stronger claims yet:

- that DPO is the best final policy
- that full 1.5B and 3B GRPO scaling has already been demonstrated
- that raw self-play parsing noise has been solved universally
- that the benchmark has saturated and no longer distinguishes policy quality

Those are good future work targets, but they are not what the current artifacts prove.

## 15. Practical Judge Takeaway

If a reviewer reads only one paragraph from this document, it should be this:

> The original LedgerShield A10G SFT proof remains intact. On top of it, the project now adds a separate Exquisite layer where the model generates multiple AP-control plans, LedgerShield executes them, the deterministic falsifier and institutional metrics score them, and GRPO updates the policy from that real environment feedback. The flagship completed result is `GRPO Qwen 0.5B`, which reaches `0.6606` mean score against a `0.6627` teacher while preserving `0.0000` unsafe release and `1.0000` parse success.

That is a much stronger story than “we fine-tuned a model on benchmark JSON.”
