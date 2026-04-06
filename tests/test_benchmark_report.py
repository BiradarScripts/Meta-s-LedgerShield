from __future__ import annotations

import benchmark_report


def test_build_report_returns_public_and_holdout_sections():
    report = benchmark_report.build_report(
        holdout_seeds=[101],
        variants_per_case=1,
        pass_threshold=0.8,
    )

    assert report["public_benchmark"]["case_count"] >= 1
    assert 0.0 <= report["public_benchmark"]["average_score"] <= 1.0
    assert report["holdout_challenge"]["seed_count"] == 1
    assert report["holdout_challenge"]["total_case_count"] >= 1
    assert "pass^4" in report["holdout_challenge"]["pass_k"]
