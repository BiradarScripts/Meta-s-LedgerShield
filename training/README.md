# LedgerShield Training Scripts

The full training writeup now lives in [`../docs/training-report.md`](../docs/training-report.md).

This directory contains the executable pieces referenced by that report:

| File | Purpose |
|---|---|
| [`ledgershield_trl_training.py`](./ledgershield_trl_training.py) | Collects live OpenEnv rollouts, builds TRL SFT records, trains/evaluates Qwen, and writes plots/metrics |
| [`launch_hf_a10g_qwen_job.py`](./launch_hf_a10g_qwen_job.py) | Launches the reproducible Hugging Face A10G training job |
| [`plot_training_results.py`](./plot_training_results.py) | Renders reviewer-readable PNG plots from `training_metrics.json` |
| [`LedgerShield_OpenEnv_TRL_Training_Colab.ipynb`](./LedgerShield_OpenEnv_TRL_Training_Colab.ipynb) | Colab entrypoint for judges who want to rerun the pipeline |
| [`requirements-training.txt`](./requirements-training.txt) | Training-only dependency pins |

Primary evidence run: [`../artifacts/trl-openenv-hf-a10g-qwen-rich/`](../artifacts/trl-openenv-hf-a10g-qwen-rich/)
