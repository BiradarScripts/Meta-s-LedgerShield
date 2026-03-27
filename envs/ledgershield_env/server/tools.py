from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from .schema import normalize_id, normalize_text, safe_float


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def _filter_tokens_for_bbox(tokens: list[dict[str, Any]], bbox: list[float] | None) -> list[dict[str, Any]]:
    if not bbox:
        return tokens
    x1, y1, x2, y2 = bbox
    selected: list[dict[str, Any]] = []
    for token in tokens:
        tb = token.get("bbox")
        if not tb or len(tb) != 4:
            continue
        tx1, ty1, tx2, ty2 = tb
        intersects = not (tx2 < x1 or tx1 > x2 or ty2 < y1 or ty1 > y2)
        if intersects:
            selected.append(token)
    return selected


def _get_doc(case: dict[str, Any], doc_id: str) -> dict[str, Any] | None:
    for doc in case.get("documents", []):
        if doc.get("doc_id") == doc_id:
            return doc
    return None


def zoom_tool(case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    doc_id = payload.get("doc_id")
    bbox = payload.get("bbox", [0, 0, 9999, 9999])
    doc = _get_doc(case, doc_id)
    if not doc:
        return {"error": f"unknown doc_id: {doc_id}"}
    tokens = _filter_tokens_for_bbox(doc.get("accurate_ocr", []), bbox)[:20]
    return {
        "doc_id": doc_id,
        "bbox": bbox,
        "crop_ref": f"crop::{doc_id}::{bbox}",
        "tokens": tokens,
        "visual_tokens": doc.get("visual_tokens", []),
    }


def ocr_tool(case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    doc_id = payload.get("doc_id")
    mode = payload.get("mode", "fast")
    bbox = payload.get("bbox")
    doc = _get_doc(case, doc_id)
    if not doc:
        return {"error": f"unknown doc_id: {doc_id}"}
    source_tokens = doc.get("accurate_ocr", []) if mode == "accurate" else doc.get("noisy_ocr", [])
    tokens = _filter_tokens_for_bbox(source_tokens, bbox)
    return {"doc_id": doc_id, "mode": mode, "tokens": tokens}


def lookup_vendor_tool(vendors: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    key = normalize_text(payload.get("vendor_key") or payload.get("canonical_name") or "")
    for vendor in vendors:
        if normalize_text(vendor.get("vendor_key")) == key or normalize_text(vendor.get("canonical_name")) == key:
            return vendor
    return {"error": f"vendor not found: {key}"}


def lookup_vendor_history_tool(vendor_history: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    vendor_key = normalize_text(payload.get("vendor_key", ""))
    rows = [row for row in vendor_history if normalize_text(row.get("vendor_key")) == vendor_key]
    return {"vendor_key": vendor_key, "history": rows}


def lookup_policy_tool(policy_rules: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    rule_id = normalize_text(payload.get("rule_id", ""))
    if not rule_id:
        return {"rules": policy_rules}
    for rule in policy_rules:
        if normalize_text(rule.get("rule_id")) == rule_id:
            return rule
    return {"error": f"policy not found: {rule_id}"}


def lookup_po_tool(po_records: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    po_id = normalize_text(payload.get("po_id", ""))
    for record in po_records:
        if normalize_text(record.get("po_id")) == po_id:
            return record
    return {"error": f"po not found: {po_id}"}


def lookup_receipt_tool(receipts: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    receipt_id = normalize_text(payload.get("receipt_id", ""))
    for record in receipts:
        if normalize_text(record.get("receipt_id")) == receipt_id:
            return record
    return {"error": f"receipt not found: {receipt_id}"}


def search_ledger_tool(ledger_index: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("similarity_query", "")).strip()
    target_amount = payload.get("amount")
    scored: list[dict[str, Any]] = []
    for row in ledger_index:
        lexical = max(
            _similarity(query, row.get("invoice_number", "")),
            _similarity(query, row.get("vendor_name", "")),
            _similarity(query, row.get("fingerprint", "")),
        )
        score = lexical
        if target_amount is not None:
            amount_gap = abs(safe_float(target_amount) - safe_float(row.get("amount")))
            score += max(0.0, 1.0 - min(amount_gap / max(safe_float(target_amount), 1.0), 1.0)) * 0.25
        scored.append({**row, "score": round(score, 4)})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return {"matches": scored[:5]}


def inspect_email_thread_tool(email_threads: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    thread_id = normalize_text(payload.get("thread_id", ""))
    vendor_key = normalize_text(payload.get("vendor_key", ""))
    for thread in email_threads:
        if thread_id and normalize_text(thread.get("thread_id")) == thread_id:
            return thread
    if vendor_key:
        matches = [row for row in email_threads if normalize_text(row.get("vendor_key")) == vendor_key]
        return {"vendor_key": vendor_key, "threads": matches}
    return {"threads": email_threads}


def compare_bank_account_tool(vendors: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    vendor_key = normalize_text(payload.get("vendor_key", ""))
    candidate_account = normalize_id(payload.get("candidate_account", ""))
    for vendor in vendors:
        if normalize_text(vendor.get("vendor_key")) != vendor_key:
            continue
        approved = [normalize_id(x) for x in vendor.get("allowed_bank_accounts", [])]
        return {
            "vendor_key": vendor_key,
            "candidate_account": candidate_account,
            "approved_accounts": approved,
            "match": candidate_account in approved,
        }
    return {"error": f"vendor not found: {vendor_key}"}
