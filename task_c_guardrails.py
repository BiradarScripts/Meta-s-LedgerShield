from __future__ import annotations

from typing import Any

from server.schema import canonical_reason_codes, normalize_text


def grounded_task_c_submission(collected: dict[str, Any]) -> dict[str, Any]:
    invoice_evidence = collected.get("invoice_evidence", {}) or {}
    ledger_search = collected.get("ledger_search") or {}
    duplicate_links = [
        hit.get("ledger_id")
        for hit in collected.get("ledger_hits", []) or []
        if hit.get("ledger_id")
    ]
    bank_compare = collected.get("bank_compare") or {}
    bank_compares = collected.get("bank_compares") or ([bank_compare] if bank_compare else [])

    bank_mismatch = any(compare and not bool(compare.get("matched")) for compare in bank_compares)
    duplicate_detected = (
        bool(duplicate_links)
        or int(ledger_search.get("exact_duplicate_count", 0) or 0) > 0
        or int(ledger_search.get("near_duplicate_count", 0) or 0) > 0
    )
    suspicious = bank_mismatch or duplicate_detected

    evidence_map: dict[str, Any] = {}
    fraud_flags: list[str] = []

    if bank_mismatch and "bank_account" in invoice_evidence:
        evidence_map["bank_override_attempt"] = invoice_evidence["bank_account"]
        fraud_flags.append("bank_override_attempt")

    if duplicate_detected and "invoice_number" in invoice_evidence:
        evidence_map["duplicate_near_match"] = invoice_evidence["invoice_number"]
        fraud_flags.append("duplicate_near_match")

    return {
        "decision": "ESCALATE_FRAUD" if suspicious else "PAY",
        "confidence": 0.98 if suspicious else 0.87,
        "duplicate_links": duplicate_links if suspicious else [],
        "fraud_flags": fraud_flags,
        "evidence_map": evidence_map,
    }


def _clamped_confidence(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        parsed = default
    return max(0.0, min(1.0, parsed))


def sanitize_task_c_submission(candidate: dict[str, Any], collected: dict[str, Any]) -> dict[str, Any]:
    """
    Keep only grounded signals, but do not auto-repair the model into the gold answer.

    This preserves benchmark separation: if the model misses a fraud signal or chooses
    the wrong decision, the mistake should be graded instead of silently corrected away.
    """

    grounded = grounded_task_c_submission(collected)
    decision = str((candidate or {}).get("decision", grounded["decision"])).strip().upper()
    if decision not in {"PAY", "ESCALATE_FRAUD"}:
        decision = grounded["decision"]

    confidence = _clamped_confidence((candidate or {}).get("confidence"), 0.5)

    grounded_flags = canonical_reason_codes(grounded.get("fraud_flags", []))
    grounded_flag_set = {normalize_text(flag) for flag in grounded_flags}
    candidate_flags = canonical_reason_codes((candidate or {}).get("fraud_flags", []))
    fraud_flags = [flag for flag in candidate_flags if normalize_text(flag) in grounded_flag_set]

    grounded_links = {str(link) for link in grounded.get("duplicate_links", []) if str(link).strip()}
    requested_links = [str(link) for link in (candidate or {}).get("duplicate_links", []) if str(link).strip()]
    duplicate_links = [link for link in requested_links if link in grounded_links]

    candidate_evidence = (candidate or {}).get("evidence_map", {}) or {}
    grounded_evidence = grounded.get("evidence_map", {}) or {}
    evidence_map = {
        flag: (
            candidate_evidence.get(flag)
            if isinstance(candidate_evidence.get(flag), dict)
            else grounded_evidence.get(flag)
        )
        for flag in fraud_flags
        if flag in grounded_evidence
    }

    if decision != "ESCALATE_FRAUD":
        fraud_flags = []
        duplicate_links = []
        evidence_map = {}

    return {
        "decision": decision,
        "confidence": confidence,
        "duplicate_links": duplicate_links,
        "fraud_flags": fraud_flags,
        "evidence_map": evidence_map,
    }


def validate_task_c_submission(candidate: dict[str, Any], collected: dict[str, Any]) -> dict[str, Any]:
    grounded = grounded_task_c_submission(collected)

    try:
        confidence = float((candidate or {}).get("confidence", grounded["confidence"]))
    except Exception:
        confidence = float(grounded["confidence"])

    grounded["confidence"] = max(float(grounded["confidence"]), max(0.0, min(1.0, confidence)))
    return grounded
