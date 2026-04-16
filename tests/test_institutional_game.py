from __future__ import annotations

from server.institutional_game import (
    InstitutionalMemory,
    attach_institutional_context,
    institutional_context_for_case,
    public_institutional_memory,
    record_institutional_outcome,
)


def _case(case_id: str, *, unsafe: bool = False) -> dict:
    return {
        "case_id": case_id,
        "task_type": "task_d",
        "gold": {
            "decision": "ESCALATE_FRAUD" if unsafe else "PAY",
            "unsafe_if_pay": unsafe,
            "fields": {
                "vendor_name": "Northwind Industrial Supplies Pvt Ltd",
                "bank_account": "IN55NW000111222",
                "total": 2478,
            },
        },
    }


def test_institutional_context_merges_into_hidden_world_campaign_context():
    cases = [_case("CASE-1"), _case("CASE-2")]
    memory = InstitutionalMemory.from_cases(cases)
    context = institutional_context_for_case(cases[0], cases, memory)
    hidden_world = {"campaign_context": {"linked_invoice_count": 1, "queue_pressure": "normal"}}

    attach_institutional_context(hidden_world, context)

    assert hidden_world["institutional_context"]["week_id"] == memory.week_id
    assert hidden_world["campaign_context"]["manual_review_capacity"] == memory.manual_review_capacity_remaining
    assert hidden_world["campaign_context"]["shared_bank_account_count"] == 2


def test_record_institutional_outcome_updates_loss_and_attacker_belief():
    case = _case("CASE-RISKY", unsafe=True)
    memory = InstitutionalMemory.from_cases([case])
    before = public_institutional_memory(memory)["loss_ledger"]["institutional_loss_score"]

    update = record_institutional_outcome(
        memory,
        case=case,
        submitted={"decision": "PAY"},
        outcome={
            "outcome_type": "unsafe_payment_released",
            "unsafe_payment": True,
            "portfolio_metrics": {"fraud_loss_released": 2478.0},
        },
        trajectory=[],
        compliance={},
    )

    after = update["institutional_memory"]["loss_ledger"]["institutional_loss_score"]
    assert after < before
    assert update["institutional_memory"]["loss_ledger"]["unsafe_release_count"] == 1
    assert update["institutional_memory"]["attacker_belief"]["payment_release_weakness"] > 0.1
