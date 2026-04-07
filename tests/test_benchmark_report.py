from __future__ import annotations

import sys

import benchmark_report


def test_build_report_returns_public_and_holdout_sections():
    report = benchmark_report.build_report(
        holdout_seeds=[101],
        variants_per_case=1,
        pass_threshold=0.8,
        pass_k=2,
    )

    assert report["public_benchmark"]["case_count"] >= 1
    assert 0.0 <= report["public_benchmark"]["average_score"] <= 1.0
    assert report["holdout_challenge"]["seed_count"] == 1
    assert report["holdout_challenge"]["total_case_count"] >= 1
    assert report["evaluation_protocol"]["pass_k"] == 2
    assert "consistent_pass_rate" in report["holdout_challenge"]
    assert "contrastive_pairs" in report


def test_build_leaderboard_entry_includes_task_e_metrics():
    report = benchmark_report.build_report(
        holdout_seeds=[101],
        variants_per_case=1,
    )

    entry = benchmark_report.build_leaderboard_entry(
        report,
        model_name="openai/gpt-4.1-mini",
        agent_type="deterministic-policy",
    )

    assert entry["public_task_e_expert_mean"] == report["public_benchmark"]["task_breakdown"]["task_e"]["score_stats"]["mean"]
    assert entry["holdout_task_e_expert_mean"] == report["holdout_challenge"]["task_breakdown"]["task_e"]["score_stats"]["mean"]
    assert entry["task_e_expert_mean"] == entry["holdout_task_e_expert_mean"]


def test_main_cli_smoke_runs_without_token(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark_report.py",
            "--format",
            "markdown",
            "--skip-write",
            "--skip-leaderboard",
            "--holdout-seeds",
            "101",
        ],
    )

    benchmark_report.main()
    output = capsys.readouterr().out

    assert "# LedgerShield Benchmark Report" in output
    assert "Agent type: deterministic-policy" in output
