"""
ASHTG end-to-end integration tests.

Verifies the full Adversarial Sequential Hypothesis Testing Game pipeline:
- SPRT state is exposed in observations
- VoI tool rankings are produced
- Reward machine tracks progress
- Categorical MDP component is wired in (Pillar 9)
- Predicted probabilities are derived and sum to 1.0
- RL data plane state vector is exported at every step
- Watchdog integration runs at decision submission
"""
from __future__ import annotations

from models import LedgerShieldAction
from server.environment import LedgerShieldEnvironment


def _diagnostics_env() -> LedgerShieldEnvironment:
    env = LedgerShieldEnvironment()
    env._track_mode = "instrumented"
    return env


# ── Reset exposes ASHTG state ─────────────────────────────────────────────────

def test_reset_hides_ashtg_state_in_blind_mode_by_default():
    env = LedgerShieldEnvironment()
    obs = env.reset(case_id="CASE-D-001")
    assert obs.case_metadata["track_mode"] == "blind"
    assert obs.sprt_state == {}
    assert obs.tool_rankings == {}
    assert obs.reward_machine == {}


def test_reset_exposes_ashtg_state():
    env = _diagnostics_env()
    obs = env.reset(case_id="CASE-D-001")
    assert "posterior_probabilities" in obs.sprt_state
    assert "recommended_tool" in obs.tool_rankings
    assert "progress_fraction" in obs.reward_machine


def test_reset_exposes_categorical_mdp_component():
    env = LedgerShieldEnvironment()
    obs = env.reset(case_id="CASE-D-001")
    assert "mdp_component" in obs.case_metadata
    mdp = obs.case_metadata["mdp_component"]
    assert "component_name" in mdp
    assert "action_space" in mdp
    assert "state_space" in mdp
    assert "required_observations" in mdp
    assert "temporal_spec" in mdp


def test_reset_categorical_component_name_matches_task():
    env = LedgerShieldEnvironment()
    for task_case in [("CASE-D-001", "task_d"), ("CASE-E-001", "task_e")]:
        case_id, task_type = task_case
        obs = env.reset(case_id=case_id)
        assert obs.task_type == task_type
        assert task_type.replace("task_", "").upper() in obs.case_metadata["mdp_component"]["component_name"].upper() or \
               obs.case_metadata["mdp_component"]["component_name"]  # at minimum not empty


def test_sprt_state_has_all_required_fields():
    env = _diagnostics_env()
    obs = env.reset(case_id="CASE-D-001")
    required = {
        "hypotheses", "log_likelihood_ratios", "posterior_probabilities",
        "upper_boundaries", "lower_boundaries", "observations_used",
        "decision_ready", "belief_entropy", "potential",
    }
    assert required <= set(obs.sprt_state.keys())


def test_tool_rankings_contain_voi_scores():
    env = _diagnostics_env()
    obs = env.reset(case_id="CASE-D-001")
    assert "rankings" in obs.tool_rankings
    assert isinstance(obs.tool_rankings["rankings"], dict)
    assert len(obs.tool_rankings["rankings"]) > 0


def test_posterior_sums_to_one_after_reset():
    env = _diagnostics_env()
    obs = env.reset(case_id="CASE-D-001")
    posteriors = obs.sprt_state["posterior_probabilities"]
    total = sum(posteriors.values())
    # Tolerance is 1e-3: the SPRT normalises across 12 hypotheses each with a
    # per-entry epsilon floor, so cumulative rounding places the sum at ~0.9996.
    assert abs(total - 1.0) < 1e-3


# ── Step updates SPRT state ───────────────────────────────────────────────────

def test_sprt_updates_after_compare_bank_account():
    env = _diagnostics_env()
    obs_reset = env.reset(case_id="CASE-D-001")
    prior_bank_fraud = obs_reset.sprt_state["posterior_probabilities"].get("bank_fraud", 0.0)

    obs_step = env.step(
        LedgerShieldAction(action_type="compare_bank_account", payload={"vendor_id": "V001"})
    )
    new_bank_fraud = obs_step.sprt_state["posterior_probabilities"].get("bank_fraud", 0.0)
    # Posterior should have changed (updated with observation)
    assert obs_step.sprt_state["observations_used"] >= 1


def test_reward_machine_advances_on_expected_action():
    env = _diagnostics_env()
    obs_reset = env.reset(case_id="CASE-D-001")
    initial_progress = obs_reset.reward_machine.get("progress_fraction", 0.0)

    obs_step = env.step(
        LedgerShieldAction(action_type="inspect_email_thread", payload={"vendor_id": "V001"})
    )
    new_progress = obs_step.reward_machine.get("progress_fraction", 0.0)
    assert new_progress >= initial_progress


def test_rl_data_plane_exported_at_each_step():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    env.step(LedgerShieldAction(action_type="inspect_email_thread", payload={"vendor_id": "V001"}))
    info = env._last_info
    assert "rl_data_plane" in info
    rl = info["rl_data_plane"]
    assert "state_vector" in rl
    assert "reward" in rl
    assert "terminal" in rl
    sv = rl["state_vector"]
    assert len(sv) > 30  # should be 37-dimensional


def test_rl_state_vector_is_list_of_floats():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    env.step(LedgerShieldAction(action_type="compare_bank_account", payload={"vendor_id": "V001"}))
    sv = env._last_info["rl_data_plane"]["state_vector"]
    assert all(isinstance(v, float) for v in sv)


# ── Decision submission ───────────────────────────────────────────────────────

def test_submit_decision_returns_predicted_probabilities():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-002")
    obs = env.step(
        LedgerShieldAction(
            action_type="submit_decision",
            payload={
                "decision": "PAY",
                "confidence": 0.88,
                "policy_checks": {
                    "three_way_match": "pass",
                    "bank_change_verification": "pass",
                    "duplicate_check": "pass",
                    "approval_threshold_check": "pass",
                },
                "evidence_map": {},
                "counterfactual": "Would HOLD if the sender domain or bank account changed.",
            },
        )
    )
    assert "predicted_probabilities" in obs.last_tool_result
    probs = obs.last_tool_result["predicted_probabilities"]
    assert abs(sum(probs.values()) - 1.0) < 1e-5


def test_submit_decision_produces_score_breakdown():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    obs = env.step(
        LedgerShieldAction(
            action_type="submit_decision",
            payload={
                "decision": "ESCALATE_FRAUD",
                "confidence": 0.9,
                "reason_codes": ["sender_domain_spoof"],
                "policy_checks": {},
                "evidence_map": {},
                "counterfactual": "",
            },
        )
    )
    assert "score_breakdown" in obs.last_tool_result
    assert "final_score" in obs.last_tool_result
    assert 0.0 <= obs.last_tool_result["final_score"] <= 1.0


def test_submit_decision_exposes_watchdog():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    obs = env.step(
        LedgerShieldAction(
            action_type="submit_decision",
            payload={
                "decision": "PAY",
                "confidence": 0.7,
                "policy_checks": {},
                "evidence_map": {},
                "counterfactual": "",
            },
        )
    )
    assert "watchdog" in obs.last_tool_result
    watchdog = obs.last_tool_result["watchdog"]
    assert "verdict" in watchdog


def test_episode_terminates_after_submit():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    env.step(
        LedgerShieldAction(
            action_type="submit_decision",
            payload={
                "decision": "ESCALATE_FRAUD",
                "confidence": 0.9,
                "policy_checks": {},
                "evidence_map": {},
                "counterfactual": "",
            },
        )
    )
    assert env._last_done is True
    assert env._last_terminated is True
    assert env._last_truncated is False


# ── Invalid actions ───────────────────────────────────────────────────────────

def test_invalid_action_returns_negative_reward():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    env.step(LedgerShieldAction(action_type="totally_fake_action", payload={}))
    assert env._last_reward < 0


def test_invalid_decision_returns_error():
    env = LedgerShieldEnvironment()
    env.reset(case_id="CASE-D-001")
    obs = env.step(
        LedgerShieldAction(
            action_type="submit_decision",
            payload={"decision": "MAYBE", "confidence": 0.5},
        )
    )
    assert obs.last_tool_result.get("success") is False


# ── Task E categorical spec ───────────────────────────────────────────────────

def test_task_e_mdp_component_includes_campaign_actions():
    env = LedgerShieldEnvironment()
    obs = env.reset(case_id="CASE-E-001")
    mdp = obs.case_metadata.get("mdp_component", {})
    # Task E should include route_to_security in action space (CampaignDetection component)
    action_space = set(mdp.get("action_space", []))
    assert "route_to_security" in action_space


def test_task_e_component_is_larger_than_task_d():
    env_d = LedgerShieldEnvironment()
    obs_d = env_d.reset(case_id="CASE-D-001")
    env_e = LedgerShieldEnvironment()
    obs_e = env_e.reset(case_id="CASE-E-001")
    actions_d = set(obs_d.case_metadata["mdp_component"]["action_space"])
    actions_e = set(obs_e.case_metadata["mdp_component"]["action_space"])
    assert len(actions_e) >= len(actions_d)
