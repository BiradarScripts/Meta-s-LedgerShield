from __future__ import annotations

import benchmark_report
from server.data_loader import load_all
from server.tools import lookup_vendor_history_tool, search_ledger_tool


def test_search_ledger_tool_resolves_vendor_alias_without_false_duplicate_on_clean_case():
    db = load_all()
    case = db["cases_by_id"]["CASE-C-002"]

    result = search_ledger_tool(
        case,
        db["ledger_index"],
        {
            "vendor_key": "eurocaps components gmbh",
            "invoice_number": "EC-4402-26",
            "amount": 845.0,
        },
    )

    assert result["count"] == 0
    assert result["exact_duplicate_count"] == 0
    assert result["near_duplicate_count"] == 0


def test_lookup_vendor_history_tool_accepts_alias_like_vendor_names():
    db = load_all()

    result = lookup_vendor_history_tool(
        db["vendor_history"],
        {"vendor_key": "Northwind Industrial Supplies Pvt Ltd"},
    )

    assert len(result["history"]) == 2
    assert "historical_bank_change_rejected" in result["derived_flags"]


def test_build_report_uses_deterministic_identity_for_local_baseline():
    report = benchmark_report.build_report(
        holdout_seeds=[101],
        variants_per_case=1,
    )

    protocol = report["evaluation_protocol"]
    assert protocol["agent_type"] == "deterministic-policy"
    assert protocol["model_name"] == benchmark_report.DETERMINISTIC_BASELINE_MODEL
