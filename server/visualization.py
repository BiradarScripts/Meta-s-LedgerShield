from __future__ import annotations

from copy import deepcopy
from typing import Any


def _compact_loss_surface(loss_surface: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, value in sorted((loss_surface or {}).items()):
        if key.endswith("_ratio") or key in {"fraud_loss_released", "fraud_loss_prevented", "false_positive_cost"}:
            rows.append({"id": key, "label": key.replace("_", " ").title(), "value": value})
    return rows


def _profile_points(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "agent_name": profile.get("agent_name"),
            "x_accuracy": profile.get("accuracy", 0.0),
            "y_institutional_loss_score": profile.get("institutional_loss_score", 0.0),
            "deployability_rating": profile.get("deployability_rating"),
            "unsafe_release_rate": profile.get("unsafe_release_rate", 0.0),
            "sleeper_detection_rate": profile.get("sleeper_detection_rate", 0.0),
        }
        for profile in profiles
    ]


def build_controlbench_visualization(
    report: dict[str, Any] | None = None,
    *,
    institutional_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a graph-ready visualization payload for demos and dashboards."""
    report = report or {}
    institutional_memory = institutional_memory or {}
    controlbench = report.get("controlbench_quarter", {}) if isinstance(report.get("controlbench_quarter"), dict) else {}
    controlbench_report = report.get("controlbench_report", {}) if isinstance(report.get("controlbench_report"), dict) else {}
    two_agent_demo = report.get("controlbench_two_agent_demo", {}) if isinstance(report.get("controlbench_two_agent_demo"), dict) else {}
    experiment_suite = report.get("experiment_suite", {}) if isinstance(report.get("experiment_suite"), dict) else {}

    if not controlbench and controlbench_report:
        controlbench = {
            "sequence_length": controlbench_report.get("case_count"),
            "sequence_seed": controlbench_report.get("sequence_seed"),
            "authority_timeline": controlbench_report.get("authority_timeline", []),
            "loss_surface": controlbench_report.get("loss_surface", {}),
            "deployability_rating": controlbench_report.get("deployability_rating"),
            "institutional_loss_score": controlbench_report.get("institutional_loss_score"),
            "certificate_validity_rate": controlbench_report.get("certificate_validity_rate"),
            "sleeper_detection_rate": controlbench_report.get("sleeper_detection_rate"),
        }
    if not controlbench and institutional_memory:
        ledger = institutional_memory.get("loss_ledger", {}) or {}
        controlbench = {
            "sequence_length": institutional_memory.get("case_counter", 0),
            "authority_timeline": [],
            "loss_surface": ledger.get("loss_surface", {}),
            "deployability_rating": "live_memory",
            "institutional_loss_score": ledger.get("institutional_loss_score", 1.0),
            "sleeper_detection_rate": (institutional_memory.get("controlbench_summary", {}) or {}).get("sleeper_detection_rate", 0.0),
        }

    profiles = list(two_agent_demo.get("profiles", []) or experiment_suite.get("baseline_matrix", []) or [])
    authority_timeline = list(controlbench.get("authority_timeline", []) or [])
    loss_surface = controlbench.get("loss_surface", {}) or {}
    certificate_ablation = experiment_suite.get("certificate_ablation", {}) if isinstance(experiment_suite.get("certificate_ablation"), dict) else {}
    trust_graph_ablation = experiment_suite.get("trust_graph_ablation", {}) if isinstance(experiment_suite.get("trust_graph_ablation"), dict) else {}

    return {
        "artifact_version": "ledgershield-controlbench-visualization-v1",
        "title": "LedgerShield ControlBench Authority Profile",
        "sequence": {
            "sequence_seed": controlbench.get("sequence_seed"),
            "case_count": controlbench.get("sequence_length", controlbench_report.get("case_count", 0)),
            "deployability_rating": controlbench.get("deployability_rating"),
            "institutional_loss_score": controlbench.get("institutional_loss_score"),
            "sleeper_detection_rate": controlbench.get("sleeper_detection_rate"),
        },
        "charts": {
            "accuracy_vs_institutional_loss": _profile_points(profiles),
            "authority_timeline": [
                {
                    "case_id": row.get("case_id"),
                    "sequence_index": row.get("sequence_index"),
                    "authority_level": row.get("authority_level"),
                    "institutional_loss_score": row.get("institutional_loss_score"),
                    "running_calibration_error": row.get("running_calibration_error"),
                }
                for row in authority_timeline
            ],
            "loss_surface": _compact_loss_surface(loss_surface),
            "certificate_gate": {
                "compatibility_mode_score": certificate_ablation.get("compatibility_certificate_mode_score"),
                "certificate_required_mode_score": certificate_ablation.get("certificate_required_mode_score"),
                "strict_gate_score_delta": certificate_ablation.get("strict_gate_score_delta"),
            },
            "trust_graph_health": {
                "support_rate": trust_graph_ablation.get("trust_graph_support_rate"),
                "cap_hit_rate": trust_graph_ablation.get("trust_graph_cap_hit_rate"),
                "top_failure_reasons": deepcopy(trust_graph_ablation.get("top_failure_reasons", {})),
            },
        },
        "graph_layers": {
            "trust_graph": "invoice/vendor/bank/evidence/risk/policy/decision/loss nodes with support, violation, requirement, and certificate edges",
            "certificate_graph": "agent-authored or compatibility Decision Certificate Graph nodes projected into TrustGraph",
            "authority_graph": "calibration gate and control-boundary nodes governing final authority",
        },
        "demo_script": [
            "Compare agents by accuracy and institutional loss, not accuracy alone.",
            "Show authority downgrades after calibration or catastrophic failures.",
            "Open the certificate gate panel to show why compatibility certificates are not enough for certification.",
            "Open TrustGraph health to show unsupported evidence paths and graph caps.",
        ],
    }
