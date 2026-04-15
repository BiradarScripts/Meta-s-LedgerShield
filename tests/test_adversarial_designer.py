from __future__ import annotations

from server.adversarial_designer import adversarial_policy_for_case, build_regret_profile, prioritize_cases
from server.data_loader import load_all


def test_regret_profile_computes_positive_gap():
    db = load_all()
    case = db["cases_by_id"]["CASE-D-001"]
    profile = build_regret_profile(case=case, achieved_score=0.5, trajectory=[], submitted={"decision": "PAY"})

    assert profile.regret > 0.0
    assert profile.solvable is True


def test_prioritize_cases_prefers_high_regret_solvable_cases():
    db = load_all()
    case = db["cases_by_id"]["CASE-D-001"]
    low = build_regret_profile(case=case, achieved_score=0.9)
    high = build_regret_profile(case=case, achieved_score=0.4)
    ordered = prioritize_cases([low, high])

    assert ordered[0].regret >= ordered[1].regret
    assert adversarial_policy_for_case(case)["priority_tools"]
