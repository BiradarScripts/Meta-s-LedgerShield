# LedgerShield Exquisite Training Scripts

The full additive Exquisite writeup lives in [`../../docs/DOCUMENTATION.md` — Exquisite Training Layer](../../docs/DOCUMENTATION.md#exquisite-training-layer), and the judge-facing visual interpretation lives in [`../../docs/DOCUMENTATION.md` — Exquisite Visual Analysis](../../docs/DOCUMENTATION.md#exquisite-visual-analysis).

Judge-rerunnable Colab entrypoint: [`./LedgerShield_Exquisite_Training_Colab.ipynb`](./LedgerShield_Exquisite_Training_Colab.ipynb)

Recommended submission-form notebook URL:
[https://huggingface.co/spaces/shreayas/ledgershield-controlbench/blob/main/training/exquisite/LedgerShield_Exquisite_Training_Colab.ipynb](https://huggingface.co/spaces/shreayas/ledgershield-controlbench/blob/main/training/exquisite/LedgerShield_Exquisite_Training_Colab.ipynb)

Supporting baseline notebook:
[https://huggingface.co/spaces/shreayas/ledgershield-controlbench/blob/main/training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb](https://huggingface.co/spaces/shreayas/ledgershield-controlbench/blob/main/training/LedgerShield_OpenEnv_TRL_Training_Colab.ipynb)

This directory contains the executable pieces for the modified environment-in-the-loop training process:

| File | Purpose |
|---|---|
| [`common.py`](./common.py) | Shared config, policy metadata, artifact helpers, and public report normalization |
| [`collect_selfplay_rollouts.py`](./collect_selfplay_rollouts.py) | Generates multi-candidate self-play rollouts from the SFT checkpoint and writes candidate / preference artifacts |
| [`grpo_env_reward_training.py`](./grpo_env_reward_training.py) | Runs environment-in-the-loop GRPO using LedgerShield reward and falsifier outcomes |
| [`dpo_falsifier_distill.py`](./dpo_falsifier_distill.py) | Builds falsifier-derived preference pairs and trains the DPO-style distillation adapter |
| [`evaluate_exquisite_policy.py`](./evaluate_exquisite_policy.py) | Builds the additive policy matrix and combined evaluation summaries |
| [`plot_exquisite_training_results.py`](./plot_exquisite_training_results.py) | Renders the 56 PNG visualization pack from additive training artifacts |
| [`build_exquisite_dashboard.py`](./build_exquisite_dashboard.py) | Generates the HTML dashboard and dashboard JSON |
| [`render_exquisite_report.py`](./render_exquisite_report.py) | Produces the Markdown report in `artifacts/exquisite-training/reports/` |
| [`launch_exquisite_jobs.py`](./launch_exquisite_jobs.py) | Launches the Hugging Face Jobs run matrix for the additive layer |
| [`monitor_exquisite_jobs.py`](./monitor_exquisite_jobs.py) | Refreshes artifacts and status from completed additive HF jobs |
| [`LedgerShield_Exquisite_Training_Colab.ipynb`](./LedgerShield_Exquisite_Training_Colab.ipynb) | Colab rerun entrypoint for the modified self-play -> GRPO -> DPO pipeline |

Primary additive evidence pack: [`../../artifacts/exquisite-training/`](../../artifacts/exquisite-training/)

Key output folders:

| Path | Contents |
|---|---|
| [`../../artifacts/exquisite-training/selfplay-0.5b/`](../../artifacts/exquisite-training/selfplay-0.5b/) | self-play candidates, preference pairs, self-play summary |
| [`../../artifacts/exquisite-training/grpo-0.5b/`](../../artifacts/exquisite-training/grpo-0.5b/) | GRPO reward history, step metrics, final evaluation, final adapter |
| [`../../artifacts/exquisite-training/sft-1.5b/`](../../artifacts/exquisite-training/sft-1.5b/) | fast-profile larger-model SFT metrics and examples |
| [`../../artifacts/exquisite-training/dpo-falsifier-distill/`](../../artifacts/exquisite-training/dpo-falsifier-distill/) | DPO pairs, step metrics, final evaluation |
| [`../../artifacts/exquisite-training/plots/`](../../artifacts/exquisite-training/plots/) | 56 committed PNG plots |
| [`../../artifacts/exquisite-training/dashboard/`](../../artifacts/exquisite-training/dashboard/) | judge-facing HTML dashboard |
| [`../../artifacts/exquisite-training/reports/`](../../artifacts/exquisite-training/reports/) | final policy matrix, report, summary, failure taxonomy, manifest |

Recommended reading order for the modified path:

1. [`../../docs/DOCUMENTATION.md` — Exquisite Training Layer](../../docs/DOCUMENTATION.md#exquisite-training-layer)
2. [`../../docs/DOCUMENTATION.md` — Exquisite Visual Analysis](../../docs/DOCUMENTATION.md#exquisite-visual-analysis)
3. [`./launch_exquisite_jobs.py`](./launch_exquisite_jobs.py)
4. [`./collect_selfplay_rollouts.py`](./collect_selfplay_rollouts.py)
5. [`./grpo_env_reward_training.py`](./grpo_env_reward_training.py)
6. [`./dpo_falsifier_distill.py`](./dpo_falsifier_distill.py)
7. [`../../artifacts/exquisite-training/dashboard/index.html`](../../artifacts/exquisite-training/dashboard/index.html)

Important scope note:

- The original SFT benchmark remains the supporting baseline proof and is documented separately in [`../README.md`](../README.md) and [`../../docs/DOCUMENTATION.md` — Training Evidence Report](../../docs/DOCUMENTATION.md#training-evidence-report).
- The Exquisite layer is the recommended single-link training submission because it best captures the reward-improvement and environment-in-the-loop learning story in one place.
