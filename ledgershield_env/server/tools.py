from __future__ import annotations
from difflib import SequenceMatcher
from typing import Any

def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def zoom_tool(case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    doc_id = payload.get("doc_id")
    region = payload.get("bbox", [0, 0, 100, 100])
    for doc in case.get("documents", []):
        if doc["doc_id"] == doc_id:
            return {
                "doc_id": doc_id,
                "bbox": region,
                "crop_hint": f"zoomed view for {doc_id}",
                "visual_tokens": doc.get("visual_tokens", [])[:10],
            }
    return {"error": f"unknown doc_id: {doc_id}"}

def ocr_tool(case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    doc_id = payload.get("doc_id")
    mode = payload.get("mode", "fast")
    for doc in case.get("documents", []):
        if doc["doc_id"] == doc_id:
            if mode == "accurate":
                return {
                    "doc_id": doc_id,
                    "mode": mode,
                    "tokens": doc.get("accurate_ocr", []),
                }
            return {
                "doc_id": doc_id,
                "mode": mode,
                "tokens": doc.get("noisy_ocr", []),
            }
    return {"error": f"unknown doc_id: {doc_id}"}

def lookup_vendor_tool(vendors: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    key = str(payload.get("vendor_key", "")).strip().lower()
    for vendor in vendors:
        if vendor["vendor_key"].lower() == key or vendor["canonical_name"].lower() == key:
            return vendor
    return {"error": f"vendor not found: {key}"}

def lookup_po_tool(po_records: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    po_id = payload.get("po_id")
    for record in po_records:
        if record["po_id"] == po_id:
            return record
    return {"error": f"po not found: {po_id}"}

def lookup_receipt_tool(receipts: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    receipt_id = payload.get("receipt_id")
    for record in receipts:
        if record["receipt_id"] == receipt_id:
            return record
    return {"error": f"receipt not found: {receipt_id}"}

def search_ledger_tool(ledger_index: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("similarity_query", "")).strip()
    if not query:
        return {"matches": []}
    scored = []
    for row in ledger_index:
        score = max(
            _similarity(query, row.get("invoice_number", "")),
            _similarity(query, row.get("vendor_name", "")),
            _similarity(query, row.get("fingerprint", ""))
        )
        scored.append({**row, "score": round(score, 4)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return {"matches": scored[:5]}