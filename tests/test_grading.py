from __future__ import annotations

from server.grading import DEGENERATE_EVIDENCE_CAP, evidence_score


def test_evidence_score_caps_empty_submission_at_degenerate_limit():
    gold_map = {
        "invoice_total": {
            "doc_id": "INV-123",
            "page": 1,
            "bbox": [10, 20, 120, 60],
            "token_ids": [7, 8, 9],
        }
    }

    assert evidence_score({}, gold_map) == DEGENERATE_EVIDENCE_CAP
