from __future__ import annotations

from server.data_loader import load_all
from server.information_design import MarkovPersuasionEnvironment


def test_information_design_prioritizes_discriminative_tools():
    db = load_all()
    case = db["cases_by_id"]["CASE-D-001"]
    policy = MarkovPersuasionEnvironment().optimal_signaling_policy(
        case,
        agent_capability_prior={"good_agent": 0.7, "weak_agent": 0.3},
    )

    assert policy["priority_tools"]
    assert "compare_bank_account" in policy["discriminative_weights"]
    assert policy["clarity_budget"] > 0.0
