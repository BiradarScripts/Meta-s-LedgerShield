# LedgerShield OpenEnv Hackathon Alignment

This document checks the current LedgerShield repository against the OpenEnv Hackathon India 2026 judging criteria and minimum submission requirements. It treats the project as two connected but separate training surfaces:

- the original OpenEnv-connected SFT benchmark proof, and
- the additive Exquisite environment-in-the-loop post-training layer.

The goal is simple: make it easy for a judge to verify that the repository contains a novel environment, a coherent reward and training pipeline, real before/after learning evidence, and a clear story.

## Executive Verdict

LedgerShield aligns well with the strict submission guidance.

The repository already satisfies the non-negotiables:

- valid OpenEnv environment contract in [`../openenv.yaml`](../openenv.yaml)
- runnable Hugging Face Space in the root [`README.md`](../README.md)
- working Hugging Face TRL training scripts for the original benchmark under [`../training/`](../training/)
- a Colab rerun notebook for the original SFT path in [`../training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb`](../training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb)
- a separate Colab rerun notebook for the additive Exquisite path in [`../training/exquisite/LedgerShield_Exquisite_Training_Colab.ipynb`](../training/exquisite/LedgerShield_Exquisite_Training_Colab.ipynb)
- committed PNG plot evidence for both the original SFT proof and the additive Exquisite layer
- a pitch deck link in the README
- detailed benchmark, training, and visual-analysis docs linked from the README

The main repo improvements added for alignment are:

- a tighter README judge path with direct submission-material links
- embedded key training plots in the README
- a dedicated modified-training index at [`../training/exquisite/README.md`](../training/exquisite/README.md)
- a separate modified-training Colab notebook at [`../training/exquisite/LedgerShield_Exquisite_Training_Colab.ipynb`](../training/exquisite/LedgerShield_Exquisite_Training_Colab.ipynb)
- this explicit alignment document for judges and reviewers

## Judging Criteria Mapping

| Criterion | Weight | LedgerShield evidence | Verdict |
|---|---:|---|---|
| Environment Innovation | 40% | POMDP enterprise AP fraud world, ASHTG formalism, calibration-gated authority, institutional memory, sleeper-vendor attacks, deterministic decision falsifier, certificate-required track, 9 official tracks | Strong |
| Storytelling | 30% | README narrative, problem framing, pitch deck link, consolidated docs, original SFT report, Exquisite deep-dive report, dashboard, mini-blog source | Strong after README tightening |
| Showing Improvement in Rewards | 20% | Original A10G SFT loss and reward plots, baseline-vs-trained comparisons, Exquisite GRPO reward curves, teacher-gap closure, policy ladders, safety frontier, per-case deltas | Strong |
| Reward and Training Script/Pipeline Setup | 10% | Original TRL SFT script + launcher + Colab, additive self-play -> environment execution -> falsifier -> GRPO -> DPO scripts, coherent reward decomposition, artifact inventories | Strong |

## Minimum Submission Requirements

| Requirement | Evidence in repo | Status |
|---|---|---|
| Use OpenEnv latest release and framework | [`../openenv.yaml`](../openenv.yaml), FastAPI app wiring, `reset/step/state` environment contract documented in [`DOCUMENTATION.md`](./DOCUMENTATION.md) | Satisfied |
| Working training script using Unsloth or Hugging Face TRL | Original path: [`../training/ledgershield_trl_training.py`](../training/ledgershield_trl_training.py), [`../training/launch_hf_a10g_qwen_job.py`](../training/launch_hf_a10g_qwen_job.py) | Satisfied |
| Ideally a Colab notebook judges can rerun | Original path: [`../training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb`](../training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb); additive path: [`../training/exquisite/LedgerShield_Exquisite_Training_Colab.ipynb`](../training/exquisite/LedgerShield_Exquisite_Training_Colab.ipynb) | Satisfied |
| Evidence that training actually happened | [`./training-report.md`](./training-report.md), [`../artifacts/trl-openenv-hf-a10g-qwen-rich/`](../artifacts/trl-openenv-hf-a10g-qwen-rich/), [`../artifacts/exquisite-training/`](../artifacts/exquisite-training/) | Satisfied |
| Loss and reward plots from a real run | Original plot pack under [`../artifacts/trl-openenv-hf-a10g-qwen-rich/plots/`](../artifacts/trl-openenv-hf-a10g-qwen-rich/plots/), Exquisite plot pack under [`../artifacts/exquisite-training/plots/`](../artifacts/exquisite-training/plots/) | Satisfied |
| Short writeup, blog, video, or slide deck linked from README | Public pitch deck link in [`../README.md`](../README.md), plus linked docs and mini-blog source | Satisfied |
| Environment pushed to a Hugging Face Space | Linked in [`../README.md`](../README.md) as [Hugging Face Space](https://huggingface.co/spaces/shreayas/ledgershield-controlbench) | Satisfied |
| README motivates problem, explains env, and shows results | [`../README.md`](../README.md) | Satisfied |
| README links to the Space and extra materials | [`../README.md`](../README.md) | Satisfied |

## Original SFT Benchmark Path

This path is the minimum-submission anchor. It is the cleanest answer to “did the team really train against the environment?”

### What it proves

- live environment trajectory collection
- TRL SFT on executable LedgerShield plans
- held-out improvement over random, naive, and base-model baselines
- committed loss/reward/safety/certificate plots
- a judge-rerunnable Colab notebook

### Primary files

- Runner: [`../training/ledgershield_trl_training.py`](../training/ledgershield_trl_training.py)
- HF launcher: [`../training/launch_hf_a10g_qwen_job.py`](../training/launch_hf_a10g_qwen_job.py)
- Colab: [`../training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb`](../training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb)
- Training doc: [`./training-report.md`](./training-report.md)
- Artifact pack: [`../artifacts/trl-openenv-hf-a10g-qwen-rich/`](../artifacts/trl-openenv-hf-a10g-qwen-rich/)

### Key numbers

- Base Qwen 0.5B: `0.1283`
- SFT Qwen 0.5B: `0.4394`
- Held-out parse success: `1.0000`
- Held-out unsafe release: `0.0000`

This path alone already satisfies the minimum training requirement well.

## Additive Exquisite Training Path

This path is not required to satisfy the minimum bar, but it materially strengthens the score on innovation, storytelling, and reward-improvement evidence.

### What it proves

- the environment is usable as a post-training surface, not just an evaluation benchmark
- self-play candidate generation produces a nontrivial quality distribution
- deterministic reward and falsifier scoring can rank those candidates
- GRPO improves the same model family from `0.4394` to `0.6606`
- the additive pipeline preserves `0.0000` unsafe release and `1.0000` parse success

### Primary files

- Package index: [`../training/exquisite/README.md`](../training/exquisite/README.md)
- Colab rerun notebook: [`../training/exquisite/LedgerShield_Exquisite_Training_Colab.ipynb`](../training/exquisite/LedgerShield_Exquisite_Training_Colab.ipynb)
- Pipeline doc: [`./exquisite-training-layer.md`](./exquisite-training-layer.md)
- Visual analysis: [`./exquisite-visual-analysis.md`](./exquisite-visual-analysis.md)
- Artifact pack: [`../artifacts/exquisite-training/`](../artifacts/exquisite-training/)
- Dashboard: [`../artifacts/exquisite-training/dashboard/index.html`](../artifacts/exquisite-training/dashboard/index.html)

### Key numbers

- SFT Qwen 0.5B: `0.4394`
- GRPO Qwen 0.5B: `0.6606`
- Teacher: `0.6627`
- GRPO teacher-gap closure: `99.6%`
- GRPO unsafe release: `0.0000`
- GRPO parse success: `1.0000`

### Honest caveats

- The completed `SFT Qwen 1.5B` artifact is a fast-profile scaling run on a smaller held-out slice, so it should be described as a scaling signal rather than as a flagship apples-to-apples comparison.
- The repo should present GRPO as the flagship additive result. DPO is implemented and complete, but it is not the best final policy.

These caveats do not weaken the core submission. They simply make the storytelling more honest and credible.

## Why The Reward Story Is Coherent

The reward and evaluation setup is one of the strongest parts of the repository:

- the environment uses shaped reward plus terminal rubric reward rather than a single brittle binary success bit
- the rubric includes certificate quality, control satisfaction, institutional utility, and safety-sensitive penalties
- the additive training layer uses deterministic environment outcomes and falsifier signals, not an unrelated offline heuristic
- the best improved policy does not gain score by taking unsafe shortcuts

The most judge-relevant evidence is visible in:

- [`../artifacts/trl-openenv-hf-a10g-qwen-rich/plots/checkpoint_reward_curve.png`](../artifacts/trl-openenv-hf-a10g-qwen-rich/plots/checkpoint_reward_curve.png)
- [`../artifacts/exquisite-training/plots/08_grpo_reward_curve_smoothed.png`](../artifacts/exquisite-training/plots/08_grpo_reward_curve_smoothed.png)
- [`../artifacts/exquisite-training/plots/04_score_safety_frontier_all_policies.png`](../artifacts/exquisite-training/plots/04_score_safety_frontier_all_policies.png)

## Recommended Judge Reading Order

For a fast 3-to-5 minute evaluation pass:

1. [`../README.md`](../README.md)
2. [`./training-report.md`](./training-report.md)
3. [`./exquisite-training-layer.md`](./exquisite-training-layer.md)
4. [`./exquisite-visual-analysis.md`](./exquisite-visual-analysis.md)
5. [`../artifacts/exquisite-training/dashboard/index.html`](../artifacts/exquisite-training/dashboard/index.html)

For a deeper technical pass:

1. [`./DOCUMENTATION.md`](./DOCUMENTATION.md)
2. [`../training/README.md`](../training/README.md)
3. [`../training/exquisite/README.md`](../training/exquisite/README.md)
4. [`../openenv.yaml`](../openenv.yaml)

## Bottom Line

LedgerShield now presents a strong two-layer training story that aligns with the OpenEnv Hackathon rubric:

- a clear, runnable, OpenEnv-native benchmark
- a real original TRL SFT training proof with rerunnable notebook and plots
- an additive environment-in-the-loop GRPO layer that visibly improves behavior and rewards
- a README and doc stack that points judges directly to the evidence
