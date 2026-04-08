from __future__ import annotations

import io
from contextlib import redirect_stdout

import compare_models_live


def test_score_from_end_prefers_exact_score_over_rounded_rewards():
    exact = compare_models_live._score_from_end("0.9562", "-0.06,-0.06,0.95")
    fallback = compare_models_live._score_from_end(None, "-0.06,-0.06,0.95")

    assert exact == 0.9562
    assert fallback == 0.95


def test_live_comparison_defaults_include_task_e_case():
    assert "CASE-E-001" in compare_models_live.DEFAULT_CASES


def test_print_table_supports_more_than_two_models():
    results = [
        compare_models_live.ModelStats(
            model="gpt-3.5-turbo",
            average_score=0.71,
            success_rate=0.5,
            min_score=0.4,
            max_score=0.9,
            failed_cases=["CASE-D-001"],
            case_scores={"CASE-D-001": 0.4},
            api_calls=10,
        ),
        compare_models_live.ModelStats(
            model="gpt-4o",
            average_score=0.82,
            success_rate=0.75,
            min_score=0.5,
            max_score=0.95,
            failed_cases=["CASE-D-003"],
            case_scores={"CASE-D-003": 0.5},
            api_calls=10,
        ),
        compare_models_live.ModelStats(
            model="gpt-5.4",
            average_score=0.9,
            success_rate=0.83,
            min_score=0.6,
            max_score=0.99,
            failed_cases=[],
            case_scores={"CASE-D-004": 0.9},
            api_calls=10,
        ),
    ]

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        compare_models_live.print_table(results)
    output = buffer.getvalue()

    assert "gpt-3.5-turbo" in output
    assert "gpt-4o" in output
    assert "gpt-5.4" in output
    assert "Average Score" in output
