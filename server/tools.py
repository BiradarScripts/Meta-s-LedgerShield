from __future__ import annotations

from copy import deepcopy
from typing import Any

from .schema import fuzzy_numeric_similarity, normalize_id, normalize_text, prefix_domain, safe_float


def _find_doc(case: dict[str, Any], doc_id: str) -> dict[str, Any] | None:
    for doc in case.get("documents", []):
        if doc.get("doc_id") == doc_id:
            return doc
    return None


def zoom_tool(case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    doc_id = payload.get("doc_id")
    bbox = payload.get("bbox", [0, 0, 100, 100])
    doc = _find_doc(case, doc_id)
    if doc is None:
        return {"error": f"unknown doc_id: {doc_id}"}

    return {
        "doc_id": doc_id,
        "bbox": bbox,
        "crop_hint": f"zoomed view for {doc_id}",
        "visual_tokens": deepcopy(doc.get("visual_tokens", []))[:20],
        "message": "Zoom completed.",
    }


def get_doc_crop_tool(case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    doc_id = payload.get("doc_id")
    page = int(payload.get("page", 1) or 1)
    bbox = payload.get("bbox", [0, 0, 100, 100])
    doc = _find_doc(case, doc_id)
    if doc is None:
        return {"error": f"unknown doc_id: {doc_id}"}

    return {
        "doc_id": doc_id,
        "page": page,
        "bbox": bbox,
        "crop_text_hint": deepcopy(doc.get("crop_text_hint", []))[:10],
        "message": "Document crop returned.",
    }


def ocr_tool(case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    doc_id = payload.get("doc_id")
    mode = payload.get("mode", "fast")
    doc = _find_doc(case, doc_id)
    if doc is None:
        return {"error": f"unknown doc_id: {doc_id}"}

    tokens = deepcopy(doc.get("accurate_ocr", [])) if mode == "accurate" else deepcopy(doc.get("noisy_ocr", []))
    text = " ".join(str(token.get("text", token)) for token in tokens[:200])

    return {
        "doc_id": doc_id,
        "mode": mode,
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
        score = 0.0
        row_vendor = normalize_text(row.get("vendor_key"))
        row_invoice = normalize_id(row.get("invoice_number"))
        row_amount = safe_float(row.get("amount"))

        if vendor_key:
            if row_vendor == vendor_key:
                score += 0.45
            else:
                continue

        if query_invoice_id:
            if row_invoice == query_invoice_id:
                score += 0.40
            elif row_invoice and (row_invoice in query_invoice_id or query_invoice_id in row_invoice):
                score += 0.22

        if query_amount is not None:
            score += 0.15 * fuzzy_numeric_similarity(row_amount, query_amount)

        if score >= 0.25:
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


def inspect_email_thread_tool(email_threads: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    thread_id = payload.get("thread_id")
    for row in email_threads:
        if row.get("thread_id") != thread_id:
            continue

        thread = deepcopy(row)
        signals: list[str] = list(thread.get("flags", []) or thread.get("fraud_signals", []) or [])

        subject = normalize_text(thread.get("subject"))
        body = normalize_text(thread.get("body") or " ".join(thread.get("messages", [])))
        sender = normalize_text(thread.get("sender"))
        from_domain = prefix_domain(sender)
        expected_domain = prefix_domain(thread.get("expected_domain") or thread.get("vendor_domain"))

        if "urgent" in subject or "urgent" in body or "asap" in body:
            signals.append("urgent_payment_pressure")

        if expected_domain and from_domain and expected_domain != from_domain:
            signals.append("sender_domain_spoof")

        if "bank" in body and ("change" in body or "update" in body or "override" in body):
            signals.append("bank_override_attempt")

        thread["derived_flags"] = sorted(set(normalize_text(x) for x in signals if x))
        return {
            "thread": thread,
            "message": "Email thread inspection complete.",
        }

    return {"error": f"thread not found: {thread_id}"}


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
    derived_flags = [] if matched else ["bank_account_mismatch"]

    return {
        "vendor_key": vendor.get("vendor_key"),
        "approved_bank_account": approved_bank_account,
        "proposed_bank_account": proposed_bank_account,
        "matched": matched,
        "derived_flags": derived_flags,
        "message": "Compared proposed bank account to approved master data.",
    }