from __future__ import annotations

from typing import Any

FIELD_KEYS = [
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "currency",
    "subtotal",
    "tax",
    "total",
    "po_id",
    "receipt_id",
    "bank_account",
]

INVESTIGATION_ACTIONS = [
    "zoom",
    "get_doc_crop",
    "ocr",
    "lookup_vendor",
    "lookup_vendor_history",
    "lookup_policy",
    "lookup_po",
    "lookup_receipt",
    "search_ledger",
    "inspect_email_thread",
    "compare_bank_account",
]

INTERVENTION_ACTIONS = [
    "request_callback_verification",
    "freeze_vendor_profile",
    "request_bank_change_approval_chain",
    "request_po_reconciliation",
    "request_additional_receipt_evidence",
    "route_to_procurement",
    "route_to_security",
    "flag_duplicate_cluster_review",
    "create_human_handoff",
]

FINAL_ACTIONS = ["submit_decision"]

ALLOWED_ACTIONS = INVESTIGATION_ACTIONS + INTERVENTION_ACTIONS + FINAL_ACTIONS
ALLOWED_DECISIONS = ["PAY", "HOLD", "NEEDS_REVIEW", "ESCALATE_FRAUD"]

DISCREPANCY_TYPES = [
    "price_mismatch",
    "quantity_mismatch",
    "missing_receipt",
    "duplicate_po_reference",
    "invalid_invoice_date",
    "total_mismatch",
    "tax_id_mismatch",
    "partial_receipt_only",
    "missing_po",
    "receipt_date_mismatch",
    "bank_account_mismatch",
    "vendor_master_mismatch",
]

FRAUD_TYPES = [
    "bank_override_attempt",
    "vendor_name_spoof",
    "sender_domain_spoof",
    "duplicate_near_match",
    "approval_threshold_evasion",
    "urgent_payment_pressure",
    "callback_verification_failed",
    "vendor_account_takeover_suspected",
    "policy_bypass_attempt",
]

POLICY_CHECK_KEYS = [
    "three_way_match",
    "bank_change_verification",
    "duplicate_check",
    "approval_threshold_check",
    "human_review_required",
    "callback_required",
]

OUTCOME_TYPES = [
    "safe_payment_cleared",
    "unsafe_payment_released",
    "fraud_prevented",
    "manual_review_created",
    "false_positive_operational_delay",
    "policy_breach",
]

ALL_REASON_CODES = sorted(set(DISCREPANCY_TYPES + FRAUD_TYPES))


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def normalize_id(value: Any) -> str:
    text = normalize_text(value)
    return "".join(ch for ch in text if ch.isalnum())


def safe_float(value: Any) -> float:
    try:
        if isinstance(value, str):
            cleaned = (
                value.replace(",", "")
                .replace("₹", "")
                .replace("$", "")
                .replace("€", "")
                .strip()
            )
            return float(cleaned)
        return float(value)
    except Exception:
        return 0.0


def numeric_match(a: Any, b: Any, tolerance: float = 0.01) -> bool:
    return abs(safe_float(a) - safe_float(b)) <= tolerance


def fuzzy_numeric_similarity(a: Any, b: Any) -> float:
    a_num = safe_float(a)
    b_num = safe_float(b)
    denom = max(abs(a_num), abs(b_num), 1.0)
    diff = abs(a_num - b_num) / denom
    return max(0.0, 1.0 - diff)


def prefix_domain(value: Any) -> str:
    text = normalize_text(value)
    if "@" in text:
        return text.split("@", 1)[-1]
    return text


def bbox_iou(box_a: list[float] | None, box_b: list[float] | None) -> float:
    if not box_a or not box_b or len(box_a) != 4 or len(box_b) != 4:
        return 0.0
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    denom = area_a + area_b - inter_area
    if denom <= 0:
        return 0.0
    return inter_area / denom


def token_overlap(pred_token_ids: list[str] | None, gold_token_ids: list[str] | None) -> float:
    pred = set(pred_token_ids or [])
    gold = set(gold_token_ids or [])
    if not pred or not gold:
        return 0.0
    return len(pred & gold) / len(gold)


def list_unique_normalized(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        norm = normalize_text(value)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        output.append(norm)
    return output


def canonical_reason_codes(values: list[Any]) -> list[str]:
    normalized = list_unique_normalized(values)
    allowed = {normalize_text(x) for x in ALL_REASON_CODES}
    return [value for value in normalized if value in allowed]


def is_intervention_action(action_type: str) -> bool:
    return normalize_text(action_type) in {normalize_text(x) for x in INTERVENTION_ACTIONS}


def is_investigation_action(action_type: str) -> bool:
    return normalize_text(action_type) in {normalize_text(x) for x in INVESTIGATION_ACTIONS}