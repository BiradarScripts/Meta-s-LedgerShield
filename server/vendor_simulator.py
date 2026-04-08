from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import random
from typing import Any

from .schema import normalize_text


class CallbackOutcome(str, Enum):
    CONFIRMS_LEGITIMATE = "confirms_legitimate"
    DISPUTES_CHANGE = "disputes_change"
    ADVERSARIAL_CONFIRM = "adversarial_confirm"
    NO_ANSWER = "no_answer"


@dataclass
class VendorSimulatorState:
    vendor_id: str
    vendor_compromised: bool
    attacker_has_phone: bool


def build_vendor_simulator_state(case: dict[str, Any], hidden_signals: list[str], seed: int) -> VendorSimulatorState:
    vendor_id = normalize_text(case.get("vendor_key"))
    if not vendor_id:
        for doc in case.get("documents", []):
            vendor_id = normalize_text(doc.get("vendor_key")) or vendor_id
            if vendor_id:
                break

    signals = {normalize_text(signal) for signal in hidden_signals}
    risky = bool((case.get("gold", {}) or {}).get("unsafe_if_pay"))
    vendor_compromised = risky and bool(
        signals
        & {
            "bank_override_attempt",
            "vendor_account_takeover_suspected",
            "sender_domain_spoof",
            "policy_bypass_attempt",
        }
    )
    rng = random.Random(seed)
    attacker_has_phone = vendor_compromised and (
        "policy_bypass_attempt" in signals or "sender_domain_spoof" in signals or rng.random() < 0.35
    )
    return VendorSimulatorState(
        vendor_id=vendor_id or "unknown-vendor",
        vendor_compromised=vendor_compromised,
        attacker_has_phone=attacker_has_phone,
    )


def simulate_callback(case: dict[str, Any], sim_state: VendorSimulatorState, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    if not sim_state.vendor_compromised:
        outcome = CallbackOutcome.CONFIRMS_LEGITIMATE
        response_text = (
            "Vendor confirmed that account details are unchanged and no bank change was requested."
        )
        risk_signal = "callback_clean"
    elif sim_state.attacker_has_phone:
        outcome = CallbackOutcome.ADVERSARIAL_CONFIRM
        response_text = (
            "Call answered. Party confirmed account change, but voice did not match the registered contact "
            "and the callback originated from an unusual area code."
        )
        risk_signal = "callback_suspicious_confirm"
    else:
        outcome = CallbackOutcome.DISPUTES_CHANGE
        response_text = (
            "Vendor disputes the change: no bank change request was submitted and an immediate freeze was requested."
        )
        risk_signal = "callback_dispute_confirmed"

    if normalize_text((case.get("gold", {}) or {}).get("decision")) == "pay" and rng.random() < 0.05:
        outcome = CallbackOutcome.NO_ANSWER
        response_text = "No answer from registered callback contact. Retry later."
        risk_signal = "callback_no_answer"

    return {
        "artifact_id": "callback_verification_result",
        "artifact_type": "verification",
        "summary": f"Vendor callback outcome: {outcome.value}.",
        "details": {
            "outcome": outcome.value,
            "response_text": response_text,
            "risk_signal": risk_signal,
            "hidden_vendor_compromised": None,
            "hidden_attacker_phone": None,
        },
    }


def get_callback_grading_weight(outcome: str, gold_decision: str) -> float:
    normalized_outcome = normalize_text(outcome)
    normalized_decision = normalize_text(gold_decision)
    if normalized_outcome == "callback_dispute_confirmed" and normalized_decision == "escalate_fraud":
        return 0.12
    if normalized_outcome == "callback_suspicious_confirm" and normalized_decision == "escalate_fraud":
        return 0.09
    if normalized_outcome == "callback_clean" and normalized_decision == "pay":
        return 0.05
    return 0.0
