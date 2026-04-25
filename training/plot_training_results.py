#!/usr/bin/env python3
"""Generate readable PNG plots from a LedgerShield training metrics file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


POLICY_LABELS = {
    "random_baseline": "Random Baseline",
    "naive_baseline": "Naive PAY",
    "base_model": "Base Model",
    "trained_model": "Trained Model",
    "teacher_policy": "Teacher Policy",
}
POLICY_COLORS = {
    "random_baseline": "#bcbd22",
    "naive_baseline": "#d62728",
    "base_model": "#7f7f7f",
    "trained_model": "#2ca02c",
    "teacher_policy": "#1f77b4",
}


def load_metrics(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def ordered_policy_names(metrics: dict[str, Any]) -> list[str]:
    evaluations = metrics.get("evaluations", {}) or {}
    preferred = ["random_baseline", "naive_baseline", "base_model", "trained_model", "teacher_policy"]
    names = [name for name in preferred if name in evaluations]
    names.extend(sorted(name for name in evaluations if name not in names))
    return names


def policy_summary(metrics: dict[str, Any], name: str) -> dict[str, Any]:
    return ((metrics.get("evaluations", {}) or {}).get(name, {}) or {}).get(
        "summary", {}
    ) or {}


def policy_results(metrics: dict[str, Any], name: str) -> list[dict[str, Any]]:
    return ((metrics.get("evaluations", {}) or {}).get(name, {}) or {}).get(
        "results", []
    ) or []


def save_figure(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=170, bbox_inches="tight")
    plt.close()
    return path


def annotate_bars(values: list[float]) -> None:
    for index, value in enumerate(values):
        plt.text(
            index, value + 0.015, f"{value:.2f}", ha="center", va="bottom", fontsize=8
        )


def plot_no_data(path: Path, title: str, message: str) -> Path:
    plt.figure(figsize=(8, 4.5))
    plt.axis("off")
    plt.title(title, fontsize=14, weight="bold")
    plt.text(0.5, 0.5, message, ha="center", va="center", wrap=True, fontsize=11)
    return save_figure(path)


def plot_training_loss(metrics: dict[str, Any], output_dir: Path) -> Path:
    history = training_history(metrics)
    points = [
        (safe_float(row.get("step")), safe_float(row.get("loss")))
        for row in history
        if "loss" in row
    ]
    if not points:
        return plot_no_data(
            output_dir / "training_loss.png",
            "Training Loss",
            "No TRL loss history is present. Run ledgershield_trl_training.py with --train to populate this plot.",
        )
    steps, losses = zip(*points)
    plt.figure(figsize=(8, 4.5))
    plt.plot(steps, losses, marker="o", color="#2ca02c", linewidth=2)
    plt.title("TRL SFT Training Loss", fontsize=14, weight="bold")
    plt.xlabel("Training step")
    plt.ylabel("Language-model loss")
    plt.grid(True, alpha=0.25)
    return save_figure(output_dir / "training_loss.png")


def training_history(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in ((metrics.get("training", {}) or {}).get("log_history", []) or [])
        if isinstance(row, dict) and "loss" in row
    ]


def moving_average(values: list[float], window: int = 5) -> list[float]:
    smoothed = []
    for index in range(len(values)):
        start = max(0, index - window + 1)
        chunk = values[start : index + 1]
        smoothed.append(sum(chunk) / max(len(chunk), 1))
    return smoothed


def plot_training_loss_smoothed(metrics: dict[str, Any], output_dir: Path) -> Path:
    history = training_history(metrics)
    steps = [safe_float(row.get("step") or idx + 1) for idx, row in enumerate(history)]
    losses = [safe_float(row.get("loss")) for row in history]
    if not losses:
        return plot_no_data(output_dir / "training_loss_smoothed.png", "Smoothed Loss", "No loss data found.")
    plt.figure(figsize=(8, 4.5))
    plt.plot(steps, losses, color="#9edae5", alpha=0.6, label="raw loss")
    plt.plot(steps, moving_average(losses, window=5), color="#1f77b4", linewidth=2.4, label="5-step moving average")
    plt.title("Training Loss With Moving Average", fontsize=14, weight="bold")
    plt.xlabel("Training step")
    plt.ylabel("Loss")
    plt.legend()
    plt.grid(True, alpha=0.25)
    return save_figure(output_dir / "training_loss_smoothed.png")


def plot_metric_curve(metrics: dict[str, Any], output_dir: Path, key: str, filename: str, title: str, ylabel: str, color: str) -> Path:
    history = training_history(metrics)
    points = [
        (safe_float(row.get("step") or idx + 1), safe_float(row.get(key)))
        for idx, row in enumerate(history)
        if key in row
    ]
    if not points:
        return plot_no_data(output_dir / filename, title, f"No {key} data found.")
    steps, values = zip(*points)
    plt.figure(figsize=(8, 4.5))
    plt.plot(steps, values, marker="o", markersize=3, color=color, linewidth=1.8)
    plt.title(title, fontsize=14, weight="bold")
    plt.xlabel("Training step")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.25)
    return save_figure(output_dir / filename)


def plot_loss_accuracy_scatter(metrics: dict[str, Any], output_dir: Path) -> Path:
    history = training_history(metrics)
    points = [
        (safe_float(row.get("loss")), safe_float(row.get("mean_token_accuracy")))
        for row in history
        if "loss" in row and "mean_token_accuracy" in row
    ]
    if not points:
        return plot_no_data(output_dir / "loss_accuracy_scatter.png", "Loss vs Token Accuracy", "No paired loss/accuracy data found.")
    losses, accuracies = zip(*points)
    plt.figure(figsize=(7.5, 5.0))
    plt.scatter(losses, accuracies, color="#9467bd", alpha=0.78)
    plt.title("Loss vs Mean Token Accuracy", fontsize=14, weight="bold")
    plt.xlabel("Loss")
    plt.ylabel("Mean token accuracy")
    plt.grid(True, alpha=0.25)
    return save_figure(output_dir / "loss_accuracy_scatter.png")


def plot_tokens_processed(metrics: dict[str, Any], output_dir: Path) -> Path:
    return plot_metric_curve(
        metrics,
        output_dir,
        "num_tokens",
        "tokens_processed_curve.png",
        "Cumulative Tokens Processed",
        "Tokens",
        "#17becf",
    )


def reward_eval_history(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in ((metrics.get("training", {}) or {}).get("reward_eval_history", []) or [])
        if isinstance(row, dict) and "step" in row
    ]


def plot_checkpoint_reward_curve(metrics: dict[str, Any], output_dir: Path) -> Path:
    history = reward_eval_history(metrics)
    if not history:
        return plot_no_data(output_dir / "checkpoint_reward_curve.png", "Reward During Training", "No checkpoint reward evaluations were logged.")
    steps = [safe_float(row.get("step")) for row in history]
    scores = [safe_float(row.get("mean_score")) for row in history]
    parse = [safe_float(row.get("parse_success_rate")) for row in history]
    plt.figure(figsize=(8.5, 4.8))
    plt.plot(steps, scores, marker="o", linewidth=2.2, color="#2ca02c", label="mean final score")
    plt.plot(steps, parse, marker="s", linewidth=1.8, color="#1f77b4", label="parse success rate")
    for ref_name in ["random_baseline", "naive_baseline", "base_model"]:
        if ref_name in (metrics.get("evaluations", {}) or {}):
            y = safe_float(policy_summary(metrics, ref_name).get("mean_score"))
            plt.axhline(y, linestyle="--", linewidth=1.2, color=POLICY_COLORS.get(ref_name), alpha=0.65, label=f"{POLICY_LABELS.get(ref_name, ref_name)} score")
    plt.title("Environment Reward During Training", fontsize=14, weight="bold")
    plt.xlabel("Training step")
    plt.ylabel("Held-out eval rate / score")
    plt.ylim(0, 1.05)
    plt.grid(True, alpha=0.25)
    plt.legend(fontsize=8)
    return save_figure(output_dir / "checkpoint_reward_curve.png")


def plot_reward_improvement_ladder(metrics: dict[str, Any], output_dir: Path) -> Path:
    ordered = [name for name in ["random_baseline", "naive_baseline", "base_model", "trained_model", "teacher_policy"] if name in (metrics.get("evaluations", {}) or {})]
    if not ordered:
        return plot_no_data(output_dir / "reward_improvement_ladder.png", "Reward Improvement Ladder", "No evaluation policies found.")
    values = [safe_float(policy_summary(metrics, name).get("mean_score")) for name in ordered]
    labels = [POLICY_LABELS.get(name, name) for name in ordered]
    colors = [POLICY_COLORS.get(name, "#9467bd") for name in ordered]
    plt.figure(figsize=(8.8, 4.8))
    plt.plot(labels, values, color="#94a3b8", linewidth=1.4, zorder=1)
    plt.scatter(labels, values, s=160, color=colors, zorder=2)
    for idx, value in enumerate(values):
        plt.text(idx, value + 0.025, f"{value:.3f}", ha="center", va="bottom", fontsize=9, weight="bold")
    plt.title("Reward Improvement Ladder", fontsize=14, weight="bold")
    plt.ylabel("Mean final score")
    plt.ylim(0, max(1.0, max(values) + 0.12))
    plt.xticks(rotation=15, ha="right")
    plt.grid(True, axis="y", alpha=0.22)
    return save_figure(output_dir / "reward_improvement_ladder.png")


def plot_mean_score(metrics: dict[str, Any], output_dir: Path) -> Path:
    names = ordered_policy_names(metrics)
    values = [
        safe_float(policy_summary(metrics, name).get("mean_score")) for name in names
    ]
    labels = [POLICY_LABELS.get(name, name) for name in names]
    colors = [POLICY_COLORS.get(name, "#9467bd") for name in names]
    plt.figure(figsize=(8, 4.5))
    plt.bar(labels, values, color=colors)
    plt.ylim(0, max(1.0, max(values, default=0.0) + 0.12))
    annotate_bars(values)
    plt.title("Mean Final Score by Policy", fontsize=14, weight="bold")
    plt.ylabel("Mean final score")
    plt.xticks(rotation=15, ha="right")
    return save_figure(output_dir / "mean_reward_by_policy.png")


def plot_mean_total_reward(metrics: dict[str, Any], output_dir: Path) -> Path:
    names = ordered_policy_names(metrics)
    values = [
        safe_float(policy_summary(metrics, name).get("mean_total_reward"))
        for name in names
    ]
    labels = [POLICY_LABELS.get(name, name) for name in names]
    colors = [POLICY_COLORS.get(name, "#9467bd") for name in names]
    lower = min(values, default=0.0)
    upper = max(values, default=0.0)
    margin = max(0.1, (upper - lower) * 0.15 if upper != lower else 0.15)
    plt.figure(figsize=(8, 4.5))
    plt.bar(labels, values, color=colors)
    plt.axhline(0, color="#222222", linewidth=1)
    plt.ylim(lower - margin, upper + margin)
    annotate_bars(values)
    plt.title("Mean Episode Reward by Policy", fontsize=14, weight="bold")
    plt.ylabel("Mean total reward")
    plt.xticks(rotation=15, ha="right")
    return save_figure(output_dir / "mean_total_reward_by_policy.png")


def plot_case_delta(metrics: dict[str, Any], output_dir: Path) -> Path:
    before_name = (
        "base_model"
        if "base_model" in (metrics.get("evaluations", {}) or {})
        else "naive_baseline"
    )
    after_name = (
        "trained_model"
        if "trained_model" in (metrics.get("evaluations", {}) or {})
        else "teacher_policy"
    )
    before = {
        row.get("case_id"): safe_float(row.get("score"))
        for row in policy_results(metrics, before_name)
    }
    after = {
        row.get("case_id"): safe_float(row.get("score"))
        for row in policy_results(metrics, after_name)
    }
    cases = [case for case in after if case in before]
    if not cases:
        return plot_no_data(
            output_dir / "case_reward_delta.png",
            "Case Reward Delta",
            "No overlapping policy evaluations found.",
        )
    deltas = [after[case] - before[case] for case in cases]
    colors = ["#2ca02c" if value >= 0 else "#d62728" for value in deltas]
    plt.figure(figsize=(max(8, len(cases) * 0.45), 4.8))
    plt.bar(cases, deltas, color=colors)
    plt.axhline(0, color="#222222", linewidth=1)
    plt.title(
        f"Per-Case Reward Delta: {POLICY_LABELS.get(before_name, before_name)} to {POLICY_LABELS.get(after_name, after_name)}",
        fontsize=13,
        weight="bold",
    )
    plt.xlabel("Case")
    plt.ylabel("Score delta")
    plt.xticks(rotation=70, ha="right", fontsize=8)
    plt.grid(True, axis="y", alpha=0.2)
    return save_figure(output_dir / "case_reward_delta.png")


def plot_cumulative_reward(metrics: dict[str, Any], output_dir: Path) -> Path:
    names = ordered_policy_names(metrics)
    plt.figure(figsize=(8, 4.8))
    for name in names:
        results = policy_results(metrics, name)
        if not results:
            continue
        cumulative = []
        running = 0.0
        for index, row in enumerate(results, start=1):
            running += safe_float(row.get("score"))
            cumulative.append(running / index)
        plt.plot(
            range(1, len(cumulative) + 1),
            cumulative,
            marker="o",
            label=POLICY_LABELS.get(name, name),
            color=POLICY_COLORS.get(name),
        )
    plt.title(
        "Cumulative Mean Reward Over Evaluation Cases", fontsize=14, weight="bold"
    )
    plt.xlabel("Evaluation case index")
    plt.ylabel("Cumulative mean final score")
    plt.ylim(0, 1.05)
    plt.grid(True, alpha=0.25)
    plt.legend()
    return save_figure(output_dir / "cumulative_mean_reward.png")


def plot_safety_metrics(metrics: dict[str, Any], output_dir: Path) -> Path:
    names = ordered_policy_names(metrics)
    metric_keys = [
        "unsafe_release_rate",
        "control_satisfied_resolution_rate",
        "parse_success_rate",
    ]
    labels = ["Unsafe release", "Control satisfied", "Parse success"]
    x = range(len(metric_keys))
    width = 0.8 / max(len(names), 1)
    plt.figure(figsize=(9, 4.8))
    for idx, name in enumerate(names):
        summary = policy_summary(metrics, name)
        values = [safe_float(summary.get(key)) for key in metric_keys]
        offsets = [pos - 0.4 + width / 2 + idx * width for pos in x]
        plt.bar(
            offsets,
            values,
            width=width,
            label=POLICY_LABELS.get(name, name),
            color=POLICY_COLORS.get(name),
        )
    plt.title("Safety and Executability Metrics", fontsize=14, weight="bold")
    plt.ylabel("Rate")
    plt.ylim(0, 1.05)
    plt.xticks(list(x), labels)
    plt.legend(fontsize=8)
    plt.grid(True, axis="y", alpha=0.2)
    return save_figure(output_dir / "safety_and_parse_metrics.png")


def plot_result_classes(metrics: dict[str, Any], output_dir: Path) -> Path:
    names = ordered_policy_names(metrics)
    classes = sorted(
        {
            result_class
            for name in names
            for result_class in policy_summary(metrics, name)
            .get("result_class_counts", {})
            .keys()
        }
    )
    if not classes:
        return plot_no_data(
            output_dir / "result_class_distribution.png",
            "Result Classes",
            "No result_class data found.",
        )
    bottom = [0.0] * len(names)
    labels = [POLICY_LABELS.get(name, name) for name in names]
    plt.figure(figsize=(8.5, 4.8))
    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
    for idx, result_class in enumerate(classes):
        values = [
            safe_float(
                policy_summary(metrics, name)
                .get("result_class_counts", {})
                .get(result_class, 0)
            )
            for name in names
        ]
        plt.bar(
            labels,
            values,
            bottom=bottom,
            label=result_class,
            color=palette[idx % len(palette)],
        )
        bottom = [base + value for base, value in zip(bottom, values)]
    plt.title("Terminal Result-Class Distribution", fontsize=14, weight="bold")
    plt.ylabel("Case count")
    plt.xticks(rotation=15, ha="right")
    plt.legend(fontsize=8)
    return save_figure(output_dir / "result_class_distribution.png")


def plot_reward_components(metrics: dict[str, Any], output_dir: Path) -> Path:
    names = ordered_policy_names(metrics)
    keys = [
        "institutional_utility_mean",
        "institutional_loss_score_mean",
        "control_satisfied_resolution_rate",
    ]
    labels = ["Institutional utility", "Loss score", "Control satisfied"]
    x = range(len(keys))
    width = 0.8 / max(len(names), 1)
    plt.figure(figsize=(9, 4.8))
    for idx, name in enumerate(names):
        values = [safe_float(policy_summary(metrics, name).get(key)) for key in keys]
        offsets = [pos - 0.4 + width / 2 + idx * width for pos in x]
        plt.bar(
            offsets,
            values,
            width=width,
            label=POLICY_LABELS.get(name, name),
            color=POLICY_COLORS.get(name),
        )
    plt.title("Institutional Reward Components", fontsize=14, weight="bold")
    plt.ylabel("Mean component value")
    plt.ylim(0, 1.05)
    plt.xticks(list(x), labels)
    plt.legend(fontsize=8)
    plt.grid(True, axis="y", alpha=0.2)
    return save_figure(output_dir / "institutional_reward_components.png")


def plot_certificate_scores(metrics: dict[str, Any], output_dir: Path) -> Path:
    names = ordered_policy_names(metrics)
    values = [
        safe_float(policy_summary(metrics, name).get("certificate_score_mean"))
        for name in names
    ]
    labels = [POLICY_LABELS.get(name, name) for name in names]
    colors = [POLICY_COLORS.get(name, "#9467bd") for name in names]
    plt.figure(figsize=(8, 4.5))
    plt.bar(labels, values, color=colors)
    plt.ylim(0, max(1.0, max(values, default=0.0) + 0.12))
    annotate_bars(values)
    plt.title("Mean Certificate Score by Policy", fontsize=14, weight="bold")
    plt.ylabel("Mean certificate score")
    plt.xticks(rotation=15, ha="right")
    return save_figure(output_dir / "certificate_score_by_policy.png")


def plot_score_safety_frontier(metrics: dict[str, Any], output_dir: Path) -> Path:
    names = ordered_policy_names(metrics)
    plt.figure(figsize=(7.5, 5.2))
    for name in names:
        summary = policy_summary(metrics, name)
        x = safe_float(summary.get("unsafe_release_rate"))
        y = safe_float(summary.get("mean_score"))
        size = max(
            120.0, 600.0 * safe_float(summary.get("control_satisfied_resolution_rate"))
        )
        plt.scatter(
            x,
            y,
            s=size,
            color=POLICY_COLORS.get(name, "#9467bd"),
            alpha=0.8,
            label=POLICY_LABELS.get(name, name),
        )
        plt.text(x + 0.01, y + 0.01, POLICY_LABELS.get(name, name), fontsize=8)
    plt.title("Score vs Safety Frontier", fontsize=14, weight="bold")
    plt.xlabel("Unsafe release rate")
    plt.ylabel("Mean final score")
    plt.xlim(-0.02, 1.02)
    plt.ylim(0, 1.05)
    plt.grid(True, alpha=0.25)
    plt.legend(fontsize=8)
    return save_figure(output_dir / "score_safety_frontier.png")


def plot_trajectory_lengths(metrics: dict[str, Any], output_dir: Path) -> Path:
    names = ordered_policy_names(metrics)
    values = [
        safe_float(policy_summary(metrics, name).get("mean_steps")) for name in names
    ]
    labels = [POLICY_LABELS.get(name, name) for name in names]
    colors = [POLICY_COLORS.get(name, "#9467bd") for name in names]
    plt.figure(figsize=(8, 4.5))
    plt.bar(labels, values, color=colors)
    annotate_bars(values)
    plt.title("Mean Episode Length", fontsize=14, weight="bold")
    plt.ylabel("Environment steps")
    plt.xticks(rotation=15, ha="right")
    return save_figure(output_dir / "mean_episode_length.png")


def plot_per_case_scores(metrics: dict[str, Any], output_dir: Path) -> Path:
    names = ordered_policy_names(metrics)
    cases = []
    for name in names:
        for row in policy_results(metrics, name):
            case_id = row.get("case_id")
            if case_id and case_id not in cases:
                cases.append(case_id)
    if not cases:
        return plot_no_data(output_dir / "per_case_scores_by_policy.png", "Per-Case Scores", "No evaluation results found.")
    width = 0.8 / max(len(names), 1)
    plt.figure(figsize=(max(9, len(cases) * 0.7), 5.0))
    x_positions = list(range(len(cases)))
    for idx, name in enumerate(names):
        scores = {row.get("case_id"): safe_float(row.get("score")) for row in policy_results(metrics, name)}
        offsets = [x - 0.4 + width / 2 + idx * width for x in x_positions]
        plt.bar(offsets, [scores.get(case, 0.0) for case in cases], width=width, label=POLICY_LABELS.get(name, name), color=POLICY_COLORS.get(name))
    plt.title("Per-Case Final Scores by Policy", fontsize=14, weight="bold")
    plt.xlabel("Evaluation case")
    plt.ylabel("Final score")
    plt.ylim(0, 1.05)
    plt.xticks(x_positions, cases, rotation=65, ha="right", fontsize=8)
    plt.legend(fontsize=8)
    plt.grid(True, axis="y", alpha=0.2)
    return save_figure(output_dir / "per_case_scores_by_policy.png")


def plot_policy_score_boxplot(metrics: dict[str, Any], output_dir: Path) -> Path:
    names = ordered_policy_names(metrics)
    values = [[safe_float(row.get("score")) for row in policy_results(metrics, name)] for name in names]
    labels = [POLICY_LABELS.get(name, name) for name in names]
    if not any(values):
        return plot_no_data(output_dir / "policy_score_boxplot.png", "Policy Score Distribution", "No policy score data found.")
    plt.figure(figsize=(8, 4.8))
    plt.boxplot(values, labels=labels, patch_artist=True)
    plt.title("Policy Score Distribution", fontsize=14, weight="bold")
    plt.ylabel("Final score")
    plt.ylim(0, 1.05)
    plt.xticks(rotation=15, ha="right")
    plt.grid(True, axis="y", alpha=0.2)
    return save_figure(output_dir / "policy_score_boxplot.png")


def plot_reward_vs_steps(metrics: dict[str, Any], output_dir: Path) -> Path:
    names = ordered_policy_names(metrics)
    plt.figure(figsize=(7.5, 5.0))
    has_data = False
    for name in names:
        results = policy_results(metrics, name)
        if not results:
            continue
        has_data = True
        plt.scatter(
            [safe_float(row.get("steps")) for row in results],
            [safe_float(row.get("score")) for row in results],
            color=POLICY_COLORS.get(name),
            label=POLICY_LABELS.get(name, name),
            alpha=0.8,
        )
    if not has_data:
        return plot_no_data(output_dir / "reward_vs_steps_scatter.png", "Reward vs Steps", "No policy evaluation data found.")
    plt.title("Reward vs Episode Length", fontsize=14, weight="bold")
    plt.xlabel("Environment steps")
    plt.ylabel("Final score")
    plt.ylim(0, 1.05)
    plt.legend(fontsize=8)
    plt.grid(True, alpha=0.25)
    return save_figure(output_dir / "reward_vs_steps_scatter.png")


def create_plots(metrics_path: Path | str, output_dir: Path | str) -> list[Path]:
    metrics_path = Path(metrics_path)
    output_dir = Path(output_dir)
    metrics = load_metrics(metrics_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    return [
        plot_training_loss(metrics, output_dir),
        plot_training_loss_smoothed(metrics, output_dir),
        plot_metric_curve(metrics, output_dir, "mean_token_accuracy", "token_accuracy_curve.png", "Mean Token Accuracy", "Mean token accuracy", "#2ca02c"),
        plot_metric_curve(metrics, output_dir, "learning_rate", "learning_rate_schedule.png", "Learning Rate Schedule", "Learning rate", "#ff7f0e"),
        plot_metric_curve(metrics, output_dir, "grad_norm", "grad_norm_curve.png", "Gradient Norm", "Gradient norm", "#d62728"),
        plot_metric_curve(metrics, output_dir, "entropy", "entropy_curve.png", "Token Entropy", "Entropy", "#8c564b"),
        plot_tokens_processed(metrics, output_dir),
        plot_loss_accuracy_scatter(metrics, output_dir),
        plot_checkpoint_reward_curve(metrics, output_dir),
        plot_reward_improvement_ladder(metrics, output_dir),
        plot_mean_score(metrics, output_dir),
        plot_mean_total_reward(metrics, output_dir),
        plot_case_delta(metrics, output_dir),
        plot_cumulative_reward(metrics, output_dir),
        plot_safety_metrics(metrics, output_dir),
        plot_result_classes(metrics, output_dir),
        plot_reward_components(metrics, output_dir),
        plot_certificate_scores(metrics, output_dir),
        plot_score_safety_frontier(metrics, output_dir),
        plot_trajectory_lengths(metrics, output_dir),
        plot_per_case_scores(metrics, output_dir),
        plot_policy_score_boxplot(metrics, output_dir),
        plot_reward_vs_steps(metrics, output_dir),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render LedgerShield training plots.")
    parser.add_argument("--metrics", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = create_plots(args.metrics, args.output_dir)
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
