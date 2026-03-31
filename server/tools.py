from __future__ import annotations

from copy import deepcopy
from typing import Any


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
        "visual_tokens": deepcopy(doc.get("visual_tokens", []))[:10],
        "message": "Zoom completed.",
    }


def ocr_tool(case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    doc_id = payload.get("doc_id")
    mode = payload.get("mode", "fast")

    doc = _find_doc(case, doc_id)
    if doc is None:
        return {"error": f"unknown doc_id: {doc_id}"}

    if mode == "accurate":
        tokens = deepcopy(doc.get("accurate_ocr", []))
    else:
        tokens = deepcopy(doc.get("noisy_ocr", []))

    return {
        "doc_id": doc_id,
        "mode": mode,
        "tokens": tokens,
        "message": f"Returned {mode} OCR.",
    }


def lookup_vendor_tool(vendors: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    vendor_key = str(payload.get("vendor_key", "")).strip().lower()

    for vendor in vendors:
        candidate_key = str(vendor.get("vendor_key", "")).strip().lower()
        candidate_name = str(
            vendor.get("canonical_name", vendor.get("vendor_name", ""))
        ).strip().lower()

        if vendor_key == candidate_key or vendor_key == candidate_name:
            return {
                "vendor": deepcopy(vendor),
                "message": "Vendor lookup complete.",
            }

    return {"error": f"vendor not found: {payload.get('vendor_key')}"}


def lookup_vendor_history_tool(
    vendor_history: list[dict[str, Any]],
    payload: dict[str, Any],
) -> dict[str, Any]:
    vendor_key = str(payload.get("vendor_key", "")).strip().lower()

    history = [
        deepcopy(row)
        for row in vendor_history
        if str(row.get("vendor_key", "")).strip().lower() == vendor_key
    ]

    return {
        "vendor_key": payload.get("vendor_key"),
        "history": history,
        "message": "Vendor history returned.",
    }


def lookup_policy_tool(policy_rules: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    rule_id = payload.get("rule_id")

    if rule_id:
        for rule in policy_rules:
            if rule.get("rule_id") == rule_id:
                return {
                    "policy": deepcopy(rule),
                    "message": "Policy lookup complete.",
                }
        return {"error": f"policy not found: {rule_id}"}

    return {
        "policies": deepcopy(policy_rules),
        "message": "All policy rules returned.",
    }


def lookup_po_tool(po_records: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    po_id = payload.get("po_id")

    for record in po_records:
        if record.get("po_id") == po_id:
            return {
                "po": deepcopy(record),
                "message": "PO lookup complete.",
            }

    return {"error": f"po not found: {po_id}"}


def lookup_receipt_tool(receipts: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    receipt_id = payload.get("receipt_id")

    for record in receipts:
        if record.get("receipt_id") == receipt_id:
            return {
                "receipt": deepcopy(record),
                "message": "Receipt lookup complete.",
            }

    return {"error": f"receipt not found: {receipt_id}"}


def search_ledger_tool(ledger_index: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    vendor_key = payload.get("vendor_key")
    invoice_number = payload.get("invoice_number")
    amount = payload.get("amount")

    hits: list[dict[str, Any]] = []

    for row in ledger_index:
        if vendor_key is not None and row.get("vendor_key") != vendor_key:
            continue
        if invoice_number is not None and row.get("invoice_number") != invoice_number:
            continue
        if amount is not None:
            try:
                if abs(float(row.get("amount", 0.0)) - float(amount)) > 0.01:
                    continue
            except Exception:
                continue

        hits.append(deepcopy(row))

    return {
        "hits": hits[:10],
        "count": len(hits),
        "message": "Ledger search complete.",
    }


def inspect_email_thread_tool(
    email_threads: list[dict[str, Any]],
    payload: dict[str, Any],
) -> dict[str, Any]:
    thread_id = payload.get("thread_id")

    for row in email_threads:
        if row.get("thread_id") == thread_id:
            thread = deepcopy(row)

            if "flags" not in thread and "fraud_signals" in thread:
                thread["flags"] = deepcopy(thread.get("fraud_signals", []))

            return {
                "thread": thread,
                "message": "Email thread inspection complete.",
            }

    return {"error": f"thread not found: {thread_id}"}


def compare_bank_account_tool(vendors: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    vendor_key = str(payload.get("vendor_key", "")).strip().lower()
    proposed_bank_account = payload.get("proposed_bank_account")

    for vendor in vendors:
        candidate_key = str(vendor.get("vendor_key", "")).strip().lower()
        if candidate_key != vendor_key:
            continue

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
            "message": "Compared proposed bank account to approved master data.",
        }

    return {"error": f"vendor not found: {payload.get('vendor_key')}"}