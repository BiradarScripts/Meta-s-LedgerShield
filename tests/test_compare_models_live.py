from __future__ import annotations

import io
import json
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
    assert "Tier" in output


def test_build_capability_summary_flags_non_monotonic_model_ordering():
    results = [
        compare_models_live.ModelStats(
            model="gpt-4o",
            average_score=0.92,
            success_rate=0.9,
            min_score=0.72,
            max_score=0.99,
            failed_cases=[],
            case_scores={"CASE-A-001": 0.92},
            api_calls=18,
            model_profile={"tier": "strong", "capability_score": 4.6},
        ),
        compare_models_live.ModelStats(
            model="gpt-5.4",
            average_score=0.81,
            success_rate=0.7,
            min_score=0.51,
            max_score=0.96,
            failed_cases=["CASE-D-004"],
            case_scores={"CASE-D-004": 0.81},
            api_calls=24,
            model_profile={"tier": "elite", "capability_score": 5.4},
        ),
    ]

    summary = compare_models_live.build_capability_summary(results)

    assert summary["ordered_models"] == ["gpt-4o", "gpt-5.4"]
    assert summary["monotonic_by_capability"] is False
    assert summary["violations"][0]["stronger_model"] == "gpt-5.4"


def test_build_output_payload_includes_cases_and_model_profiles():
    results = [
        compare_models_live.ModelStats(
            model="gpt-5.4",
            average_score=0.93,
            success_rate=0.86,
            min_score=0.71,
            max_score=0.99,
            failed_cases=["CASE-D-005"],
            case_scores={"CASE-D-005": 0.71},
            api_calls=32,
            debug_artifact_dir="live_model_comparison_debug/gpt-5.4",
            model_profile={"tier": "elite", "capability_score": 5.4},
            average_certificate_score=0.91,
            average_institutional_loss_score=0.73,
            case_certificate_scores={"CASE-D-005": 0.91},
            case_institutional_loss_scores={"CASE-D-005": 0.73},
        )
    ]

    payload = compare_models_live.build_output_payload(
        results,
        cases=["CASE-A-001", "CASE-D-005"],
        pass_threshold=0.85,
        api_base_url="https://api.openai.com/v1",
        env_url="http://127.0.0.1:8000",
    )

    assert payload["cases"] == ["CASE-A-001", "CASE-D-005"]
    assert payload["case_count"] == 2
    assert payload["capability_order"]["ordered_models"] == ["gpt-5.4"]
    assert payload["results"][0]["model_profile"]["tier"] == "elite"
    assert payload["results"][0]["average_certificate_score"] == 0.91
    assert payload["results"][0]["average_institutional_loss_score"] == 0.73
    assert payload["results"][0]["case_certificate_scores"] == {"CASE-D-005": 0.91}
    assert payload["results"][0]["case_institutional_loss_scores"] == {"CASE-D-005": 0.73}


def test_load_audit_scores_from_debug_artifacts(tmp_path):
    artifact_dir = tmp_path / "debug"
    artifact_dir.mkdir()
    (artifact_dir / "CASE-D-001.json").write_text(
        json.dumps(
            {
                "case_id": "CASE-D-001",
                "score_breakdown": {
                    "certificate_score": 0.82,
                    "institutional_loss_score": 0.69,
                },
            }
        ),
        encoding="utf-8",
    )

    certificate_scores, institutional_scores = compare_models_live._load_audit_scores_from_debug_artifacts(
        artifact_dir
    )

    assert certificate_scores == {"CASE-D-001": 0.82}
    assert institutional_scores == {"CASE-D-001": 0.69}
