from __future__ import annotations

from copy import deepcopy
from typing import Any

from .schema import bbox_iou, fuzzy_numeric_similarity, normalize_id, normalize_text, prefix_domain, safe_float


def _find_doc(case: dict[str, Any], doc_id: str) -> dict[str, Any] | None:
    for doc in case.get("documents", []):
        if doc.get("doc_id") == doc_id:
            return doc
    return None


def _page_number(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _scoped_tokens(
    doc: dict[str, Any],
    *,
    mode: str = "accurate",
    page: int | None = None,
    bbox: list[float] | None = None,
) -> list[dict[str, Any]]:
    token_key = "accurate_ocr" if mode == "accurate" else "noisy_ocr"
    tokens = deepcopy(doc.get(token_key, []))
    if page is None and not bbox:
        return tokens

    selected: list[dict[str, Any]] = []
    for token in tokens:
        token_page = _page_number(token.get("page")) or 1
        if page is not None and token_page != page:
            continue
        if bbox and bbox_iou(token.get("bbox"), bbox) <= 0.0:
            continue
        selected.append(token)

    return selected


def _token_text_preview(tokens: list[dict[str, Any]], limit: int = 6) -> list[str]:
    preview: list[str] = []
    for token in tokens[:limit]:
        text = str(token.get("text", "")).strip()
        if text:
            preview.append(text)
    return preview


def zoom_tool(case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    doc_id = payload.get("doc_id")
    page = _page_number(payload.get("page")) or 1
    bbox = payload.get("bbox", [0, 0, 100, 100])
    doc = _find_doc(case, doc_id)
    if doc is None:
        return {"error": f"unknown doc_id: {doc_id}"}

    focus_tokens = _scoped_tokens(doc, page=page, bbox=bbox)
    return {
        "doc_id": doc_id,
        "page": page,
        "bbox": bbox,
        "crop_hint": f"zoomed view for {doc_id}",
        "visual_tokens": deepcopy(doc.get("visual_tokens", []))[:20],
        "focus_text": _token_text_preview(focus_tokens),
        "region_token_count": len(focus_tokens),
        "message": "Zoom completed.",
    }


def get_doc_crop_tool(case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    doc_id = payload.get("doc_id")
    page = int(payload.get("page", 1) or 1)
    bbox = payload.get("bbox", [0, 0, 100, 100])
    doc = _find_doc(case, doc_id)
    if doc is None:
        return {"error": f"unknown doc_id: {doc_id}"}

    focus_tokens = _scoped_tokens(doc, page=page, bbox=bbox)
    return {
        "doc_id": doc_id,
        "page": page,
        "bbox": bbox,
        "crop_text_hint": _token_text_preview(focus_tokens, limit=8) or deepcopy(doc.get("crop_text_hint", []))[:10],
        "region_token_count": len(focus_tokens),
        "message": "Document crop returned.",
    }


def ocr_tool(case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    doc_id = payload.get("doc_id")
    mode = payload.get("mode", "fast")
    page = _page_number(payload.get("page"))
    bbox = payload.get("bbox")
    doc = _find_doc(case, doc_id)
    if doc is None:
        return {"error": f"unknown doc_id: {doc_id}"}

    tokens = _scoped_tokens(doc, mode=mode, page=page, bbox=bbox)
    scope = "region" if bbox else ("page" if page is not None else "document")
    text = " ".join(str(token.get("text", token)) for token in tokens[:200])

    return {
        "doc_id": doc_id,
        "mode": mode,
        "scope": scope,
        "page": page,
        "bbox": bbox,
        "tokens": tokens,
        "text_preview": text[:600],
        "message": f"Returned {mode} OCR.",
    }


def lookup_vendor_tool(vendors_by_key: dict[str, dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    vendor_key = normalize_text(payload.get("vendor_key"))
    vendor = vendors_by_key.get(vendor_key)
    if vendor is None:
        return {"error": f"vendor not found: {payload.get('vendor_key')}"}

    return {
        "vendor": deepcopy(vendor),
        "message": "Vendor lookup complete.",
    }


def lookup_vendor_history_tool(vendor_history: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    vendor_key = normalize_text(payload.get("vendor_key"))
    history = [
        deepcopy(row)
        for row in vendor_history
        if normalize_text(row.get("vendor_key")) == vendor_key
    ]
    risk_flags: list[str] = []
    for row in history:
        event_type = normalize_text(row.get("event_type") or row.get("change_type"))
        status = normalize_text(row.get("status"))
        if "bank" in event_type and status in {"rejected", "failed", "denied"}:
            risk_flags.append("historical_bank_change_rejected")
        if "fraud" in event_type:
            risk_flags.append("historical_fraud_event")

    return {
        "vendor_key": payload.get("vendor_key"),
        "history": history,
        "derived_flags": sorted(set(risk_flags)),
        "message": "Vendor history returned.",
    }


def lookup_policy_tool(policy_by_id: dict[str, dict[str, Any]], all_policies: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    rule_id = payload.get("rule_id")
    if rule_id:
        policy = policy_by_id.get(str(rule_id))
        if policy is None:
            return {"error": f"policy not found: {rule_id}"}
        return {
            "policy": deepcopy(policy),
            "message": "Policy lookup complete.",
        }

    return {
        "policies": deepcopy(all_policies),
        "message": "All policy rules returned.",
    }


def lookup_po_tool(po_by_id: dict[str, dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    po_id = payload.get("po_id")
    record = po_by_id.get(str(po_id))
    if record is None:
        return {"error": f"po not found: {po_id}"}
    return {
        "po": deepcopy(record),
        "message": "PO lookup complete.",
    }


def lookup_receipt_tool(receipt_by_id: dict[str, dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    receipt_id = payload.get("receipt_id")
    record = receipt_by_id.get(str(receipt_id))
    if record is None:
        return {"error": f"receipt not found: {receipt_id}"}
    return {
        "receipt": deepcopy(record),
        "message": "Receipt lookup complete.",
    }


def search_ledger_tool(ledger_index: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    vendor_key = normalize_text(payload.get("vendor_key"))
    invoice_number = payload.get("invoice_number")
    amount = payload.get("amount")

    query_invoice_id = normalize_id(invoice_number)
    query_amount = safe_float(amount) if amount is not None else None

    hits: list[dict[str, Any]] = []

    for row in ledger_index:
        row_vendor = normalize_text(row.get("vendor_key"))
        row_invoice = normalize_id(row.get("invoice_number"))
        row_amount = safe_float(row.get("amount"))
        score = 0.0
        invoice_signal = 0.0
        amount_signal = 0.0

        if vendor_key:
            if row_vendor == vendor_key:
                score += 0.20
            else:
                continue

        if query_invoice_id:
            if row_invoice == query_invoice_id:
                invoice_signal = 0.55
            elif row_invoice and (row_invoice in query_invoice_id or query_invoice_id in row_invoice):
                invoice_signal = 0.30

        if query_amount is not None:
            amount_similarity = fuzzy_numeric_similarity(row_amount, query_amount)
            if amount_similarity >= 0.98:
                amount_signal = 0.25
            elif amount_similarity >= 0.92:
                amount_signal = 0.18
            elif amount_similarity >= 0.80:
                amount_signal = 0.10

        # Vendor match alone should never be enough to create a duplicate hit.
        if invoice_signal == 0.0 and amount_signal == 0.0:
            continue

        score += invoice_signal + amount_signal

        if score >= 0.45:
            enriched = deepcopy(row)
            enriched["match_score"] = round(score, 4)
            hits.append(enriched)

    hits.sort(key=lambda item: item.get("match_score", 0.0), reverse=True)

    exact_count = sum(1 for row in hits if row.get("match_score", 0.0) >= 0.8)
    near_duplicate_count = sum(1 for row in hits if 0.45 <= row.get("match_score", 0.0) < 0.8)

    return {
        "hits": hits[:10],
        "count": len(hits),
        "exact_duplicate_count": exact_count,
        "near_duplicate_count": near_duplicate_count,
        "message": "Ledger search complete.",
    }


def inspect_email_thread_tool(case: dict[str, Any], email_threads: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    thread_id = payload.get("thread_id")
    for doc in case.get("documents", []):
        if doc.get("doc_id") == thread_id and isinstance(doc.get("thread_data"), dict):
            row = doc.get("thread_data") or {}
            break
    else:
        row = None

    if row is None:
        for candidate in email_threads:
            if candidate.get("thread_id") == thread_id:
                row = candidate
                break

    if row is None:
        return {"error": f"thread not found: {thread_id}"}

    subject = normalize_text(row.get("subject"))
    body = normalize_text(row.get("body") or " ".join(row.get("messages", [])))
    sender = normalize_text(row.get("sender"))
    from_domain = prefix_domain(sender)
    expected_domain = prefix_domain(row.get("expected_domain") or row.get("vendor_domain"))

    urgency_language = "urgent" in subject or "urgent" in body or "asap" in body
    domain_alignment = "mismatch" if expected_domain and from_domain and expected_domain != from_domain else "aligned"

    explicit_no_change = any(
        phrase in body
        for phrase in {
            "no bank change",
            "no bank changes",
            "no change to bank",
            "approved remittance instructions already on file",
        }
    )
    bank_change_language = (
        "bank" in body and ("change" in body or "update" in body or "override" in body) and not explicit_no_change
    )

    bypass_phrases = {
        "skip callback",
        "do not call",
        "don't call",
        "ignore standard workflow",
        "override policy",
        "bypass policy",
        "do not verify",
        "treat this email as the source of truth",
        "portal is offline",
        "avoid reapproval",
    }
    callback_discouraged = any(phrase in body for phrase in {"skip callback", "do not call", "don't call", "do not verify"})
    policy_override_language = any(phrase in body for phrase in bypass_phrases)
    quoted_directives: list[str] = []
    if bank_change_language:
        quoted_directives.append("bank or remittance instructions changed in email body")
    if callback_discouraged:
        quoted_directives.append("email discourages callback verification")
    if policy_override_language:
        quoted_directives.append("email pressures agent to override standard workflow")
    if urgency_language:
        quoted_directives.append("message uses urgency language")

    thread = {
        "thread_id": row.get("thread_id"),
        "vendor_key": row.get("vendor_key"),
        "sender": row.get("sender") or row.get("from"),
        "subject": row.get("subject", ""),
        "body": row.get("body", ""),
        "message_count": max(1, len(row.get("messages", []) or [])),
        "sender_profile": {
            "from_domain": from_domain,
            "expected_domain": expected_domain,
            "domain_alignment": domain_alignment,
        },
        "request_signals": {
            "bank_change_language": bank_change_language,
            "urgency_language": urgency_language,
            "callback_discouraged": callback_discouraged,
            "policy_override_language": policy_override_language,
        },
        "quoted_directives": quoted_directives,
    }
    return {
        "thread": thread,
        "message": "Email thread inspection complete.",
    }


def compare_bank_account_tool(vendors_by_key: dict[str, dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    vendor_key = normalize_text(payload.get("vendor_key"))
    proposed_bank_account = payload.get("proposed_bank_account")
    vendor = vendors_by_key.get(vendor_key)

    if vendor is None:
        return {"error": f"vendor not found: {payload.get('vendor_key')}"}

    approved_bank_account = (
        vendor.get("bank_account")
        or vendor.get("approved_bank_account")
        or (
            vendor.get("allowed_bank_accounts", [None])[0]
            if vendor.get("allowed_bank_accounts")
            else None
        )
    )

    matched = approved_bank_account == proposed_bank_account
    return {
        "vendor_key": vendor.get("vendor_key"),
        "approved_bank_account": approved_bank_account,
        "proposed_bank_account": proposed_bank_account,
        "matched": matched,
        "comparison_summary": "matched_master_data" if matched else "mismatch_to_master_data",
        "message": "Compared proposed bank account to approved master data.",
    }
