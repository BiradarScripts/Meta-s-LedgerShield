"""
Regulatory compliance engine for LedgerShield.

Implements SOX (Sarbanes-Oxley) Section 404 internal controls for
accounts payable processes. Evaluates whether an agent's investigation
and decision-making adheres to enterprise compliance requirements.

SOX Controls Modeled:
    - SOX-AP-001: Segregation of duties (no single approver)
    - SOX-AP-002: Three-way match verification (PO, receipt, invoice)
    - SOX-AP-003: Bank change verification protocol
    - SOX-AP-004: Duplicate payment prevention
    - SOX-AP-005: Approval threshold enforcement
    - SOX-AP-006: Vendor master data verification
    - SOX-AP-007: Callback verification for high-risk payments
    - SOX-AP-008: Audit trail completeness
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .schema import normalize_text


@dataclass
class SOXControl:
    """A single SOX internal control definition.

    Attributes:
        control_id: Unique identifier (e.g. SOX-AP-001).
        name: Human-readable control name.
        description: What the control verifies.
        required_actions: Actions that must be in trajectory to satisfy.
        required_artifacts: Artifacts that must be revealed.
        severity: Impact level if control fails (critical/high/medium).
        applies_to: Task types this control applies to.
    """
    control_id: str = ""
    name: str = ""
    description: str = ""
    required_actions: list[str] = field(default_factory=list)
    required_artifacts: list[str] = field(default_factory=list)
    severity: str = "high"
    applies_to: list[str] = field(default_factory=list)


SOX_CONTROLS: list[SOXControl] = [
    SOXControl(
        control_id="SOX-AP-001",
        name="Segregation of Duties",
        description="Payment decisions require independent verification. "
                    "Agent must use callback or human handoff for high-risk.",
        required_actions=["request_callback_verification", "create_human_handoff"],
        severity="critical",
        applies_to=["task_c", "task_d", "task_e"],
    ),
    SOXControl(
        control_id="SOX-AP-002",
        name="Three-Way Match",
        description="Invoice must be matched against PO and receipt.",
        required_actions=["lookup_po", "lookup_receipt"],
        severity="high",
        applies_to=["task_a", "task_b", "task_c", "task_d", "task_e"],
    ),
    SOXControl(
        control_id="SOX-AP-003",
        name="Bank Change Verification",
        description="Any bank account change must go through approval chain.",
        required_actions=["compare_bank_account", "request_bank_change_approval_chain"],
        required_artifacts=["bank_change_approval_chain"],
        severity="critical",
        applies_to=["task_b", "task_c", "task_d", "task_e"],
    ),
    SOXControl(
        control_id="SOX-AP-004",
        name="Duplicate Payment Prevention",
        description="Ledger must be searched for duplicate invoices.",
        required_actions=["search_ledger", "flag_duplicate_cluster_review"],
        severity="high",
        applies_to=["task_c", "task_d", "task_e"],
    ),
    SOXControl(
        control_id="SOX-AP-005",
        name="Approval Threshold Enforcement",
        description="Payments above threshold require additional approval.",
        required_actions=["lookup_policy"],
        severity="high",
        applies_to=["task_b", "task_c", "task_d", "task_e"],
    ),
    SOXControl(
        control_id="SOX-AP-006",
        name="Vendor Master Verification",
        description="Vendor identity must be verified against master data.",
        required_actions=["lookup_vendor", "lookup_vendor_history"],
        severity="medium",
        applies_to=["task_b", "task_c", "task_d", "task_e"],
    ),
    SOXControl(
        control_id="SOX-AP-007",
        name="Callback Verification",
        description="High-risk payments require callback to vendor.",
        required_actions=["request_callback_verification"],
        required_artifacts=["callback_verification_result"],
        severity="critical",
        applies_to=["task_d", "task_e"],
    ),
    SOXControl(
        control_id="SOX-AP-008",
        name="Audit Trail Completeness",
        description="All investigation steps must be documented in trajectory.",
        required_actions=[],  # Evaluated by trajectory length
        severity="medium",
        applies_to=["task_a", "task_b", "task_c", "task_d", "task_e"],
    ),
]


@dataclass
class ComplianceResult:
    """Result of a compliance evaluation.

    Attributes:
        overall_compliant: Whether all applicable controls passed.
        controls_evaluated: Number of controls checked.
        controls_passed: Number of controls that passed.
        controls_failed: Number of controls that failed.
        compliance_score: Score from 0.0 to 1.0.
        findings: List of individual control findings.
        critical_failures: Control IDs of critical failures.
        remediation_required: Whether remediation is needed.
    """
    overall_compliant: bool = True
    controls_evaluated: int = 0
    controls_passed: int = 0
    controls_failed: int = 0
    compliance_score: float = 1.0
    findings: list[dict[str, Any]] = field(default_factory=list)
    critical_failures: list[str] = field(default_factory=list)
    remediation_required: bool = False


def _normalized_gold_signals(gold: dict[str, Any]) -> set[str]:
    signals: set[str] = set()
    for key in ("reason_codes", "fraud_flags", "discrepancies", "campaign_signals"):
        for value in gold.get(key, []) or []:
            normalized = normalize_text(value)
            if normalized:
                signals.add(normalized)
    policy_checks = gold.get("policy_checks", {}) or {}
    for check_name, status in policy_checks.items():
        if normalize_text(status) == "fail":
            normalized = normalize_text(check_name)
            if normalized:
                signals.add(normalized)
    return signals


def _control_applies(
    control: SOXControl,
    *,
    task_type: str,
    gold: dict[str, Any],
    case_context: dict[str, Any] | None,
) -> bool:
    task_norm = normalize_text(task_type)
    if task_norm not in control.applies_to:
        return False

    instruction = normalize_text((case_context or {}).get("instruction", ""))
    gold_signals = _normalized_gold_signals(gold)
    policy_checks = {
        normalize_text(name): normalize_text(status)
        for name, status in (gold.get("policy_checks", {}) or {}).items()
    }

    if control.control_id == "SOX-AP-002":
        return (
            task_norm == "task_b"
            or "three_way_match" in policy_checks
            or "three way match" in instruction
            or "3-way match" in instruction
        )

    if control.control_id == "SOX-AP-003":
        return bool(
            {"bank_override_attempt", "bank_account_mismatch", "shared_bank_account"} & gold_signals
            or policy_checks.get("bank_change_verification") == "fail"
            or any(
                phrase in instruction
                for phrase in {
                    "bank update",
                    "bank account",
                    "bank change",
                    "remittance instructions",
                }
            )
        )

    if control.control_id == "SOX-AP-004":
        return bool(
            {
                "duplicate_near_match",
                "shared_bank_account",
                "coordinated_timing",
                "approval_threshold_evasion",
            }
            & gold_signals
            or policy_checks.get("duplicate_check") == "fail"
            or any(
                phrase in instruction
                for phrase in {
                    "duplicate",
                    "batch payment",
                    "coordinated fraud",
                    "similar amounts and timing",
                    "approval threshold",
                    "structured below",
                    "split invoice",
                }
            )
        )

    if control.control_id == "SOX-AP-005":
        return bool(
            task_norm == "task_b"
            or "approval_threshold_check" in policy_checks
            or "approval_threshold_evasion" in gold_signals
            or any(
                phrase in instruction
                for phrase in {
                    "approval threshold",
                    "threshold",
                    "structured below",
                    "split invoice",
                }
            )
        )

    if control.control_id == "SOX-AP-006":
        return task_norm in {"task_c", "task_d", "task_e"} or "vendor master" in instruction

    if control.control_id == "SOX-AP-007":
        return task_norm in {"task_d", "task_e"} and bool(gold.get("unsafe_if_pay"))

    return True


def evaluate_compliance(
    task_type: str,
    trajectory: list[dict[str, Any]],
    revealed_artifacts: list[str],
    decision: str,
    gold: dict[str, Any],
    case_context: dict[str, Any] | None = None,
) -> ComplianceResult:
    """Evaluate SOX compliance for an episode.

    Args:
        task_type: The task type (task_a through task_e).
        trajectory: List of trajectory step dicts.
        revealed_artifacts: List of revealed artifact IDs.
        decision: The agent's final decision.
        gold: Gold-standard answers.

    Returns:
        ComplianceResult with findings.
    """
    task_norm = normalize_text(task_type)
    decision_norm = normalize_text(decision)
    is_risky = bool(gold.get("unsafe_if_pay"))

    actions_taken = {
        normalize_text(step.get("action_type", ""))
        for step in (trajectory or [])
        if step.get("success", True)
    }
    artifacts_set = {normalize_text(a) for a in (revealed_artifacts or [])}

    result = ComplianceResult()
    applicable = [
        c
        for c in SOX_CONTROLS
        if _control_applies(c, task_type=task_type, gold=gold, case_context=case_context)
    ]
    result.controls_evaluated = len(applicable)

    for control in applicable:
        finding: dict[str, Any] = {
            "control_id": control.control_id,
            "name": control.name,
            "severity": control.severity,
            "status": "pass",
            "details": "",
        }

        # SOX-AP-008: Audit trail — check trajectory length
        if control.control_id == "SOX-AP-008":
            min_steps = {"task_a": 2, "task_b": 3, "task_c": 4,
                         "task_d": 5, "task_e": 6}.get(task_norm, 3)
            if len(trajectory or []) < min_steps:
                finding["status"] = "fail"
                finding["details"] = (
                    f"Insufficient investigation: {len(trajectory or [])} steps "
                    f"(minimum {min_steps} for {task_type})"
                )
        # SOX-AP-001: Segregation — only required for risky cases with PAY
        elif control.control_id == "SOX-AP-001":
            if is_risky and decision_norm == "pay":
                has_sod = bool(
                    actions_taken & {normalize_text(a) for a in control.required_actions}
                )
                if not has_sod:
                    finding["status"] = "fail"
                    finding["details"] = "No independent verification for high-risk payment"
            # Non-risky or non-PAY: auto-pass
        else:
            # Standard control evaluation
            req_actions = {normalize_text(a) for a in control.required_actions}
            req_artifacts = {normalize_text(a) for a in control.required_artifacts}

            # For non-risky cases paying, relax some controls
            if not is_risky and decision_norm == "pay":
                needs_any = bool(req_actions & actions_taken) or not req_actions
            else:
                missing_actions = req_actions - actions_taken
                missing_artifacts = req_artifacts - artifacts_set
                needs_any = not missing_actions and not missing_artifacts

                if not needs_any:
                    missing_items = []
                    if req_actions - actions_taken:
                        missing_items.append(
                            f"Missing actions: {sorted(req_actions - actions_taken)}"
                        )
                    if req_artifacts - artifacts_set:
                        missing_items.append(
                            f"Missing artifacts: {sorted(req_artifacts - artifacts_set)}"
                        )
                    finding["status"] = "fail"
                    finding["details"] = "; ".join(missing_items)

        if finding["status"] == "fail":
            result.controls_failed += 1
            if control.severity == "critical":
                result.critical_failures.append(control.control_id)
        else:
            result.controls_passed += 1

        result.findings.append(finding)

    if result.controls_evaluated > 0:
        result.compliance_score = round(
            result.controls_passed / result.controls_evaluated, 4
        )
    result.overall_compliant = result.controls_failed == 0
    result.remediation_required = len(result.critical_failures) > 0

    return result


def compliance_penalty(result: ComplianceResult) -> float:
    """Calculate a grading penalty from compliance results.

    Args:
        result: The ComplianceResult from evaluate_compliance().

    Returns:
        Negative penalty value (0.0 for full compliance).
    """
    if result.overall_compliant:
        return 0.0

    penalty = 0.0
    for finding in result.findings:
        if finding["status"] != "fail":
            continue
        severity = finding.get("severity", "medium")
        if severity == "critical":
            penalty -= 0.08
        elif severity == "high":
            penalty -= 0.04
        else:
            penalty -= 0.02

    return max(-0.30, penalty)
