from __future__ import annotations

from server.causal_model import build_causal_model_for_case, scenario_template_from_case
from server.data_loader import load_all


def test_scenario_template_infers_campaign_case():
    db = load_all()
    template = scenario_template_from_case(db["cases_by_id"]["CASE-E-001"])
    assert template.hypothesis in {"campaign_fraud", "multi_entity_layering"}


def test_d_separation_improves_after_observing_required_nodes():
    db = load_all()
    scm = build_causal_model_for_case(db["cases_by_id"]["CASE-D-001"])

    bare = scm.d_separation_sufficiency(set())
    observed = scm.observed_nodes_for_actions(["inspect_email_thread", "compare_bank_account", "request_callback_verification"])
    informed = scm.d_separation_sufficiency(observed)

    assert informed >= bare


def test_counterfactual_clean_world_recommends_payment():
    db = load_all()
    scm = build_causal_model_for_case(db["cases_by_id"]["CASE-D-001"])
    counterfactual = scm.counterfactual(
        overrides={
            "sender_authenticity": "verified",
            "bank_alignment": "match",
            "approval_chain_integrity": "approved",
            "duplicate_pattern": "absent",
            "callback_result": "clean",
        }
    )

    assert counterfactual["decision"] == "PAY"
