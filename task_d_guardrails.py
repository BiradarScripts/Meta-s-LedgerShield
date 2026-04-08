from __future__ import annotations

from typing import Any

from server.schema import normalize_text, safe_float


def token_ref(token: dict[str, Any], doc_id: str) -> dict[str, Any]:
    return {
        "doc_id": doc_id,
        "page": int(token.get("page", 1) or 1),
        "bbox": token.get("bbox", []),
        "token_ids": [str(token.get("token_id", ""))],
    }


def _looks_like_token_ref(value: Any) -> bool:
    return isinstance(value, dict) and {"doc_id", "page", "bbox", "token_ids"} <= set(value)


def derive_email_thread_signals(thread: dict[str, Any]) -> set[str]:
    sender_profile = thread.get("sender_profile", {}) or {}
    request_signals = thread.get("request_signals", {}) or {}
    signals = {
        normalize_text(flag)
        for flag in (thread.get("derived_flags", []) or []) + (thread.get("flags", []) or [])
        if normalize_text(flag)
    }

    if normalize_text(sender_profile.get("domain_alignment")) == "mismatch":
        signals.add("sender_domain_spoof")
    if bool(request_signals.get("bank_change_language")):
        signals.add("bank_override_attempt")
    if bool(request_signals.get("callback_discouraged")) or bool(request_signals.get("policy_override_language")):
        signals.add("policy_bypass_attempt")
    if bool(request_signals.get("urgency_language")):
        signals.add("urgent_payment_pressure")

    return signals


def policy_check_payload(three_way_match: str, bank_change_verification: str, duplicate_check: str) -> dict[str, str]:
    return {
        "three_way_match": three_way_match,
        "bank_change_verification": bank_change_verification,
        "duplicate_check": duplicate_check,
        "approval_threshold_check": "pass",
    }


def make_task_d_counterfactual(candidate: Any) -> str:
    text = str(candidate or "").strip()
    if len(text.split()) >= 6:
        return text
    return (
        "Would PAY if the sender domain matched approved vendor records, "
        "the bank account matched vendor master, and no duplicate cluster existed."
    )


def _task_d_findings(collected: dict[str, Any]) -> dict[str, Any]:
    invoice_records = collected.get("invoice_records", []) or []
    primary_record = invoice_records[0] if invoice_records else {
        "fields": collected.get("invoice_fields", {}),
        "evidence": collected.get("invoice_evidence", {}),
    }
    email_evidence = collected.get("email_evidence", {})
    email_thread = collected.get("email_thread") or {}
    ledger_search = collected.get("ledger_search") or {}
    bank_compares = collected.get("bank_compares") or (
        [collected.get("bank_compare")] if collected.get("bank_compare") else []
    )
    vendor_history = collected.get("vendor_history", []) or []
    ledger_hits = collected.get("ledger_hits", []) or []

    email_flags = derive_email_thread_signals(email_thread)
    duplicate_detected = bool(ledger_hits) or int(ledger_search.get("exact_duplicate_count", 0) or 0) > 0
    bank_mismatch = any(compare and not bool(compare.get("matched")) for compare in bank_compares)
    invoice_totals = [safe_float(record.get("fields", {}).get("total")) for record in invoice_records]
    threshold_split = (
        len(invoice_totals) >= 2
        and sum(invoice_totals) >= 3000.0
        and all(0.0 < total < 2000.0 for total in invoice_totals)
    )
    high_value_pressure = any(total >= 50000.0 for total in invoice_totals) and "urgent_payment_pressure" in email_flags
    suspicious_history = any(
        normalize_text(item.get("status")) in {"rejected", "pending_callback_verification", "failed", "denied"}
        and "bank" in normalize_text(item.get("change_type") or item.get("event_type"))
        for item in vendor_history
    )
    suspicious = duplicate_detected or bank_mismatch or bool(email_flags) or suspicious_history or threshold_split

    bank_evidence = None
    duplicate_evidence = None
    for record in invoice_records or [primary_record]:
        evidence = record.get("evidence", {})
        if bank_evidence is None and "bank_account" in evidence:
            bank_evidence = evidence["bank_account"]
        if duplicate_evidence is None and "invoice_number" in evidence:
            duplicate_evidence = evidence["invoice_number"]

    evidence_map: dict[str, Any] = {}
    reason_codes: list[str] = []

    if bank_mismatch and bank_evidence:
        evidence_map["bank_override_attempt"] = bank_evidence
        reason_codes.append("bank_override_attempt")
    if duplicate_detected and duplicate_evidence:
        evidence_map["duplicate_near_match"] = duplicate_evidence
        reason_codes.append("duplicate_near_match")
    if ("sender_domain_spoof" in email_flags or "sender_domain_spoof" in email_evidence) and "from_header" in email_evidence:
        evidence_map["sender_domain_spoof"] = email_evidence["from_header"]
        reason_codes.append("sender_domain_spoof")
    if "approval_threshold_evasion" in email_flags or threshold_split or "approval_threshold_evasion" in email_evidence:
        threshold_evidence = (
            email_evidence.get("approval_threshold_evasion")
            or email_evidence.get("subject_header")
            or duplicate_evidence
        )
        if threshold_evidence:
            evidence_map["approval_threshold_evasion"] = threshold_evidence
        reason_codes.append("approval_threshold_evasion")
    if "policy_bypass_attempt" in email_flags or "policy_bypass_attempt" in email_evidence:
        bypass_evidence = (
            email_evidence.get("policy_bypass_attempt")
            or email_evidence.get("subject_header")
            or email_evidence.get("from_header")
        )
        if bypass_evidence:
            evidence_map["policy_bypass_attempt"] = bypass_evidence
        reason_codes.append("policy_bypass_attempt")
    if "urgent_payment_pressure" in email_flags:
        urgent_evidence = (
            email_evidence.get("subject_header")
            or email_evidence.get("policy_bypass_attempt")
            or email_evidence.get("from_header")
        )
        if urgent_evidence:
            evidence_map["urgent_payment_pressure"] = urgent_evidence
        reason_codes.append("urgent_payment_pressure")

    policy_checks = policy_check_payload(
        three_way_match="pass",
        bank_change_verification="fail"
        if bank_mismatch or "sender_domain_spoof" in reason_codes or "policy_bypass_attempt" in reason_codes
        else "pass",
        duplicate_check="fail" if duplicate_detected else "pass",
    )
    if "approval_threshold_evasion" in reason_codes or high_value_pressure:
        policy_checks["approval_threshold_check"] = "fail"

    return {
        "primary_record": primary_record,
        "suspicious": suspicious,
        "reason_codes": sorted(set(reason_codes)),
        "evidence_map": evidence_map,
        "policy_checks": policy_checks,
    }


def grounded_task_d_submission(collected: dict[str, Any], *, counterfactual: Any = "") -> dict[str, Any]:
    findings = _task_d_findings(collected)
    if not findings["suspicious"]:
        return {
            "decision": "PAY",
            "confidence": 0.88,
            "reason_codes": [],
            "policy_checks": policy_check_payload("pass", "pass", "pass"),
            "evidence_map": {},
            "counterfactual": (
                "Would HOLD if the sender domain changed, the bank account mismatched "
                "vendor master, or a duplicate cluster appeared in ledger history."
            ),
        }

    return {
        "decision": "ESCALATE_FRAUD",
        "confidence": 0.99,
        "reason_codes": findings["reason_codes"],
        "policy_checks": findings["policy_checks"],
        "evidence_map": findings["evidence_map"],
        "counterfactual": make_task_d_counterfactual(counterfactual),
    }


def sanitize_task_d_submission(candidate: dict[str, Any], collected: dict[str, Any]) -> dict[str, Any]:
    """
    Keep only grounded reason codes, but preserve model misses for benchmarking.

    Unlike validate_task_d_submission(), this function does not auto-fill the full
    grounded answer. It allows the benchmark to observe whether the model chose the
    right decision and which grounded reasons it actually surfaced.
    """

    grounded = grounded_task_d_submission(
        collected,
        counterfactual=(candidate or {}).get("counterfactual", ""),
    )
    decision = str((candidate or {}).get("decision", grounded["decision"])).strip().upper()
    if decision not in {"PAY", "HOLD", "NEEDS_REVIEW", "ESCALATE_FRAUD"}:
        decision = grounded["decision"]

    try:
        confidence = float((candidate or {}).get("confidence", 0.5))
    except Exception:
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    grounded_reason_codes = set(grounded.get("reason_codes", []))
    candidate_reason_codes = [
        reason
        for reason in (candidate or {}).get("reason_codes", []) or []
        if normalize_text(reason) in {normalize_text(item) for item in grounded_reason_codes}
    ]

    policy_checks = dict(grounded.get("policy_checks", {}) or {})
    candidate_evidence = (candidate or {}).get("evidence_map", {}) or {}
    grounded_evidence = grounded.get("evidence_map", {}) or {}
    evidence_map = {}
    for reason in candidate_reason_codes:
        if reason not in grounded_evidence:
            continue
        candidate_ref = candidate_evidence.get(reason)
        evidence_map[reason] = candidate_ref if _looks_like_token_ref(candidate_ref) else grounded_evidence.get(reason)

    if decision != "ESCALATE_FRAUD":
        candidate_reason_codes = []
        evidence_map = {}

    return {
        "decision": decision,
        "confidence": confidence,
        "reason_codes": candidate_reason_codes,
        "policy_checks": policy_checks,
        "evidence_map": evidence_map,
        "counterfactual": make_task_d_counterfactual((candidate or {}).get("counterfactual", "")),
    }


def validate_task_d_submission(candidate: dict[str, Any], collected: dict[str, Any]) -> dict[str, Any]:
    grounded = grounded_task_d_submission(
        collected,
        counterfactual=(candidate or {}).get("counterfactual", ""),
    )
    decision = normalize_text((candidate or {}).get("decision"))

    if grounded["decision"] == "PAY" and decision != "pay":
        return grounded
    if grounded["decision"] == "ESCALATE_FRAUD" and decision != "escalate_fraud":
        return grounded

    try:
        confidence = float((candidate or {}).get("confidence", grounded["confidence"]))
    except Exception:
        confidence = float(grounded["confidence"])
    grounded["confidence"] = max(float(grounded["confidence"]), max(0.0, min(1.0, confidence)))
    return grounded
