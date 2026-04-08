from __future__ import annotations

from copy import deepcopy
import re
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


def _doc_vendor_name(case: dict[str, Any]) -> str:
    for doc in case.get("documents", []):
        if normalize_text(doc.get("doc_type")) != "invoice":
            continue
        for token in _scoped_tokens(doc, mode="accurate"):
            text = str(token.get("text", "")).strip()
            if text:
                return text
    return ""


def _infer_sender_domain_alignment(sender: str, *, expected_domain: str, vendor_name: str) -> str:
    from_domain = prefix_domain(sender)
    expected = prefix_domain(expected_domain)
    if expected and from_domain:
        return "mismatch" if expected != from_domain else "aligned"
    if not from_domain:
        return "aligned"

    stop_words = {
        "ag",
        "co",
        "company",
        "components",
        "corp",
        "gmbh",
        "group",
        "holdings",
        "industrial",
        "llc",
        "llp",
        "limited",
        "ltd",
        "manufacturing",
        "pvt",
        "supplies",
    }
    vendor_tokens = {
        chunk
        for chunk in re.split(r"[^a-z0-9]+", normalize_text(vendor_name))
        if len(chunk) > 2 and chunk not in stop_words
    }
    domain_tokens = {
        chunk
        for chunk in re.split(r"[^a-z0-9]+", normalize_text(from_domain))
        if len(chunk) > 2
    }
    if vendor_tokens and domain_tokens and vendor_tokens & domain_tokens:
        return "aligned"
    return "mismatch" if vendor_tokens else "aligned"


def _build_thread_payload(
    *,
    thread_id: str,
    vendor_key: str,
    sender: str,
    subject: str,
    body: str,
    expected_domain: str = "",
    vendor_name: str = "",
) -> dict[str, Any]:
    subject_norm = normalize_text(subject)
    body_norm = normalize_text(body)
    sender_norm = normalize_text(sender)
    from_domain = prefix_domain(sender_norm)
    expected = prefix_domain(expected_domain)

    urgency_language = any(
        phrase in subject_norm or phrase in body_norm
        for phrase in {"urgent", "asap", "immediately", "today"}
    )
    explicit_no_change = any(
        phrase in body_norm
        for phrase in {
            "no bank change",
            "no bank changes",
            "no change to bank",
            "approved remittance instructions already on file",
        }
    )
    bank_change_language = (
        "bank" in body_norm and ("change" in body_norm or "update" in body_norm or "override" in body_norm)
        and not explicit_no_change
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
        "skip normal review",
        "personally approved",
    }
    callback_discouraged = any(
        phrase in body_norm
        for phrase in {"skip callback", "do not call", "don't call", "do not verify"}
    )
    policy_override_language = any(phrase in body_norm for phrase in bypass_phrases)
    quoted_directives: list[str] = []
    if bank_change_language:
        quoted_directives.append("bank or remittance instructions changed in email body")
    if callback_discouraged:
        quoted_directives.append("email discourages callback verification")
    if policy_override_language:
        quoted_directives.append("email pressures agent to override standard workflow")
    if urgency_language:
        quoted_directives.append("message uses urgency language")

    return {
        "thread_id": thread_id,
        "vendor_key": vendor_key,
        "sender": sender,
        "subject": subject,
        "body": body,
        "message_count": max(1, len([line for line in body.splitlines() if line.strip()])),
        "sender_profile": {
            "from_domain": from_domain,
            "expected_domain": expected,
            "domain_alignment": _infer_sender_domain_alignment(
                sender_norm,
                expected_domain=expected,
                vendor_name=vendor_name,
            ),
        },
        "request_signals": {
            "bank_change_language": bank_change_language,
            "urgency_language": urgency_language,
            "callback_discouraged": callback_discouraged,
            "policy_override_language": policy_override_language,
        },
        "quoted_directives": quoted_directives,
    }


def _thread_from_email_document(case: dict[str, Any], thread_id: str, doc: dict[str, Any]) -> dict[str, Any] | None:
    if normalize_text(doc.get("doc_type")) != "email":
        return None

    lines = [
        str(token.get("text", "")).strip()
        for token in _scoped_tokens(doc, mode="accurate")
        if str(token.get("text", "")).strip()
    ]
    if not lines:
        return None

    sender = ""
    subject = ""
    body_lines: list[str] = []
    for line in lines:
        lower = line.lower()
        if lower.startswith("from:"):
            sender = line.split(":", 1)[-1].strip()
            continue
        if lower.startswith("subject:"):
            subject = line.split(":", 1)[-1].strip()
            continue
        body_lines.append(line)

    return _build_thread_payload(
        thread_id=thread_id,
        vendor_key="",
        sender=sender,
        subject=subject,
        body="\n".join(body_lines),
        vendor_name=_doc_vendor_name(case),
    )


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
    email_doc = None
    for doc in case.get("documents", []):
        if doc.get("doc_id") == thread_id:
            email_doc = doc
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
        if email_doc is not None:
            inferred = _thread_from_email_document(case, str(thread_id), email_doc)
            if inferred is not None:
                return {
                    "thread": inferred,
                    "message": "Email thread inspection derived from document OCR.",
                }
        return {"error": f"thread not found: {thread_id}"}

    thread = _build_thread_payload(
        thread_id=str(row.get("thread_id") or thread_id),
        vendor_key=str(row.get("vendor_key") or ""),
        sender=str(row.get("sender") or row.get("from") or ""),
        subject=str(row.get("subject") or ""),
        body=str(row.get("body") or " ".join(row.get("messages", []))),
        expected_domain=str(row.get("expected_domain") or row.get("vendor_domain") or ""),
    )
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
