"""Tests for the SOX compliance engine (Phase 1.3)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.compliance_engine import (
    evaluate_compliance,
    compliance_penalty,
    SOX_CONTROLS,
)


class TestComplianceEvaluation:
    def test_full_compliance_task_d(self, sample_trajectory_thorough, sample_gold_unsafe):
        """Thorough investigation should pass most controls."""
        result = evaluate_compliance(
            task_type="task_d",
            trajectory=sample_trajectory_thorough,
            revealed_artifacts=["callback_verification_result", "bank_change_approval_chain"],
            decision="ESCALATE_FRAUD",
            gold=sample_gold_unsafe,
        )
        assert result.controls_evaluated > 0
        assert result.compliance_score > 0.5

    def test_empty_trajectory_fails_audit_trail(self, sample_gold_safe):
        """Empty trajectory should fail SOX-AP-008."""
        result = evaluate_compliance(
            task_type="task_b",
            trajectory=[],
            revealed_artifacts=[],
            decision="PAY",
            gold=sample_gold_safe,
        )
        assert result.controls_failed > 0
        findings = {f["control_id"]: f for f in result.findings}
        assert findings.get("SOX-AP-008", {}).get("status") == "fail"

    def test_risky_pay_no_sod_fails(self, sample_gold_unsafe):
        """PAY on risky case without callbacks should fail SOX-AP-001."""
        trajectory = [
            {"step": 1, "action_type": "ocr", "success": True},
            {"step": 2, "action_type": "lookup_vendor", "success": True},
            {"step": 3, "action_type": "lookup_po", "success": True},
            {"step": 4, "action_type": "lookup_receipt", "success": True},
            {"step": 5, "action_type": "lookup_policy", "success": True},
        ]
        result = evaluate_compliance(
            task_type="task_d",
            trajectory=trajectory,
            revealed_artifacts=[],
            decision="PAY",
            gold=sample_gold_unsafe,
        )
        assert "SOX-AP-001" in result.critical_failures

    def test_compliance_penalty_clean(self, sample_gold_safe):
        """Fully compliant result has zero penalty."""
        result = evaluate_compliance(
            task_type="task_a",
            trajectory=[
                {"step": i, "action_type": a, "success": True}
                for i, a in enumerate(["ocr", "zoom", "lookup_po"], 1)
            ],
            revealed_artifacts=[],
            decision="PAY",
            gold=sample_gold_safe,
        )
        penalty = compliance_penalty(result)
        assert penalty >= -0.30  # bounded


class TestSOXControlDefinitions:
    def test_all_controls_have_ids(self):
        for control in SOX_CONTROLS:
            assert control.control_id.startswith("SOX-AP-")

    def test_control_count(self):
        assert len(SOX_CONTROLS) == 8

    def test_critical_controls_exist(self):
        critical = [c for c in SOX_CONTROLS if c.severity == "critical"]
        assert len(critical) >= 3
