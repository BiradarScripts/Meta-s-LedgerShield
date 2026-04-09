from __future__ import annotations

import json
import sys
from pathlib import Path

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


def test_load_leaderboard_payload_filters_legacy_deterministic_alias(tmp_path: Path):
    report = benchmark_report.build_report(
        holdout_seeds=[101],
        variants_per_case=1,
    )
    canonical = benchmark_report.build_leaderboard_entry(
        report,
        model_name=benchmark_report.DETERMINISTIC_BASELINE_MODEL,
        agent_type="deterministic-policy",
    )
    legacy_alias = {
        **canonical,
        "model": "gpt-5.4",
        "public_mean": round(canonical["public_mean"] - 0.02, 4),
        "holdout_mean": round(canonical["holdout_mean"] + 0.03, 4),
        "updated_at": "2026-04-01T00:00:00+00:00",
    }
    leaderboard_path = tmp_path / "leaderboard.json"
    leaderboard_path.write_text(
        json.dumps(
            {
                "benchmark": "ledgershield-v3",
                "generated_at": report["generated_at"],
                "entries": [legacy_alias, canonical],
            }
        ),
        encoding="utf-8",
    )
    report_path = tmp_path / "benchmark_report_latest.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    payload = benchmark_report.load_leaderboard_payload(
        leaderboard_path=leaderboard_path,
        report_path=report_path,
    )

    assert payload["entries"] == [canonical]


def test_upsert_leaderboard_entry_prunes_legacy_alias(tmp_path: Path):
    report = benchmark_report.build_report(
        holdout_seeds=[101],
        variants_per_case=1,
    )
    entry = benchmark_report.build_leaderboard_entry(
        report,
        model_name=benchmark_report.DETERMINISTIC_BASELINE_MODEL,
        agent_type="deterministic-policy",
    )
    legacy_payload = {
        "benchmark": "ledgershield-v3",
        "generated_at": report["generated_at"],
        "entries": [
            {
                **entry,
                "model": "gpt-5.4",
                "updated_at": "2026-04-01T00:00:00+00:00",
            }
        ],
    }
    leaderboard_path = tmp_path / "leaderboard.json"
    leaderboard_path.write_text(json.dumps(legacy_payload), encoding="utf-8")

    updated = benchmark_report.upsert_leaderboard_entry(
        entry,
        leaderboard_path=leaderboard_path,
    )

    assert updated["entries"] == [entry]
