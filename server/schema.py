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

DISCREPANCY_TYPES = [
    "price_mismatch",
    "quantity_mismatch",
    "missing_receipt",
    "duplicate_po_reference",
    "invalid_invoice_date",
    "total_mismatch",
    "tax_id_mismatch",
    "partial_receipt_only",
]

FRAUD_TYPES = [
    "bank_override_attempt",
    "vendor_name_spoof",
    "sender_domain_spoof",
    "duplicate_near_match",
    "approval_threshold_evasion",
]

POLICY_CHECK_KEYS = [
    "three_way_match",
    "bank_change_verification",
    "duplicate_check",
    "approval_threshold_check",
]

ALL_REASON_CODES = sorted(set(DISCREPANCY_TYPES + FRAUD_TYPES))


def normalize_text(value: Any) -> str:
    return " ".join(str(value).strip().lower().split())


def normalize_id(value: Any) -> str:
    text = normalize_text(value)
    return "".join(ch for ch in text if ch.isalnum())


def safe_float(value: Any) -> float:
    try:
        if isinstance(value, str):
            cleaned = value.replace(",", "").replace("₹", "").replace("$", "").strip()
            return float(cleaned)
        return float(value)
    except Exception:
        return 0.0


def numeric_match(a: Any, b: Any, tolerance: float = 0.01) -> bool:
    return abs(safe_float(a) - safe_float(b)) <= tolerance


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
