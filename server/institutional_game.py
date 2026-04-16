from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any

from .schema import normalize_text


@dataclass
class VendorInstitutionalMemory:
    vendor_id: str
    cases_seen: int = 0
    unsafe_releases: int = 0
    fraud_prevented: int = 0
    clean_releases: int = 0
    manual_reviews: int = 0
    callback_failures: int = 0
    last_decision: str = ""
    trust_score: float = 0.70

    def update_trust(self) -> None:
        risk_events = self.unsafe_releases + self.callback_failures
        positive_events = self.clean_releases + self.fraud_prevented
        raw = 0.70 + 0.04 * positive_events - 0.16 * risk_events - 0.03 * self.manual_reviews
        self.trust_score = round(max(0.05, min(0.98, raw)), 4)


@dataclass
class InstitutionalLossLedger:
    fraud_loss_prevented: float = 0.0
    fraud_loss_released: float = 0.0
    operational_delay_hours: float = 0.0
    manual_review_minutes: float = 0.0
    supplier_friction: float = 0.0
    compliance_breaches: int = 0
    unsafe_release_count: int = 0
    false_positive_count: int = 0
    safe_release_count: int = 0

    def loss_score(self) -> float:
        fraud_denominator = max(self.fraud_loss_prevented + self.fraud_loss_released, 1.0)
        fraud_loss_ratio = min(1.0, self.fraud_loss_released / fraud_denominator)
        delay_ratio = min(1.0, self.operational_delay_hours / 80.0)
        review_ratio = min(1.0, self.manual_review_minutes / 480.0)
        friction_ratio = min(1.0, self.supplier_friction / 8.0)
        breach_ratio = min(1.0, self.compliance_breaches / 6.0)
        raw_loss = (
            0.50 * fraud_loss_ratio
            + 0.18 * delay_ratio
            + 0.14 * review_ratio
            + 0.10 * friction_ratio
            + 0.08 * breach_ratio
        )
        return round(max(0.0, min(1.0, 1.0 - raw_loss)), 4)


@dataclass
class InstitutionalMemory:
    week_id: str = "AP-WEEK-2026-04"
    case_counter: int = 0
    queue_depth: int = 0
    manual_review_capacity_total: int = 6
    manual_review_capacity_remaining: int = 6
    callback_capacity_total: int = 5
    callback_capacity_remaining: int = 5
    vendor_memory: dict[str, VendorInstitutionalMemory] = field(default_factory=dict)
    loss_ledger: InstitutionalLossLedger = field(default_factory=InstitutionalLossLedger)
    attacker_belief: dict[str, float] = field(default_factory=lambda: {
        "callback_gap": 0.10,
        "queue_pressure_exploit": 0.10,
        "duplicate_control_gap": 0.10,
        "payment_release_weakness": 0.10,
    })
    amendment_log: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_cases(cls, cases: list[dict[str, Any]] | None = None) -> "InstitutionalMemory":
        memory = cls(queue_depth=len(cases or []))
        return memory


def _case_vendor_id(case: dict[str, Any]) -> str:
    gold = case.get("gold", {}) or {}
    fields = gold.get("fields", {}) or gold.get("extracted_fields", {}) or {}
    candidate = (
        case.get("vendor_key")
        or fields.get("vendor_key")
        or fields.get("vendor_name")
        or case.get("case_id")
        or "unknown_vendor"
    )
    return normalize_text(candidate) or "unknown_vendor"


def _case_bank_account(case: dict[str, Any]) -> str:
    gold = case.get("gold", {}) or {}
    fields = gold.get("fields", {}) or gold.get("extracted_fields", {}) or {}
    return normalize_text(fields.get("bank_account"))


def _invoice_total(case: dict[str, Any]) -> float:
    gold = case.get("gold", {}) or {}
    fields = gold.get("fields", {}) or gold.get("extracted_fields", {}) or {}
    try:
        return float(fields.get("total", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _linked_case_ids(case: dict[str, Any]) -> list[str]:
    gold = case.get("gold", {}) or {}
    links = list(gold.get("duplicate_links", []) or [])
    links.extend(gold.get("cross_invoice_links", []) or [])
    for item in case.get("campaign_context", {}).get("linked_case_ids", []) or []:
        links.append(item)
    return sorted({str(item) for item in links if str(item)})


def public_institutional_memory(memory: InstitutionalMemory) -> dict[str, Any]:
    vendor_scores = {
        vendor_id: {
            "cases_seen": vendor.cases_seen,
            "trust_score": vendor.trust_score,
            "unsafe_releases": vendor.unsafe_releases,
            "fraud_prevented": vendor.fraud_prevented,
            "manual_reviews": vendor.manual_reviews,
            "callback_failures": vendor.callback_failures,
            "last_decision": vendor.last_decision,
        }
        for vendor_id, vendor in sorted(memory.vendor_memory.items())
    }
    ledger = asdict(memory.loss_ledger)
    ledger["institutional_loss_score"] = memory.loss_ledger.loss_score()
    return {
        "week_id": memory.week_id,
        "case_counter": memory.case_counter,
        "queue_depth": memory.queue_depth,
        "manual_review_capacity_remaining": memory.manual_review_capacity_remaining,
        "callback_capacity_remaining": memory.callback_capacity_remaining,
        "attacker_belief": {key: round(float(value), 4) for key, value in sorted(memory.attacker_belief.items())},
        "vendor_memory": vendor_scores,
        "loss_ledger": ledger,
        "amendment_count": len(memory.amendment_log),
    }


def institutional_context_for_case(
    case: dict[str, Any],
    all_cases: list[dict[str, Any]],
    memory: InstitutionalMemory,
) -> dict[str, Any]:
    vendor_id = _case_vendor_id(case)
    bank_account = _case_bank_account(case)
    linked_case_ids = _linked_case_ids(case)
    bank_shared_count = 0
    if bank_account:
        bank_shared_count = sum(1 for candidate in all_cases if _case_bank_account(candidate) == bank_account)

    vendor_memory = memory.vendor_memory.get(vendor_id, VendorInstitutionalMemory(vendor_id=vendor_id))
    queue_pressure = "normal"
    if len(linked_case_ids) >= 2 or bank_shared_count >= 3:
        queue_pressure = "campaign"
    elif memory.queue_depth >= 12 or memory.manual_review_capacity_remaining <= 1:
        queue_pressure = "elevated"
    if memory.loss_ledger.unsafe_release_count:
        queue_pressure = "adversarial"

    attacker_pressure = max(memory.attacker_belief.values()) if memory.attacker_belief else 0.0
    return {
        "week_id": memory.week_id,
        "case_sequence_index": memory.case_counter + 1,
        "queue_depth": max(memory.queue_depth, 0),
        "vendor_id": vendor_id,
        "vendor_trust_score": vendor_memory.trust_score,
        "vendor_cases_seen": vendor_memory.cases_seen,
        "manual_review_capacity_remaining": memory.manual_review_capacity_remaining,
        "callback_capacity_remaining": memory.callback_capacity_remaining,
        "shared_bank_account_count": bank_shared_count,
        "linked_case_ids": linked_case_ids,
        "queue_pressure": queue_pressure,
        "attacker_pressure": round(attacker_pressure, 4),
        "current_invoice_total": round(_invoice_total(case), 2),
        "institutional_loss_score_so_far": memory.loss_ledger.loss_score(),
    }


def attach_institutional_context(hidden_world: dict[str, Any], context: dict[str, Any]) -> None:
    hidden_world["institutional_context"] = deepcopy(context)
    campaign_context = hidden_world.setdefault("campaign_context", {})
    campaign_context.setdefault("week_id", context.get("week_id"))
    campaign_context.setdefault("queue_depth", context.get("queue_depth", 0))
    campaign_context.setdefault("vendor_trust_score", context.get("vendor_trust_score", 0.7))
    campaign_context.setdefault("case_sequence_index", context.get("case_sequence_index", 1))
    campaign_context["manual_review_capacity"] = context.get("manual_review_capacity_remaining", 0)
    campaign_context["callback_capacity"] = context.get("callback_capacity_remaining", 0)
    campaign_context["institutional_loss_score_so_far"] = context.get("institutional_loss_score_so_far", 1.0)
    if str(campaign_context.get("queue_pressure", "normal")) == "normal":
        campaign_context["queue_pressure"] = context.get("queue_pressure", "normal")
    if int(context.get("shared_bank_account_count", 0) or 0) > 1:
        campaign_context.setdefault("shared_bank_account_count", context["shared_bank_account_count"])


def record_institutional_outcome(
    memory: InstitutionalMemory,
    *,
    case: dict[str, Any],
    submitted: dict[str, Any],
    outcome: dict[str, Any],
    trajectory: list[dict[str, Any]],
    compliance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    vendor_id = _case_vendor_id(case)
    vendor = memory.vendor_memory.setdefault(vendor_id, VendorInstitutionalMemory(vendor_id=vendor_id))
    decision = normalize_text(submitted.get("decision"))
    outcome_type = normalize_text(outcome.get("outcome_type"))
    metrics = outcome.get("portfolio_metrics", {}) or {}
    compliance = compliance or {}

    memory.case_counter += 1
    memory.queue_depth = max(0, memory.queue_depth - 1)

    vendor.cases_seen += 1
    vendor.last_decision = decision.upper()
    if outcome.get("unsafe_payment"):
        vendor.unsafe_releases += 1
        memory.loss_ledger.unsafe_release_count += 1
        memory.attacker_belief["payment_release_weakness"] = min(
            1.0, memory.attacker_belief.get("payment_release_weakness", 0.1) + 0.22
        )
    if outcome_type == "fraud_prevented":
        vendor.fraud_prevented += 1
    if outcome_type == "safe_payment_cleared":
        vendor.clean_releases += 1
        memory.loss_ledger.safe_release_count += 1
    if outcome_type == "false_positive_operational_delay":
        memory.loss_ledger.false_positive_count += 1
    if decision in {"hold", "needs_review", "escalate_fraud"}:
        vendor.manual_reviews += 1
        memory.manual_review_capacity_remaining = max(0, memory.manual_review_capacity_remaining - 1)

    actions = {normalize_text(step.get("action_type")) for step in trajectory}
    if "request_callback_verification" in actions:
        memory.callback_capacity_remaining = max(0, memory.callback_capacity_remaining - 1)
    elif case.get("gold", {}).get("unsafe_if_pay"):
        memory.attacker_belief["callback_gap"] = min(1.0, memory.attacker_belief.get("callback_gap", 0.1) + 0.08)

    if "flag_duplicate_cluster_review" not in actions and case.get("gold", {}).get("duplicate_links"):
        memory.attacker_belief["duplicate_control_gap"] = min(
            1.0, memory.attacker_belief.get("duplicate_control_gap", 0.1) + 0.10
        )
    if memory.manual_review_capacity_remaining <= 1:
        memory.attacker_belief["queue_pressure_exploit"] = min(
            1.0, memory.attacker_belief.get("queue_pressure_exploit", 0.1) + 0.08
        )

    memory.loss_ledger.fraud_loss_prevented += float(metrics.get("fraud_loss_prevented", 0.0) or 0.0)
    memory.loss_ledger.fraud_loss_released += float(metrics.get("fraud_loss_released", 0.0) or 0.0)
    memory.loss_ledger.operational_delay_hours += float(metrics.get("operational_delay_hours", 0.0) or 0.0)
    memory.loss_ledger.manual_review_minutes += float(metrics.get("manual_review_minutes", 0.0) or 0.0)
    memory.loss_ledger.supplier_friction += float(metrics.get("supplier_friction", 0.0) or 0.0)
    failed_controls = compliance.get("failed_controls", []) or compliance.get("critical_failures", []) or []
    memory.loss_ledger.compliance_breaches += len(failed_controls)
    vendor.callback_failures += sum(
        1
        for artifact in outcome.get("revealed_artifacts", []) or []
        if normalize_text(artifact.get("artifact_id")) == "callback_verification_result"
        and normalize_text(artifact.get("details", {}).get("status")) == "failed"
    )
    vendor.update_trust()

    amendment = {
        "case_id": case.get("case_id"),
        "decision": decision.upper(),
        "outcome_type": outcome.get("outcome_type"),
        "unsafe_payment": bool(outcome.get("unsafe_payment")),
        "institutional_loss_score": memory.loss_ledger.loss_score(),
    }
    memory.amendment_log.append(amendment)
    return {
        "case_update": amendment,
        "institutional_memory": public_institutional_memory(memory),
    }
