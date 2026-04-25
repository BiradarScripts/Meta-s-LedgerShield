from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .benchmark_contract import ensure_case_contract_fields
from .case_factory import generate_benign_twin, generate_case_batch, generate_controlbench_sequence, generate_holdout_suite
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
    cloned = ensure_case_contract_fields(case)
    cloned.setdefault("budget_total", 15.0)
    cloned.setdefault("max_steps", 20)
    cloned.setdefault("difficulty", "medium")
    difficulty = normalize_text(cloned.get("difficulty"))
    if "due_date_days" not in cloned:
        if difficulty == "easy":
            cloned["due_date_days"] = 3
        elif difficulty in {"hard", "expert"}:
            cloned["due_date_days"] = 30
        else:
            cloned["due_date_days"] = 14
    cloned.setdefault("documents", [])
    cloned.setdefault("gold", {})
    cloned.setdefault("task_label", cloned.get("task_type", ""))
    cloned.setdefault("contrastive_pair_id", "")
    cloned.setdefault("contrastive_role", "")
    cloned.setdefault("initial_visible_doc_ids", [doc.get("doc_id") for doc in cloned.get("documents", []) if doc.get("doc_id")])
    return cloned


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return normalize_text(value) in {"1", "true", "yes", "on"}


def load_all() -> dict[str, Any]:
    vendors = load_json("vendors.json")
    vendors_by_key = _vendor_index(vendors)
    vendor_history = load_json("vendor_history.json")
    base_cases = [_case_defaults(case) for case in load_json("cases.json")]
    hard_cases = [case for case in base_cases if normalize_text(case.get("task_type")) in {"task_c", "task_d", "task_e"}]
    include_challenge = _env_flag("LEDGERSHIELD_INCLUDE_CHALLENGE", True)
    include_holdout = _env_flag("LEDGERSHIELD_INCLUDE_HOLDOUT", False)
    include_twins = _env_flag("LEDGERSHIELD_INCLUDE_TWINS", False)
    include_controlbench = _env_flag("LEDGERSHIELD_INCLUDE_CONTROLBENCH", False)
    challenge_variants = max(0, int(os.getenv("LEDGERSHIELD_CHALLENGE_VARIANTS", "2") or 2))
    challenge_seed = int(os.getenv("LEDGERSHIELD_CHALLENGE_SEED", "2026") or 2026)
    holdout_variants = max(0, int(os.getenv("LEDGERSHIELD_HOLDOUT_VARIANTS", "1") or 1))
    holdout_seed = int(os.getenv("LEDGERSHIELD_HOLDOUT_SEED", "31415") or 31415)
    controlbench_length = max(0, int(os.getenv("LEDGERSHIELD_CONTROLBENCH_CASES", "100") or 100))
    controlbench_seed = int(os.getenv("LEDGERSHIELD_CONTROLBENCH_SEED", "2026") or 2026)
    controlbench_sleepers = max(0, int(os.getenv("LEDGERSHIELD_CONTROLBENCH_SLEEPERS", "3") or 3))
    controlbench_sleeper_warmups = max(0, int(os.getenv("LEDGERSHIELD_CONTROLBENCH_SLEEPER_WARMUPS", "3") or 3))

    cases = list(base_cases)
    if include_challenge and hard_cases and challenge_variants > 0:
        challenge_cases = generate_case_batch(
            base_cases=hard_cases,
            variants_per_case=challenge_variants,
            seed=challenge_seed,
            split="challenge",
        )
        cases.extend(_case_defaults(case) for case in challenge_cases)

    if include_holdout and hard_cases and holdout_variants > 0:
        holdout_cases = generate_holdout_suite(
            base_cases=hard_cases,
            variants_per_case=holdout_variants,
            seed=holdout_seed,
        )
        cases.extend(_case_defaults(case) for case in holdout_cases)

    if include_twins:
        for idx, case in enumerate(base_cases):
            gold = case.get("gold", {}) or {}
            if normalize_text(case.get("task_type")) not in {"task_d", "task_e"} or not gold.get("unsafe_if_pay"):
                continue
            approved_bank_account = None
            for vendor_key_candidate in {
                normalize_text(case.get("vendor_key")),
                normalize_text(gold.get("vendor_key")),
            }:
                if vendor_key_candidate and vendor_key_candidate in vendors_by_key:
                    approved_bank_account = vendors_by_key[vendor_key_candidate].get("bank_account")
                    break
            twin = generate_benign_twin(case, seed=holdout_seed + idx, approved_bank_account=approved_bank_account)
            cases.append(_case_defaults(twin))

    if include_controlbench and controlbench_length > 0:
        controlbench_cases = generate_controlbench_sequence(
            base_cases=base_cases,
            sequence_length=controlbench_length,
            seed=controlbench_seed,
            sleeper_count=controlbench_sleepers,
            sleeper_warmup_cases=controlbench_sleeper_warmups,
        )
        cases.extend(_case_defaults(case) for case in controlbench_cases)

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
        "vendors_by_key": vendors_by_key,
        "po_by_id": _index_by(po_records, "po_id"),
        "receipt_by_id": _index_by(receipts, "receipt_id"),
        "thread_by_id": _index_by(email_threads, "thread_id"),
        "policy_by_id": _index_by(policy_rules, "rule_id"),
        "ledger_by_vendor": _ledger_vendor_index(ledger_index),
    }
