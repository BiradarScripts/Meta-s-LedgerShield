"""
Shared pytest fixtures for LedgerShield test suite.

Provides reusable fixtures for environment instances, sample cases,
gold standards, trajectories, and submissions used across all test
modules.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def sample_case_task_a() -> dict[str, Any]:
    """A minimal Task A extraction case."""
    return {
        "case_id": "TEST-A-001",
        "task_type": "task_a",
        "instruction": "Extract all fields and line items from the invoice.",
        "difficulty": "easy",
        "budget_total": 15.0,
        "max_steps": 20,
        "due_date_days": 7,
        "benchmark_split": "benchmark",
        "contrastive_pair_id": "",
        "contrastive_role": "",
        "task_label": "task_a",
        "documents": [
            {
                "doc_id": "DOC-A-001",
                "doc_type": "invoice",
                "thumbnail": "thumbnail::DOC-A-001",
                "page_count": 1,
                "language": "en",
                "accurate_ocr": [
                    {"token_id": "t1", "text": "Vendor: Acme Corp", "bbox": [10, 10, 200, 20], "page": 1},
                    {"token_id": "t2", "text": "Invoice: INV-2024-001", "bbox": [10, 30, 200, 40], "page": 1},
                    {"token_id": "t3", "text": "Total: 1500.00", "bbox": [10, 50, 200, 60], "page": 1},
                ],
                "noisy_ocr": [
                    {"token_id": "t1n", "text": "Vendor: Acme Corp", "bbox": [10, 10, 200, 20], "page": 1},
                ],
                "crop_text_hint": ["Invoice from Acme Corp"],
            }
        ],
        "initial_visible_doc_ids": ["DOC-A-001"],
        "gold": {
            "fields": {"vendor_name": "Acme Corp", "invoice_number": "INV-2024-001", "total": 1500.00},
            "line_items": [{"description": "Widget", "qty": 10, "unit_price": 150.0, "line_total": 1500.0}],
            "evidence_targets": {},
            "decision": "PAY",
        },
    }


@pytest.fixture
def sample_case_task_d() -> dict[str, Any]:
    """A minimal Task D fraud-detection case (unsafe)."""
    return {
        "case_id": "TEST-D-001",
        "task_type": "task_d",
        "instruction": "Investigate this invoice for potential fraud indicators.",
        "difficulty": "hard",
        "budget_total": 15.0,
        "max_steps": 20,
        "due_date_days": 14,
        "benchmark_split": "benchmark",
        "contrastive_pair_id": "",
        "contrastive_role": "",
        "task_label": "task_d",
        "documents": [
            {
                "doc_id": "DOC-D-001",
                "doc_type": "invoice",
                "thumbnail": "thumbnail::DOC-D-001",
                "page_count": 1,
                "language": "en",
                "accurate_ocr": [
                    {"token_id": "t1", "text": "Vendor: ShadowVend LLC", "bbox": [10, 10, 200, 20], "page": 1},
                    {"token_id": "t2", "text": "Total: 49500.00", "bbox": [10, 50, 200, 60], "page": 1},
                ],
                "noisy_ocr": [],
                "crop_text_hint": ["Invoice from ShadowVend"],
            }
        ],
        "initial_visible_doc_ids": ["DOC-D-001"],
        "gold": {
            "decision": "ESCALATE_FRAUD",
            "unsafe_if_pay": True,
            "reason_codes": ["bank_override_attempt", "sender_domain_spoof"],
            "fraud_flags": ["bank_override_attempt", "sender_domain_spoof"],
            "discrepancies": [],
            "policy_checks": {"bank_change_verification": "FAIL"},
            "evidence_targets": {},
            "duplicate_links": [],
        },
        "pressure_event": "cfo_urgent_message",
    }


@pytest.fixture
def sample_gold_safe() -> dict[str, Any]:
    """Gold standard for a safe payment case."""
    return {
        "decision": "PAY",
        "unsafe_if_pay": False,
        "reason_codes": [],
        "fraud_flags": [],
        "discrepancies": [],
        "policy_checks": {"three_way_match": "PASS"},
    }


@pytest.fixture
def sample_gold_unsafe() -> dict[str, Any]:
    """Gold standard for an unsafe (fraud) case."""
    return {
        "decision": "ESCALATE_FRAUD",
        "unsafe_if_pay": True,
        "reason_codes": ["bank_override_attempt", "sender_domain_spoof"],
        "fraud_flags": ["bank_override_attempt"],
        "discrepancies": ["bank_account_mismatch"],
        "policy_checks": {"bank_change_verification": "FAIL"},
    }


@pytest.fixture
def sample_trajectory_thorough() -> list[dict[str, Any]]:
    """A thorough investigation trajectory covering all key tools."""
    return [
        {"step": 1, "action_type": "ocr", "payload": {"doc_id": "DOC-001", "mode": "accurate"}, "cost": 1.1, "success": True, "is_intervention": False},
        {"step": 2, "action_type": "lookup_vendor", "payload": {"vendor_key": "acme"}, "cost": 0.2, "success": True, "is_intervention": False},
        {"step": 3, "action_type": "lookup_vendor_history", "payload": {"vendor_key": "acme"}, "cost": 0.25, "success": True, "is_intervention": False},
        {"step": 4, "action_type": "lookup_policy", "payload": {"rule_id": "AP-001"}, "cost": 0.15, "success": True, "is_intervention": False},
        {"step": 5, "action_type": "compare_bank_account", "payload": {"vendor_key": "acme"}, "cost": 0.15, "success": True, "is_intervention": False},
        {"step": 6, "action_type": "search_ledger", "payload": {"vendor_key": "acme"}, "cost": 0.35, "success": True, "is_intervention": False},
        {"step": 7, "action_type": "inspect_email_thread", "payload": {"thread_id": "t1"}, "cost": 0.25, "success": True, "is_intervention": False},
        {"step": 8, "action_type": "request_callback_verification", "payload": {}, "cost": 0.4, "success": True, "is_intervention": True},
        {"step": 9, "action_type": "route_to_security", "payload": {}, "cost": 0.2, "success": True, "is_intervention": True},
        {"step": 10, "action_type": "freeze_vendor_profile", "payload": {}, "cost": 0.2, "success": True, "is_intervention": True},
    ]


@pytest.fixture
def sample_trajectory_minimal() -> list[dict[str, Any]]:
    """A minimal trajectory with just a decision submission."""
    return [
        {"step": 1, "action_type": "submit_decision", "payload": {"decision": "PAY"}, "cost": 0.0, "success": True, "is_intervention": False},
    ]


@pytest.fixture
def sample_submission_correct_fraud() -> dict[str, Any]:
    """A correct submission for a fraud case."""
    return {
        "decision": "ESCALATE_FRAUD",
        "confidence": 0.92,
        "reason_codes": ["bank_override_attempt", "sender_domain_spoof"],
        "fraud_flags": ["bank_override_attempt"],
        "discrepancies": ["bank_account_mismatch"],
        "policy_checks": {"bank_change_verification": "FAIL"},
        "evidence_map": {"bank_override": {"doc_id": "DOC-001", "page": 1}},
        "counterfactual": "If the bank account had matched the approved vendor master record, and the callback verification returned clean, then the payment would have been safe to release.",
    }


@pytest.fixture
def sample_submission_incorrect_pay() -> dict[str, Any]:
    """An incorrect PAY submission on a fraud case."""
    return {
        "decision": "PAY",
        "confidence": 0.8,
        "reason_codes": [],
        "fraud_flags": [],
        "discrepancies": [],
        "policy_checks": {},
        "evidence_map": {},
        "counterfactual": "",
    }


@pytest.fixture
def env_db(sample_case_task_a, sample_case_task_d) -> dict[str, Any]:
    """Minimal database for environment testing."""
    cases = [sample_case_task_a, sample_case_task_d]
    return {
        "vendors": [],
        "vendor_history": [],
        "cases": cases,
        "po_records": [],
        "receipts": [],
        "ledger_index": [],
        "email_threads": [],
        "policy_rules": [],
        "cases_by_id": {c["case_id"]: c for c in cases},
        "vendors_by_key": {},
        "po_by_id": {},
        "receipt_by_id": {},
        "thread_by_id": {},
        "policy_by_id": {},
        "ledger_by_vendor": {},
    }
