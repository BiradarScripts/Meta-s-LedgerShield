from __future__ import annotations

import compare_all_models


def test_score_from_end_prefers_exact_score_over_rounded_rewards():
    exact = compare_all_models._score_from_end("0.9817", "-0.06,-0.06,0.98")
    fallback = compare_all_models._score_from_end(None, "-0.06,-0.06,0.98")

    assert exact == 0.9817
    assert fallback == 0.98
