from __future__ import annotations

from server.dual_agent_mode import compute_stackelberg_equilibrium


def test_stackelberg_equilibrium_returns_valid_mixed_strategy():
    analyst = {
        "audit_payment": {"pay": -0.8, "hold": 0.4},
        "audit_identity": {"pay": -0.6, "hold": 0.5},
        "audit_duplicate": {"pay": -0.5, "hold": 0.45},
    }
    watchdog = {
        "audit_payment": {"pay": 1.0, "hold": 0.3},
        "audit_identity": {"pay": 0.8, "hold": 0.4},
        "audit_duplicate": {"pay": 0.7, "hold": 0.5},
    }

    strategy = compute_stackelberg_equilibrium(analyst, watchdog, resolution=0.2)

    assert round(sum(strategy.audit_probabilities.values()), 6) == 1.0
    assert 0.0 < strategy.veto_threshold < 1.0
