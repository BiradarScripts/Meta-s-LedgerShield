from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import normalize_id, normalize_text

BASE_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = BASE_DIR / "fixtures"


def load_json(name: str) -> Any:
    path = FIXTURE_DIR / name
    with path.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def _index_by(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        output[str(value)] = row
    return output


def _vendor_index(vendors: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for vendor in vendors:
        keys = {
            normalize_text(vendor.get("vendor_key")),
            normalize_text(vendor.get("canonical_name")),
            normalize_text(vendor.get("vendor_name")),
        }
        for key in keys:
            if key:
                output[key] = vendor
    return output


def _ledger_vendor_index(ledger_index: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {}
    for row in ledger_index:
        vendor_key = normalize_text(row.get("vendor_key"))
        output.setdefault(vendor_key, []).append(row)
    return output


def _case_index(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(case["case_id"]): case for case in cases if "case_id" in case}


def _case_defaults(case: dict[str, Any]) -> dict[str, Any]:
    cloned = dict(case)
    cloned.setdefault("budget_total", 15.0)
    cloned.setdefault("max_steps", 20)
    cloned.setdefault("difficulty", "medium")
    cloned.setdefault("documents", [])
    cloned.setdefault("gold", {})
    cloned.setdefault("task_label", cloned.get("task_type", ""))
    cloned.setdefault("initial_visible_doc_ids", [doc.get("doc_id") for doc in cloned.get("documents", []) if doc.get("doc_id")])
    return cloned


def load_all() -> dict[str, Any]:
    vendors = load_json("vendors.json")
    vendor_history = load_json("vendor_history.json")
    cases = [_case_defaults(case) for case in load_json("cases.json")]
    po_records = load_json("po_records.json")
    receipts = load_json("receipts.json")
    ledger_index = load_json("ledger_index.json")
    email_threads = load_json("email_threads.json")
    policy_rules = load_json("policy_rules.json")

    return {
        "vendors": vendors,
        "vendor_history": vendor_history,
        "cases": cases,
        "po_records": po_records,
        "receipts": receipts,
        "ledger_index": ledger_index,
        "email_threads": email_threads,
        "policy_rules": policy_rules,
        "cases_by_id": _case_index(cases),
        "vendors_by_key": _vendor_index(vendors),
        "po_by_id": _index_by(po_records, "po_id"),
        "receipt_by_id": _index_by(receipts, "receipt_id"),
        "thread_by_id": _index_by(email_threads, "thread_id"),
        "policy_by_id": _index_by(policy_rules, "rule_id"),
        "ledger_by_vendor": _ledger_vendor_index(ledger_index),
    }