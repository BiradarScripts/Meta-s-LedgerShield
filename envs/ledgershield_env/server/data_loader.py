from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = BASE_DIR / "fixtures"


def load_json(name: str) -> Any:
    path = FIXTURE_DIR / name
    with path.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def load_all() -> dict[str, Any]:
    return {
        "vendors": load_json("vendors.json"),
        "vendor_history": load_json("vendor_history.json"),
        "cases": load_json("cases.json"),
        "po_records": load_json("po_records.json"),
        "receipts": load_json("receipts.json"),
        "ledger_index": load_json("ledger_index.json"),
        "email_threads": load_json("email_threads.json"),
        "policy_rules": load_json("policy_rules.json"),
    }
