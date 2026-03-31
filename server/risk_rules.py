from __future__ import annotations

from .schema import normalize_text


def assess_submission_risk(submitted: dict, gold: dict) -> tuple[float, list[str]]:
    reasons: list[str] = []
    risk = 0.0

    decision = normalize_text(submitted.get("decision", ""))
    if decision == "pay" and gold.get("unsafe_if_pay"):
        risk += 0.6
        reasons.append("unsafe_pay_attempt")

    for code in submitted.get("reason_codes", []):
        norm = normalize_text(code)
        if norm in {"bank_override_attempt", "sender_domain_spoof", "vendor_name_spoof"}:
            risk += 0.1
            reasons.append(norm)

    score = max(0.0, min(1.0, risk))
    return score, sorted(set(reasons))
