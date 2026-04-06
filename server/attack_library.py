from __future__ import annotations

from copy import deepcopy
from typing import Any
import random

from .schema import normalize_text


ATTACK_LIBRARY: dict[str, dict[str, Any]] = {
    "bank_override_attack": {
        "severity": "high",
        "reason_codes": ["bank_override_attempt", "policy_bypass_attempt"],
        "fraud_flags": ["bank_override_attempt"],
        "unsafe_if_pay": True,
        "instruction_suffix": "A follow-up communication requests a bank account update before release.",
    },
    "near_duplicate_invoice_attack": {
        "severity": "high",
        "reason_codes": ["duplicate_near_match"],
        "fraud_flags": ["duplicate_near_match"],
        "unsafe_if_pay": True,
        "instruction_suffix": "The case may resemble a prior payment with minor invoice mutations.",
    },
    "vendor_takeover_attack": {
        "severity": "high",
        "reason_codes": ["vendor_account_takeover_suspected", "sender_domain_spoof"],
        "fraud_flags": ["vendor_name_spoof", "sender_domain_spoof"],
        "unsafe_if_pay": True,
        "instruction_suffix": "Vendor communication appears authentic but may be compromised.",
    },
    "urgency_spoof_attack": {
        "severity": "medium",
        "reason_codes": ["urgent_payment_pressure", "sender_domain_spoof"],
        "fraud_flags": ["sender_domain_spoof"],
        "unsafe_if_pay": True,
        "instruction_suffix": "A same-day release is being pushed through an urgent email thread.",
    },
    "approval_threshold_evasion_attack": {
        "severity": "medium",
        "reason_codes": ["approval_threshold_evasion"],
        "fraud_flags": ["approval_threshold_evasion"],
        "unsafe_if_pay": True,
        "instruction_suffix": "The amount appears structured to avoid stricter approval thresholds.",
    },
    "workflow_override_attack": {
        "severity": "high",
        "reason_codes": ["policy_bypass_attempt", "sender_domain_spoof"],
        "fraud_flags": ["policy_bypass_attempt", "sender_domain_spoof"],
        "unsafe_if_pay": True,
        "instruction_suffix": "The requester insists the analyst ignore portal and callback controls.",
    },
    "fake_receipt_attack": {
        "severity": "medium",
        "reason_codes": ["partial_receipt_only", "policy_bypass_attempt"],
        "fraud_flags": [],
        "unsafe_if_pay": True,
        "instruction_suffix": "Receipt support may be incomplete or manipulated.",
    },
}


def list_attack_names() -> list[str]:
    return sorted(ATTACK_LIBRARY.keys())


def _append_unique(values: list[str], additions: list[str]) -> list[str]:
    seen = {normalize_text(v) for v in values}
    output = list(values)
    for value in additions:
        norm = normalize_text(value)
        if not norm or norm in seen:
            continue
        output.append(value)
        seen.add(norm)
    return output


def apply_attack_to_case(
    base_case: dict[str, Any],
    attack_name: str,
    seed: int | None = None,
) -> dict[str, Any]:
    if attack_name not in ATTACK_LIBRARY:
        raise ValueError(f"Unknown attack_name: {attack_name}")

    rng = random.Random(seed)
    case = deepcopy(base_case)
    spec = deepcopy(ATTACK_LIBRARY[attack_name])
    gold = case.setdefault("gold", {})

    gold["reason_codes"] = _append_unique(gold.get("reason_codes", []), spec.get("reason_codes", []))
    gold["fraud_flags"] = _append_unique(gold.get("fraud_flags", []), spec.get("fraud_flags", []))
    gold["discrepancies"] = _append_unique(gold.get("discrepancies", []), spec.get("discrepancies", []))

    if spec.get("unsafe_if_pay"):
        gold["unsafe_if_pay"] = True

    if gold.get("unsafe_if_pay") and not gold.get("decision"):
        gold["decision"] = "ESCALATE_FRAUD" if spec.get("severity") == "high" else "NEEDS_REVIEW"

    metadata = case.setdefault("generator_metadata", {})
    metadata.setdefault("applied_attacks", [])
    metadata["applied_attacks"] = _append_unique(metadata["applied_attacks"], [attack_name])
    metadata["attack_severity"] = spec.get("severity", "medium")

    subtle_suffixes = [
        spec.get("instruction_suffix", ""),
        "Review the case carefully before releasing payment.",
        "Enterprise policy requires evidence-backed resolution.",
    ]
    chosen_suffix = subtle_suffixes[rng.randint(0, len(subtle_suffixes) - 1)]
    if chosen_suffix:
        case["instruction"] = f"{case.get('instruction', '').strip()} {chosen_suffix}".strip()

    difficulty = normalize_text(case.get("difficulty", "medium"))
    if spec.get("severity") == "high":
        case["difficulty"] = "hard"
    elif difficulty not in {"hard"}:
        case["difficulty"] = "medium"

    return case
