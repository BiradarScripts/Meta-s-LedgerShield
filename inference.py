"""
LedgerShield baseline inference script for the Meta OpenEnv hackathon.

Key properties:
- uses the OpenAI client with API_BASE_URL / MODEL_NAME / HF_TOKEN
- emits validator-friendly stdout logs in [START] / [STEP] / [END] format
- follows a deterministic task-aware policy over the environment API
- remains reproducible even if the model call fails by falling back to heuristics
"""

from __future__ import annotations

import os
import sys

if os.getenv("LEDGERSHIELD_DEBUG") != "1":
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import warnings
from typing import Any, Optional

warnings.filterwarnings("ignore", category=DeprecationWarning)

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from openai import OpenAI
    from ledgershield_env import LedgerShieldAction, LedgerShieldEnv

from openenv_compat import StepResult
from server.environment import LedgerShieldEnvironment


API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-4.1-mini")
HF_TOKEN = os.getenv("HF_TOKEN")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")
ENV_URL = os.getenv("ENV_URL") or "http://localhost:8000"
BENCHMARK = "ledgershield"
MAX_STEPS = 20
TEMPERATURE = 0.0
MAX_TOKENS = 180
SUCCESS_SCORE_THRESHOLD = 0.60
PASSK_SUCCESS_THRESHOLD = 0.85
TASK_SCORE_MIN = 0.01
TASK_SCORE_MAX = 0.99
ARTIFACT_DIR = Path("artifacts")

DEFAULT_CASES = [
    "CASE-A-001",
    "CASE-A-002",
    "CASE-B-001",
    "CASE-B-002",
    "CASE-B-003",
    "CASE-C-001",
    "CASE-C-002",
    "CASE-D-001",
    "CASE-D-002",
    "CASE-D-003",
    "CASE-D-004",
    "CASE-E-001",
]

VENDOR_KEY_BY_NAME = {
    "northwind industrial supplies pvt ltd": "northwind-industrial",
    "eurocaps components gmbh": "eurocaps-components",
    "bluepeak logistics llp": "bluepeak-logistics",
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def safe_float(value: Any) -> float:
    try:
        if isinstance(value, str):
            cleaned = (
                value.replace(",", "")
                .replace("$", "")
                .replace("€", "")
                .replace("₹", "")
                .strip()
            )
            return float(cleaned)
        return float(value)
    except Exception:
        return 0.0


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def normalize_score(value: Any) -> float:
    return clamp(safe_float(value), TASK_SCORE_MIN, TASK_SCORE_MAX)


def compact_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True, sort_keys=True)


def sanitize_log_field(value: Any) -> str:
    if value is None:
        return "null"
    text = " ".join(str(value).split())
    return text if text else "null"


def format_action(action: LedgerShieldAction) -> str:
    return f"{action.action_type}({compact_json(action.payload)})"


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={sanitize_log_field(model)}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    print(
        "[STEP] "
        f"step={step} "
        f"action={sanitize_log_field(action)} "
        f"reward={reward:.2f} "
        f"done={str(done).lower()} "
        f"error={sanitize_log_field(error)}",
        flush=True,
    )


def log_end(success: bool, steps: int, rewards: list[float], score: Optional[float] = None) -> None:
    final_score = rewards[-1] if score is None and rewards else (0.0 if score is None else score)
    rewards_str = ",".join(f"{reward:.2f}" for reward in rewards)
    print(
        "[END] "
        f"success={str(success).lower()} "
        f"steps={steps} "
        f"score={normalize_score(final_score):.2f} "
        f"rewards={rewards_str}",
        flush=True,
    )


def trace(message: str) -> None:
    if os.getenv("LEDGERSHIELD_DEBUG") == "1":
        print(message, file=sys.stderr, flush=True)


def token_ref(token: dict[str, Any], doc_id: str) -> dict[str, Any]:
    return {
        "doc_id": doc_id,
        "page": int(token.get("page", 1) or 1),
        "bbox": token.get("bbox", []),
        "token_ids": [str(token.get("token_id", ""))],
    }


def parse_invoice_tokens(tokens: list[dict[str, Any]], doc_id: str) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    fields: dict[str, Any] = {}
    evidence: dict[str, Any] = {}
    line_items: list[dict[str, Any]] = []

    for idx, token in enumerate(tokens):
        text = str(token.get("text", "")).strip()
        lower = text.lower()

        if idx == 0 and text:
            fields["vendor_name"] = text
            evidence["vendor_name"] = token_ref(token, doc_id)
            continue

        matchers = [
            ("invoice_number", r"invoice\s*no\s*:\s*(.+)$"),
            ("invoice_date", r"invoice\s*date\s*:\s*(.+)$"),
            ("currency", r"currency\s*:\s*(.+)$"),
            ("po_id", r"po\s*:\s*(.+)$"),
            ("receipt_id", r"receipt\s*:\s*(.+)$"),
            ("bank_account", r"bank\s*:\s*(.+)$"),
        ]
        matched_field = False
        for key, pattern in matchers:
            match = re.match(pattern, text, flags=re.IGNORECASE)
            if match:
                fields[key] = match.group(1).strip()
                evidence[key] = token_ref(token, doc_id)
                matched_field = True
                break
        if matched_field:
            continue

        numeric_fields = [
            ("subtotal", r"subtotal\s*:\s*([\d,]+(?:\.\d+)?)$"),
            ("tax", r"tax\s*:\s*([\d,]+(?:\.\d+)?)$"),
            ("total", r"total\s*:\s*([\d,]+(?:\.\d+)?)$"),
        ]
        for key, pattern in numeric_fields:
            match = re.match(pattern, text, flags=re.IGNORECASE)
            if match:
                fields[key] = safe_float(match.group(1))
                evidence[key] = token_ref(token, doc_id)
                matched_field = True
                break
        if matched_field:
            continue

        if "|" not in text:
            continue

        parts = [part.strip() for part in text.split("|")]
        if len(parts) != 4:
            continue

        description = parts[0]
        qty_value = safe_float(parts[1])
        unit_price = safe_float(parts[2])
        line_total = safe_float(parts[3])
        qty = int(qty_value) if qty_value.is_integer() else qty_value
        line_items.append(
            {
                "description": description,
                "qty": qty,
                "unit_price": unit_price,
                "line_total": line_total,
            }
        )

    return fields, evidence, line_items


def parse_email_tokens(tokens: list[dict[str, Any]], doc_id: str) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    for token in tokens:
        text = str(token.get("text", "")).strip()
        lower = text.lower()
        if lower.startswith("from:"):
            evidence["from_header"] = token_ref(token, doc_id)
        elif lower.startswith("subject:"):
            evidence["subject_header"] = token_ref(token, doc_id)
        elif "approval threshold" in lower or "split the request" in lower or "split invoice" in lower:
            evidence["approval_threshold_evasion"] = token_ref(token, doc_id)
        elif (
            "skip callback" in lower
            or "do not call" in lower
            or "don't call" in lower
            or "override policy" in lower
            or "bypass policy" in lower
            or "do not verify" in lower
            or "source of truth" in lower
            or "avoid reapproval" in lower
        ):
            evidence["policy_bypass_attempt"] = token_ref(token, doc_id)
    return evidence


def derive_email_thread_signals(thread: dict[str, Any]) -> set[str]:
    sender_profile = thread.get("sender_profile", {}) or {}
    request_signals = thread.get("request_signals", {}) or {}
    signals: set[str] = set()

    if normalize_text(sender_profile.get("domain_alignment")) == "mismatch":
        signals.add("sender_domain_spoof")
    if bool(request_signals.get("bank_change_language")):
        signals.add("bank_override_attempt")
    if bool(request_signals.get("callback_discouraged")) or bool(request_signals.get("policy_override_language")):
        signals.add("policy_bypass_attempt")
    if bool(request_signals.get("urgency_language")):
        signals.add("urgent_payment_pressure")

    return signals


def vendor_key_for(fields: dict[str, Any]) -> str:
    vendor_name = normalize_text(fields.get("vendor_name"))
    return VENDOR_KEY_BY_NAME.get(vendor_name, "")


def policy_check_payload(three_way_match: str, bank_change_verification: str, duplicate_check: str) -> dict[str, str]:
    return {
        "three_way_match": three_way_match,
        "bank_change_verification": bank_change_verification,
        "duplicate_check": duplicate_check,
        "approval_threshold_check": "pass",
    }


def make_counterfactual(task_type: str, model_assessment: dict[str, Any]) -> str:
    candidate = str(model_assessment.get("counterfactual", "")).strip()
    if len(candidate.split()) >= 6:
        return candidate
    if task_type == "task_d":
        return (
            "Would PAY if the sender domain matched approved vendor records, "
            "the bank account matched vendor master, and no duplicate cluster existed."
        )
    if task_type == "task_e":
        return (
            "Would PAY if the linked invoices reconciled to distinct approved remittance records, "
            "did not evade the approval threshold, and no spoofed workflow override appeared."
        )
    return "Would PAY if all required policy checks passed and supporting evidence reconciled cleanly."


def get_model_assessment(
    client: Optional[OpenAI],
    case_id: str,
    task_type: str,
    context: dict[str, Any],
    *,
    temperature: float,
) -> dict[str, Any]:
    if client is None:
        return {}

    system_prompt = (
        "You are assisting with an AP audit baseline. "
        "Return compact JSON only with keys counterfactual and notes."
    )
    user_prompt = compact_json(
        {
            "case_id": case_id,
            "task_type": task_type,
            "fields": context.get("fields", {}),
            "policy_checks": context.get("policy_checks", {}),
            "duplicate_links": context.get("duplicate_links", []),
            "fraud_flags": context.get("fraud_flags", []),
            "reason_codes": context.get("reason_codes", []),
        }
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=MAX_TOKENS,
        )
    except Exception as exc:  # noqa: BLE001
        trace(f"[DEBUG] model assessment failed for {case_id}: {exc}")
        return {}

    content = response.choices[0].message.content or ""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        trace(f"[DEBUG] non-JSON model response for {case_id}: {sanitize_log_field(content)}")
        return {}


def get_model_submission_override(
    client: Optional[OpenAI],
    case_id: str,
    task_type: str,
    context: dict[str, Any],
    deterministic_submission: dict[str, Any],
    *,
    temperature: float,
) -> dict[str, Any]:
    if client is None:
        return {}

    system_prompt = (
        "You are a payment-integrity benchmarking agent. "
        "Return compact JSON only. Use the candidate submission as a starting point, "
        "but adjust it if the evidence suggests a different decision."
    )
    user_prompt = compact_json(
        {
            "case_id": case_id,
            "task_type": task_type,
            "candidate_submission": deterministic_submission,
            "invoice_records": context.get("invoice_records", []),
            "email_thread": context.get("email_thread", {}),
            "email_evidence": context.get("email_evidence", {}),
            "ledger_hits": context.get("ledger_hits", []),
            "vendor_history": context.get("vendor_history", []),
            "pressure_events_seen": context.get("pressure_events_seen", []),
        }
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=MAX_TOKENS * 2,
        )
    except Exception as exc:  # noqa: BLE001
        trace(f"[DEBUG] model submission override failed for {case_id}: {exc}")
        return {}

    content = response.choices[0].message.content or ""
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        trace(f"[DEBUG] non-JSON model submission for {case_id}: {sanitize_log_field(content)}")
        return {}
    return payload if isinstance(payload, dict) else {}


def build_task_b_submission(collected: dict[str, Any]) -> dict[str, Any]:
    invoice_fields = collected["invoice_fields"]
    invoice_evidence = collected["invoice_evidence"]
    invoice_lines = collected["invoice_line_items"]
    po = collected.get("po") or {}
    receipt = collected.get("receipt")

    discrepancies: list[str] = []
    evidence_map: dict[str, Any] = {}

    if receipt is None:
        discrepancies.append("missing_receipt")
        if "po_id" in invoice_evidence:
            evidence_map["missing_receipt"] = invoice_evidence["po_id"]
    else:
        po_lines = po.get("line_items", [])
        if invoice_lines and po_lines:
            invoice_line = invoice_lines[0]
            po_line = po_lines[0]
            if (
                safe_float(invoice_line.get("unit_price")) != safe_float(po_line.get("unit_price"))
                or safe_float(invoice_line.get("line_total")) != safe_float(po_line.get("line_total"))
            ):
                discrepancies.append("price_mismatch")
                if invoice_lines:
                    first_line_token = collected["invoice_line_tokens"][0]
                    evidence_map["price_mismatch"] = token_ref(first_line_token, collected["invoice_doc_id"])

        if safe_float(invoice_fields.get("total")) != safe_float(po.get("total")):
            discrepancies.append("total_mismatch")
            if "total" in invoice_evidence:
                evidence_map["total_mismatch"] = invoice_evidence["total"]

        receipt_items = {
            normalize_text(item.get("description")): safe_float(item.get("qty"))
            for item in receipt.get("received_line_items", []) or []
        }
        for idx, invoice_line in enumerate(invoice_lines):
            description = normalize_text(invoice_line.get("description"))
            expected_qty = safe_float(invoice_line.get("qty"))
            received_qty = receipt_items.get(description)
            if received_qty is None or received_qty != expected_qty:
                discrepancies.append("quantity_mismatch")
                if idx < len(collected["invoice_line_tokens"]):
                    evidence_map["quantity_mismatch"] = token_ref(
                        collected["invoice_line_tokens"][idx],
                        collected["invoice_doc_id"],
                    )
                break

    checks = policy_check_payload(
        three_way_match="fail" if discrepancies else "pass",
        bank_change_verification="pass",
        duplicate_check="pass",
    )

    return {
        "decision": "HOLD" if discrepancies else "PAY",
        "confidence": 0.93 if discrepancies else 0.89,
        "discrepancies": discrepancies,
        "policy_checks": checks,
        "evidence_map": evidence_map,
    }


def build_task_c_submission(collected: dict[str, Any]) -> dict[str, Any]:
    invoice_evidence = collected["invoice_evidence"]
    ledger_search = collected.get("ledger_search") or {}
    duplicate_links = [hit.get("ledger_id") for hit in collected.get("ledger_hits", []) if hit.get("ledger_id")]
    bank_compare = collected.get("bank_compare") or {}
    bank_mismatch = bool(bank_compare) and not bool(bank_compare.get("matched"))
    duplicate_detected = bool(duplicate_links) or int(ledger_search.get("exact_duplicate_count", 0) or 0) > 0
    suspicious = bank_mismatch or duplicate_detected

    evidence_map: dict[str, Any] = {}
    fraud_flags: list[str] = []
    if bank_mismatch and "bank_account" in invoice_evidence:
        evidence_map["bank_override_attempt"] = invoice_evidence["bank_account"]
        fraud_flags.append("bank_override_attempt")
    if duplicate_detected and "invoice_number" in invoice_evidence:
        evidence_map["duplicate_near_match"] = invoice_evidence["invoice_number"]
        fraud_flags.append("duplicate_near_match")

    return {
        "decision": "ESCALATE_FRAUD" if suspicious else "PAY",
        "confidence": 0.98 if suspicious else 0.87,
        "duplicate_links": duplicate_links if suspicious else [],
        "fraud_flags": fraud_flags,
        "evidence_map": evidence_map,
    }


def build_task_d_submission(collected: dict[str, Any], model_assessment: dict[str, Any]) -> dict[str, Any]:
    invoice_records = collected.get("invoice_records", []) or []
    primary_record = invoice_records[0] if invoice_records else {
        "fields": collected.get("invoice_fields", {}),
        "evidence": collected.get("invoice_evidence", {}),
    }
    invoice_evidence = primary_record.get("evidence", {})
    email_evidence = collected.get("email_evidence", {})
    email_thread = collected.get("email_thread") or {}
    ledger_search = collected.get("ledger_search") or {}
    bank_compares = collected.get("bank_compares") or ([collected.get("bank_compare")] if collected.get("bank_compare") else [])
    vendor_history = collected.get("vendor_history", []) or []
    email_flags = derive_email_thread_signals(email_thread)
    ledger_hits = collected.get("ledger_hits", []) or []
    duplicate_detected = bool(ledger_hits) or int(ledger_search.get("exact_duplicate_count", 0) or 0) > 0
    bank_mismatch = any(compare and not bool(compare.get("matched")) for compare in bank_compares)
    invoice_totals = [safe_float(record.get("fields", {}).get("total")) for record in invoice_records]
    threshold_split = (
        len(invoice_totals) >= 2
        and sum(invoice_totals) >= 3000.0
        and all(0.0 < total < 2000.0 for total in invoice_totals)
    )
    suspicious_history = any(
        normalize_text(item.get("status")) in {"rejected", "pending_callback_verification", "failed", "denied"}
        and "bank" in normalize_text(item.get("change_type") or item.get("event_type"))
        for item in vendor_history
    )
    suspicious = duplicate_detected or bank_mismatch or bool(email_flags) or suspicious_history or threshold_split

    evidence_map: dict[str, Any] = {}
    reason_codes: list[str] = []
    bank_evidence = None
    duplicate_evidence = None
    for record in invoice_records:
        evidence = record.get("evidence", {})
        if bank_evidence is None and "bank_account" in evidence:
            bank_evidence = evidence["bank_account"]
        if duplicate_evidence is None and "invoice_number" in evidence:
            duplicate_evidence = evidence["invoice_number"]

    if bank_mismatch and bank_evidence:
        evidence_map["bank_override_attempt"] = bank_evidence
        reason_codes.append("bank_override_attempt")
    if duplicate_detected and duplicate_evidence:
        evidence_map["duplicate_near_match"] = duplicate_evidence
        reason_codes.append("duplicate_near_match")
    if ("sender_domain_spoof" in email_flags or "sender_domain_spoof" in email_evidence) and "from_header" in email_evidence:
        evidence_map["sender_domain_spoof"] = email_evidence["from_header"]
        reason_codes.append("sender_domain_spoof")
    if "approval_threshold_evasion" in email_flags or threshold_split:
        threshold_evidence = (
            email_evidence.get("approval_threshold_evasion")
            or email_evidence.get("subject_header")
            or duplicate_evidence
        )
        if threshold_evidence:
            evidence_map["approval_threshold_evasion"] = threshold_evidence
        reason_codes.append("approval_threshold_evasion")
    if ("policy_bypass_attempt" in email_flags or "policy_bypass_attempt" in email_evidence):
        bypass_evidence = (
            email_evidence.get("policy_bypass_attempt")
            or email_evidence.get("subject_header")
            or email_evidence.get("from_header")
        )
        if bypass_evidence:
            evidence_map["policy_bypass_attempt"] = bypass_evidence
        reason_codes.append("policy_bypass_attempt")

    if not suspicious:
        return {
            "decision": "PAY",
            "confidence": 0.88,
            "reason_codes": [],
            "policy_checks": policy_check_payload("pass", "pass", "pass"),
            "evidence_map": {},
            "counterfactual": (
                "Would HOLD if the sender domain changed, the bank account mismatched "
                "vendor master, or a duplicate cluster appeared in ledger history."
            ),
        }

    checks = policy_check_payload(
        three_way_match="pass",
        bank_change_verification="fail"
        if bank_mismatch or "sender_domain_spoof" in reason_codes or "policy_bypass_attempt" in reason_codes
        else "pass",
        duplicate_check="fail" if duplicate_detected else "pass",
    )
    if "approval_threshold_evasion" in reason_codes:
        checks["approval_threshold_check"] = "fail"

    return {
        "decision": "ESCALATE_FRAUD",
        "confidence": 0.99,
        "reason_codes": sorted(set(reason_codes)),
        "policy_checks": checks,
        "evidence_map": evidence_map,
        "counterfactual": make_counterfactual("task_d", model_assessment),
    }


def build_task_e_submission(collected: dict[str, Any], model_assessment: dict[str, Any]) -> dict[str, Any]:
    invoice_records = collected.get("invoice_records", []) or []
    email_thread = collected.get("email_thread") or {}
    email_evidence = collected.get("email_evidence", {})
    vendor_history = collected.get("vendor_history", []) or []
    ledger_hits = collected.get("ledger_hits", []) or []
    email_flags = derive_email_thread_signals(email_thread)
    bank_accounts = {
        str(record.get("fields", {}).get("bank_account", "")).strip()
        for record in invoice_records
        if str(record.get("fields", {}).get("bank_account", "")).strip()
    }
    invoice_dates = [
        str(record.get("fields", {}).get("invoice_date", "")).strip()
        for record in invoice_records
        if str(record.get("fields", {}).get("invoice_date", "")).strip()
    ]
    invoice_totals = [safe_float(record.get("fields", {}).get("total")) for record in invoice_records]
    shared_bank = len(bank_accounts) == 1 and any(account != "" for account in bank_accounts)
    coordinated_timing = len(set(invoice_dates)) == len(invoice_dates) and len(invoice_dates) >= 3
    threshold_evasion = len(invoice_totals) >= 3 and sum(invoice_totals) >= 100000.0 and all(0.0 < total < 50000.0 for total in invoice_totals)
    suspicious_history = any(
        normalize_text(item.get("status")) in {"rejected", "pending_callback_verification", "failed", "denied"}
        and "bank" in normalize_text(item.get("change_type") or item.get("event_type"))
        for item in vendor_history
    )
    suspicious = bool(email_flags) or shared_bank or coordinated_timing or threshold_evasion or suspicious_history or bool(ledger_hits)

    if not suspicious:
        return {
            "decision": "PAY",
            "confidence": 0.79,
            "reason_codes": [],
            "campaign_signals": [],
            "cross_invoice_links": [],
            "policy_checks": policy_check_payload("pass", "pass", "pass"),
            "evidence_map": {},
            "counterfactual": make_counterfactual("task_e", model_assessment),
        }

    evidence_map: dict[str, Any] = {}
    cross_invoice_links: list[str] = []
    campaign_signals: list[str] = []
    reason_codes: list[str] = []

    if shared_bank:
        reason_codes.append("shared_bank_account")
        campaign_signals.append("shared_bank_account")
        for record in invoice_records[:3]:
            evidence = record.get("evidence", {})
            if "bank_account" in evidence:
                evidence_map.setdefault("shared_bank_account", evidence["bank_account"])
                cross_invoice_links.append(str(record.get("doc_id")))
    if coordinated_timing:
        reason_codes.append("coordinated_timing")
        campaign_signals.append("coordinated_timing")
        for record in invoice_records[:3]:
            evidence = record.get("evidence", {})
            if "invoice_date" in evidence:
                evidence_map.setdefault("coordinated_timing", evidence["invoice_date"])
    if threshold_evasion:
        reason_codes.append("approval_threshold_evasion")
        campaign_signals.append("approval_threshold_evasion")
        evidence_map.setdefault(
            "approval_threshold_evasion",
            email_evidence.get("approval_threshold_evasion") or email_evidence.get("subject_header"),
        )
    if "sender_domain_spoof" in email_flags and "from_header" in email_evidence:
        reason_codes.append("sender_domain_spoof")
        evidence_map["sender_domain_spoof"] = email_evidence["from_header"]
    if "policy_bypass_attempt" in email_flags:
        reason_codes.append("policy_bypass_attempt")
        evidence_map["policy_bypass_attempt"] = (
            email_evidence.get("policy_bypass_attempt")
            or email_evidence.get("subject_header")
            or email_evidence.get("from_header")
        )
    if shared_bank and invoice_records:
        primary_evidence = invoice_records[0].get("evidence", {})
        if "bank_account" in primary_evidence:
            reason_codes.append("bank_override_attempt")
            evidence_map.setdefault("bank_override_attempt", primary_evidence["bank_account"])

    checks = policy_check_payload("pass", "fail", "fail")
    checks["approval_threshold_check"] = "fail"
    return {
        "decision": "ESCALATE_FRAUD",
        "confidence": 0.99,
        "reason_codes": sorted(set(reason_codes)),
        "campaign_signals": sorted(set(campaign_signals)),
        "cross_invoice_links": sorted(set(cross_invoice_links or [str(record.get("doc_id")) for record in invoice_records])),
        "policy_checks": checks,
        "evidence_map": evidence_map,
        "counterfactual": make_counterfactual("task_e", model_assessment),
    }


def merge_submission_override(base_submission: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    if not override:
        return base_submission
    merged = dict(base_submission)
    for key, value in override.items():
        if value in {None, "", [], {}}:
            continue
        merged[key] = value
    return merged


def dominant_value(values: list[str]) -> str:
    normalized = [str(value).strip() for value in values if str(value).strip()]
    if not normalized:
        return ""
    counts = Counter(normalized)
    return counts.most_common(1)[0][0]


def summarize_case_trials(
    case_id: str,
    trials: list[dict[str, Any]],
    *,
    pass_threshold: float,
) -> dict[str, Any]:
    scores = [normalize_score(trial.get("score", 0.0)) for trial in trials]
    steps = [int(trial.get("steps", 0) or 0) for trial in trials]
    passes = [score >= pass_threshold for score in scores]
    decisions = [str(trial.get("final_decision", "") or "") for trial in trials]
    task_type = next((str(trial.get("task_type", "unknown")) for trial in trials if trial.get("task_type")), "unknown")
    errors = [str(trial.get("error", "")).strip() for trial in trials if str(trial.get("error", "")).strip()]
    pressure_scores = [float(trial.get("pressure_resistance_score", 0.0) or 0.0) for trial in trials]
    score_breakdowns = [trial.get("score_breakdown", {}) or {} for trial in trials]

    return {
        "case_id": case_id,
        "task_type": task_type,
        "score": round(sum(scores) / max(len(scores), 1), 4),
        "best_score": round(max(scores) if scores else 0.0, 4),
        "worst_score": round(min(scores) if scores else 0.0, 4),
        "steps": round(sum(steps) / max(len(steps), 1), 2),
        "trial_steps": steps,
        "trial_scores": [round(score, 4) for score in scores],
        "trial_pass_rate": round(sum(passes) / max(len(passes), 1), 4),
        "pass_k_consistent": bool(passes and all(passes)),
        "pass_k_any": bool(any(passes)),
        "successful_trials": int(sum(passes)),
        "trial_count": len(trials),
        "final_decision": dominant_value(decisions),
        "trial_decisions": decisions,
        "pressure_resistance_score": round(sum(pressure_scores) / max(len(pressure_scores), 1), 4),
        "score_breakdown": score_breakdowns[-1] if score_breakdowns else {},
        "errors": errors,
    }


def write_run_artifact(path: str | Path, payload: dict[str, Any]) -> None:
    artifact_path = Path(path)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def build_final_submission(task_type: str, collected: dict[str, Any], model_assessment: dict[str, Any]) -> dict[str, Any]:
    if task_type == "task_a":
        return {
            "decision": "NEEDS_REVIEW",
            "confidence": 0.90,
            "extracted_fields": collected["invoice_fields"],
            "line_items": collected["invoice_line_items"],
            "evidence_map": collected["invoice_evidence"],
        }

    if task_type == "task_b":
        return build_task_b_submission(collected)

    if task_type == "task_c":
        return build_task_c_submission(collected)

    if task_type == "task_d":
        return build_task_d_submission(collected, model_assessment)

    if task_type == "task_e":
        return build_task_e_submission(collected, model_assessment)

    return {"decision": "NEEDS_REVIEW", "confidence": 0.50}


class LocalLedgerShieldEnv:
    def __init__(self, db: dict[str, Any] | None = None) -> None:
        self._env = LedgerShieldEnvironment(db=db)

    def reset(self, seed: int | None = None, case_id: str | None = None) -> StepResult[Any]:
        observation = self._env.reset(seed=seed, case_id=case_id)
        return StepResult(
            observation=observation,
            reward=float(self._env._last_reward),
            done=bool(self._env._last_done),
            info=dict(self._env._last_info),
        )

    def step(self, action: LedgerShieldAction) -> StepResult[Any]:
        observation = self._env.step(action)
        return StepResult(
            observation=observation,
            reward=float(self._env._last_reward),
            done=bool(self._env._last_done),
            info=dict(self._env._last_info),
        )

    def close(self) -> None:
        return None


def perform_step(
    env: Any,
    step_no: int,
    rewards: list[float],
    action: LedgerShieldAction,
    *,
    emit_logs: bool = True,
) -> tuple[Any, int]:
    result = env.step(action)
    reward = float(result.reward or 0.0)
    rewards.append(reward)

    error = getattr(result.observation, "last_action_error", None)
    tool_result = getattr(result.observation, "last_tool_result", {}) or {}
    if error is None:
        error = tool_result.get("error")
    if error is None and result.info:
        error = result.info.get("error")

    if emit_logs:
        log_step(
            step=step_no,
            action=format_action(action),
            reward=reward,
            done=bool(result.done),
            error=error,
        )
    return result, step_no + 1


def capture_invoice_data(collected: dict[str, Any], tool_result: dict[str, Any]) -> None:
    doc_id = str(tool_result.get("doc_id", ""))
    tokens = list(tool_result.get("tokens", []) or [])
    fields, evidence, line_items = parse_invoice_tokens(tokens, doc_id)
    record = {
        "doc_id": doc_id,
        "tokens": tokens,
        "fields": fields,
        "evidence": evidence,
        "line_items": line_items,
        "line_tokens": [token for token in tokens if "|" in str(token.get("text", ""))],
    }
    collected.setdefault("invoice_records", []).append(record)

    collected["invoice_doc_id"] = doc_id
    collected["invoice_tokens"] = tokens
    collected["invoice_fields"] = fields
    collected["invoice_evidence"] = evidence
    collected["invoice_line_items"] = line_items
    collected["invoice_line_tokens"] = record["line_tokens"]


def capture_email_data(collected: dict[str, Any], tool_result: dict[str, Any]) -> None:
    doc_id = str(tool_result.get("doc_id", ""))
    tokens = list(tool_result.get("tokens", []) or [])
    collected["email_doc_id"] = doc_id
    collected["email_tokens"] = tokens
    collected["email_evidence"] = parse_email_tokens(tokens, doc_id)


def run_episode_with_env(
    env: Any,
    case_id: str,
    client: Optional[OpenAI],
    *,
    temperature: float = TEMPERATURE,
    emit_logs: bool = True,
) -> dict[str, Any]:
    rewards: list[float] = []
    steps_taken = 0
    final_score = 0.0
    success = False
    task_type = "unknown"

    if emit_logs:
        log_start(task=case_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        reset_result = env.reset(case_id=case_id)
        observation = reset_result.observation
        task_type = observation.task_type
        max_steps = int(getattr(observation, "max_steps", MAX_STEPS) or MAX_STEPS)
        step_no = 1

        collected: dict[str, Any] = {
            "invoice_doc_id": "",
            "invoice_tokens": [],
            "invoice_fields": {},
            "invoice_evidence": {},
            "invoice_line_items": [],
            "invoice_line_tokens": [],
            "invoice_records": [],
            "email_doc_id": "",
            "email_tokens": [],
            "email_evidence": {},
            "po": None,
            "receipt": None,
            "ledger_hits": [],
            "ledger_queries": {},
            "ledger_search": {},
            "vendor_history": [],
            "email_thread": None,
            "bank_compare": None,
            "bank_compares": [],
            "pressure_events_seen": [],
            "pressure_docs": [],
            "pressure_doc_ids": [],
        }

        invoice_doc_ids: list[str] = []
        email_doc_id = ""
        for doc in observation.visible_documents:
            doc_type = normalize_text(doc.get("doc_type"))
            if doc_type == "invoice":
                invoice_doc_ids.append(str(doc.get("doc_id")))
            if doc_type == "email" and not email_doc_id:
                email_doc_id = str(doc.get("doc_id"))

        if not invoice_doc_ids:
            raise RuntimeError(f"No visible invoice document for {case_id}")

        for invoice_doc_id in invoice_doc_ids:
            ocr_invoice_result, step_no = perform_step(
                env,
                step_no,
                rewards,
                LedgerShieldAction(
                    action_type="ocr",
                    payload={"doc_id": invoice_doc_id, "mode": "accurate"},
                ),
                emit_logs=emit_logs,
            )
            steps_taken = step_no - 1
            capture_invoice_data(collected, ocr_invoice_result.observation.last_tool_result)
            if task_type not in {"task_d", "task_e"}:
                break

        if task_type == "task_a":
            invoice_doc_id = invoice_doc_ids[0]
            zoom_result, step_no = perform_step(
                env,
                step_no,
                rewards,
                LedgerShieldAction(
                    action_type="zoom",
                    payload={"doc_id": invoice_doc_id, "bbox": [0, 0, 400, 400]},
                ),
                emit_logs=emit_logs,
            )
            steps_taken = step_no - 1
            if zoom_result.done:
                final_score = normalize_score(zoom_result.info.get("final_score", rewards[-1] if rewards else 0.0))
                success = final_score >= SUCCESS_SCORE_THRESHOLD
            model_assessment = get_model_assessment(client, case_id, task_type, collected, temperature=temperature)
            submit_payload = build_final_submission(task_type, collected, model_assessment)
            submit_payload = merge_submission_override(
                submit_payload,
                get_model_submission_override(
                    client,
                    case_id,
                    task_type,
                    collected,
                    submit_payload,
                    temperature=temperature,
                ),
            )
            final_result, step_no = perform_step(
                env,
                step_no,
                rewards,
                LedgerShieldAction(action_type="submit_decision", payload=submit_payload),
                emit_logs=emit_logs,
            )
            steps_taken = step_no - 1
            final_score = normalize_score(final_result.info.get("final_score", final_result.reward or 0.0))
            success = final_score >= SUCCESS_SCORE_THRESHOLD
            return {
                "case_id": case_id,
                "task_type": task_type,
                "score": final_score,
                "steps": steps_taken,
            }

        invoice_fields = collected["invoice_fields"]
        vendor_key = vendor_key_for(invoice_fields)
        if not vendor_key:
            vendor_key = normalize_text(collected.get("email_thread", {}).get("vendor_key"))

        po_id = str(invoice_fields.get("po_id", "")).strip()
        receipt_id = str(invoice_fields.get("receipt_id", "")).strip()
        invoice_total = safe_float(invoice_fields.get("total"))
        invoice_number = str(invoice_fields.get("invoice_number", "")).strip()
        proposed_bank_account = str(invoice_fields.get("bank_account", "")).strip()

        if task_type == "task_b":
            action_plan = [
                LedgerShieldAction(action_type="lookup_policy", payload={}),
                LedgerShieldAction(action_type="lookup_po", payload={"po_id": po_id}),
                LedgerShieldAction(
                    action_type="lookup_receipt",
                    payload={"receipt_id": receipt_id or po_id.replace("PO-", "GRN-")},
                ),
            ]
        elif task_type == "task_c":
            action_plan = [
                LedgerShieldAction(
                    action_type="search_ledger",
                    payload={
                        "vendor_key": vendor_key,
                        "invoice_number": invoice_number,
                        "amount": invoice_total,
                    },
                ),
                LedgerShieldAction(
                    action_type="compare_bank_account",
                    payload={
                        "vendor_key": vendor_key,
                        "proposed_bank_account": proposed_bank_account,
                    },
                ),
            ]
        else:
            action_plan = []
            if email_doc_id:
                action_plan.extend(
                    [
                        LedgerShieldAction(
                            action_type="ocr",
                            payload={"doc_id": email_doc_id, "mode": "accurate"},
                        ),
                        LedgerShieldAction(action_type="inspect_email_thread", payload={"thread_id": email_doc_id}),
                    ]
                )
            action_plan.extend(
                [
                    LedgerShieldAction(action_type="lookup_vendor_history", payload={"vendor_key": vendor_key}),
                    LedgerShieldAction(action_type="lookup_policy", payload={}),
                ]
            )
            for record in collected.get("invoice_records", []) or []:
                record_fields = record.get("fields", {})
                action_plan.append(
                    LedgerShieldAction(
                        action_type="compare_bank_account",
                        payload={
                            "vendor_key": vendor_key,
                            "proposed_bank_account": str(record_fields.get("bank_account", "")).strip(),
                        },
                    )
                )
                action_plan.append(
                    LedgerShieldAction(
                        action_type="search_ledger",
                        payload={
                            "vendor_key": vendor_key,
                            "invoice_number": str(record_fields.get("invoice_number", "")).strip(),
                            "amount": safe_float(record_fields.get("total")),
                        },
                    )
                )

        for action in action_plan:
            if step_no > max_steps:
                break
            result, step_no = perform_step(env, step_no, rewards, action, emit_logs=emit_logs)
            steps_taken = step_no - 1
            tool = result.observation.last_tool_result or {}
            tool_name = tool.get("tool_name")

            if tool_name == "lookup_po" and tool.get("success"):
                collected["po"] = tool.get("po")
            elif tool_name == "lookup_receipt" and tool.get("success"):
                collected["receipt"] = tool.get("receipt")
            elif tool_name == "search_ledger" and tool.get("success"):
                hits = list(tool.get("hits", []) or [])
                existing_ids = {row.get("ledger_id") for row in collected["ledger_hits"]}
                for hit in hits:
                    if hit.get("ledger_id") not in existing_ids:
                        collected["ledger_hits"].append(hit)
                        existing_ids.add(hit.get("ledger_id"))
                invoice_key = normalize_text(action.payload.get("invoice_number"))
                if invoice_key:
                    collected["ledger_queries"][invoice_key] = tool
                collected["ledger_search"] = tool
            elif tool_name == "lookup_vendor_history" and tool.get("success"):
                collected["vendor_history"] = list(tool.get("history", []) or [])
            elif tool_name == "inspect_email_thread" and tool.get("success"):
                collected["email_thread"] = tool.get("thread") or {}
            elif tool_name == "compare_bank_account" and tool.get("success"):
                collected["bank_compare"] = tool
                collected["bank_compares"].append(tool)
            elif tool_name == "lookup_policy" and tool.get("success"):
                collected["policies"] = list(tool.get("policies", []) or [])
            elif tool_name == "ocr" and tool.get("success") and tool.get("doc_id") == email_doc_id:
                capture_email_data(collected, tool)
            if tool.get("pressure_event"):
                pressure_doc_id = str(tool["pressure_event"].get("doc_id", "")).strip()
                if pressure_doc_id and pressure_doc_id not in collected["pressure_doc_ids"]:
                    collected["pressure_doc_ids"].append(pressure_doc_id)
                    collected["pressure_events_seen"].append(pressure_doc_id)

            if result.done:
                final_score = normalize_score(result.info.get("final_score", result.reward or 0.0))
                success = final_score >= SUCCESS_SCORE_THRESHOLD
                return {
                    "case_id": case_id,
                    "task_type": task_type,
                    "score": final_score,
                    "steps": steps_taken,
                    "final_decision": str((tool or {}).get("decision", "")),
                    "score_breakdown": dict(result.info.get("score_breakdown", {}) or {}),
                    "pressure_resistance_score": float(result.info.get("pressure_resistance_score", 0.0) or 0.0),
                }

        for pressure_doc_id in list(collected.get("pressure_doc_ids", [])):
            if pressure_doc_id in collected["pressure_docs"]:
                continue
            if step_no > max_steps:
                break
            pressure_result, step_no = perform_step(
                env,
                step_no,
                rewards,
                LedgerShieldAction(
                    action_type="ocr",
                    payload={"doc_id": pressure_doc_id, "mode": "accurate"},
                ),
                emit_logs=emit_logs,
            )
            steps_taken = step_no - 1
            collected["pressure_docs"].append(pressure_doc_id)
            if pressure_result.done:
                final_score = normalize_score(pressure_result.info.get("final_score", pressure_result.reward or 0.0))
                success = final_score >= SUCCESS_SCORE_THRESHOLD
                last_tool = pressure_result.observation.last_tool_result or {}
                return {
                    "case_id": case_id,
                    "task_type": task_type,
                    "score": final_score,
                    "steps": steps_taken,
                    "final_decision": str(last_tool.get("decision", "")),
                    "score_breakdown": dict(pressure_result.info.get("score_breakdown", {}) or {}),
                    "pressure_resistance_score": float(pressure_result.info.get("pressure_resistance_score", 0.0) or 0.0),
                }

        if task_type == "task_b":
            preview_submission = build_task_b_submission(collected)
            if preview_submission["decision"] == "HOLD" and step_no <= max_steps:
                result, step_no = perform_step(
                    env,
                    step_no,
                    rewards,
                    LedgerShieldAction(action_type="request_callback_verification", payload={}),
                    emit_logs=emit_logs,
                )
                steps_taken = step_no - 1
                if result.done:
                    final_score = normalize_score(result.info.get("final_score", result.reward or 0.0))
                    success = final_score >= SUCCESS_SCORE_THRESHOLD
                    return {
                        "case_id": case_id,
                        "task_type": task_type,
                        "score": final_score,
                        "steps": steps_taken,
                        "final_decision": str((result.observation.last_tool_result or {}).get("decision", "")),
                        "score_breakdown": dict(result.info.get("score_breakdown", {}) or {}),
                        "pressure_resistance_score": float(result.info.get("pressure_resistance_score", 0.0) or 0.0),
                    }

        if task_type == "task_c":
            preview_submission = build_task_c_submission(collected)
            if preview_submission["decision"] == "ESCALATE_FRAUD":
                for action in [
                    LedgerShieldAction(action_type="request_callback_verification", payload={}),
                    LedgerShieldAction(action_type="flag_duplicate_cluster_review", payload={}),
                    LedgerShieldAction(action_type="route_to_security", payload={}),
                    LedgerShieldAction(action_type="freeze_vendor_profile", payload={}),
                ]:
                    if step_no > max_steps:
                        break
                    result, step_no = perform_step(env, step_no, rewards, action, emit_logs=emit_logs)
                    steps_taken = step_no - 1
                    if result.done:
                        final_score = normalize_score(result.info.get("final_score", result.reward or 0.0))
                        success = final_score >= SUCCESS_SCORE_THRESHOLD
                        return {
                            "case_id": case_id,
                            "task_type": task_type,
                            "score": final_score,
                            "steps": steps_taken,
                            "final_decision": str((result.observation.last_tool_result or {}).get("decision", "")),
                            "score_breakdown": dict(result.info.get("score_breakdown", {}) or {}),
                            "pressure_resistance_score": float(result.info.get("pressure_resistance_score", 0.0) or 0.0),
                        }

        if task_type in {"task_d", "task_e"}:
            preview_submission = (
                build_task_e_submission(collected, {})
                if task_type == "task_e"
                else build_task_d_submission(collected, {})
            )
            if preview_submission["decision"] == "ESCALATE_FRAUD":
                followup_actions = [
                    LedgerShieldAction(action_type="request_callback_verification", payload={}),
                    LedgerShieldAction(action_type="flag_duplicate_cluster_review", payload={}),
                    LedgerShieldAction(action_type="route_to_security", payload={}),
                    LedgerShieldAction(action_type="freeze_vendor_profile", payload={}),
                ]
                if task_type == "task_e":
                    followup_actions.append(
                        LedgerShieldAction(
                            action_type="create_human_handoff",
                            payload={
                                "summary": "Coordinated multi-invoice campaign detected.",
                                "recommended_next_step": "campaign_freeze_and_manual_review",
                                "confidence": 0.93,
                            },
                        )
                    )
                for action in followup_actions:
                    if step_no > max_steps:
                        break
                    result, step_no = perform_step(env, step_no, rewards, action, emit_logs=emit_logs)
                    steps_taken = step_no - 1
                    if result.done:
                        final_score = normalize_score(result.info.get("final_score", result.reward or 0.0))
                        success = final_score >= SUCCESS_SCORE_THRESHOLD
                        return {
                            "case_id": case_id,
                            "task_type": task_type,
                            "score": final_score,
                            "steps": steps_taken,
                            "final_decision": str((result.observation.last_tool_result or {}).get("decision", "")),
                            "score_breakdown": dict(result.info.get("score_breakdown", {}) or {}),
                            "pressure_resistance_score": float(result.info.get("pressure_resistance_score", 0.0) or 0.0),
                        }

        context = {
            "fields": collected.get("invoice_fields", {}),
            "duplicate_links": [hit.get("ledger_id") for hit in collected.get("ledger_hits", []) if hit.get("ledger_id")],
            "fraud_flags": build_task_c_submission(collected).get("fraud_flags", []) if task_type == "task_c" else [],
            "reason_codes": (
                build_task_d_submission(collected, {}).get("reason_codes", [])
                if task_type == "task_d"
                else build_task_e_submission(collected, {}).get("reason_codes", [])
                if task_type == "task_e"
                else []
            ),
            "policy_checks": (
                build_task_d_submission(collected, {}).get("policy_checks", policy_check_payload("pass", "pass", "pass"))
                if task_type == "task_d"
                else build_task_e_submission(collected, {}).get("policy_checks", policy_check_payload("pass", "fail", "fail"))
                if task_type == "task_e"
                else build_task_b_submission(collected).get("policy_checks", policy_check_payload("fail", "pass", "pass"))
            ),
            "invoice_records": collected.get("invoice_records", []),
            "email_thread": collected.get("email_thread", {}),
            "email_evidence": collected.get("email_evidence", {}),
            "ledger_hits": collected.get("ledger_hits", []),
            "vendor_history": collected.get("vendor_history", []),
            "pressure_events_seen": collected.get("pressure_events_seen", []),
        }
        model_assessment = get_model_assessment(client, case_id, task_type, context, temperature=temperature)
        submit_payload = build_final_submission(task_type, collected, model_assessment)
        submit_payload = merge_submission_override(
            submit_payload,
            get_model_submission_override(
                client,
                case_id,
                task_type,
                context,
                submit_payload,
                temperature=temperature,
            ),
        )

        final_info: dict[str, Any] = {}
        last_tool: dict[str, Any] = {}
        if step_no <= max_steps:
            final_result, step_no = perform_step(
                env,
                step_no,
                rewards,
                LedgerShieldAction(action_type="submit_decision", payload=submit_payload),
                emit_logs=emit_logs,
            )
            steps_taken = step_no - 1
            final_score = normalize_score(final_result.info.get("final_score", final_result.reward or 0.0))
            success = final_score >= SUCCESS_SCORE_THRESHOLD
            final_info = dict(final_result.info or {})
            last_tool = final_result.observation.last_tool_result or {}
        else:
            final_score = normalize_score(rewards[-1] if rewards else 0.0)
            success = False

        return {
            "case_id": case_id,
            "task_type": task_type,
            "score": final_score,
            "steps": steps_taken,
            "final_decision": str(last_tool.get("decision", submit_payload.get("decision", ""))),
            "score_breakdown": dict(final_info.get("score_breakdown", {}) or {}),
            "pressure_resistance_score": float(final_info.get("pressure_resistance_score", 0.0) or 0.0),
        }

    except Exception as exc:  # noqa: BLE001
        trace(f"[ERROR] episode failed for {case_id}: {exc}")
        return {
            "case_id": case_id,
            "task_type": task_type,
            "score": 0.0,
            "steps": steps_taken,
            "final_decision": "",
            "score_breakdown": {},
            "pressure_resistance_score": 0.0,
            "error": str(exc),
        }
    finally:
        try:
            env.close()
        except Exception as exc:  # noqa: BLE001
            trace(f"[DEBUG] env.close failed for {case_id}: {exc}")
        if emit_logs:
            log_end(success=success, steps=steps_taken, rewards=rewards, score=final_score)


def run_episode(
    env_url: str,
    case_id: str,
    client: Optional[OpenAI],
    *,
    temperature: float = TEMPERATURE,
    emit_logs: bool = True,
) -> dict[str, Any]:
    env = LedgerShieldEnv(base_url=env_url)
    return run_episode_with_env(
        env=env,
        case_id=case_id,
        client=client,
        temperature=temperature,
        emit_logs=emit_logs,
    )


def build_openai_client() -> Optional[OpenAI]:
    if not HF_TOKEN:
        trace("[DEBUG] HF_TOKEN not set; running heuristic-only baseline.")
        return None

    try:
        return OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    except Exception as exc:  # noqa: BLE001
        trace(f"[DEBUG] failed to initialize OpenAI client: {exc}")
        return None


def run_baseline_inference(
    env_url: str,
    cases: list[str],
    *,
    temperature: float = TEMPERATURE,
    pass_k: int = 1,
    pass_threshold: float = PASSK_SUCCESS_THRESHOLD,
    emit_logs: bool = True,
) -> dict[str, Any]:
    client = build_openai_client()
    results: list[dict[str, Any]] = []
    total_trial_successes = 0
    total_trials = 0

    for case_id in cases:
        trials = [
            run_episode(
                env_url=env_url,
                case_id=case_id,
                client=client,
                temperature=temperature,
                emit_logs=emit_logs,
            )
            for _ in range(max(1, int(pass_k)))
        ]
        summary = summarize_case_trials(case_id, trials, pass_threshold=pass_threshold)
        results.append(summary)
        total_trial_successes += int(summary.get("successful_trials", 0) or 0)
        total_trials += int(summary.get("trial_count", 0) or 0)
        if emit_logs and pass_k > 1:
            trace(
                "[PASSK] "
                f"case={case_id} "
                f"k={int(pass_k)} "
                f"trial_pass_rate={float(summary.get('trial_pass_rate', 0.0)):.3f} "
                f"consistent_pass={str(bool(summary.get('pass_k_consistent', False))).lower()}"
            )

    avg_score = sum(result.get("score", 0.0) for result in results) / max(len(results), 1)
    consistent_pass_rate = sum(bool(result.get("pass_k_consistent", False)) for result in results) / max(len(results), 1)
    any_pass_rate = sum(bool(result.get("pass_k_any", False)) for result in results) / max(len(results), 1)
    trial_pass_rate = total_trial_successes / max(total_trials, 1)
    trace(
        "[SUMMARY] "
        f"cases={len(results)} "
        f"avg_score={avg_score:.4f} "
        f"scores={compact_json({result['case_id']: result.get('score', 0.0) for result in results})}"
    )
    return {
        "results": results,
        "average_score": round(avg_score, 4),
        "temperature": round(float(temperature), 4),
        "pass_k": int(pass_k),
        "pass_threshold": round(float(pass_threshold), 4),
        "trial_pass_rate": round(trial_pass_rate, 4),
        "consistent_pass_rate": round(consistent_pass_rate, 4),
        "any_pass_rate": round(any_pass_rate, 4),
    }


def run_local_baseline(
    cases: list[str],
    *,
    db: dict[str, Any] | None = None,
    client: Optional[OpenAI] = None,
    emit_logs: bool = False,
    temperature: float = TEMPERATURE,
    pass_k: int = 1,
    pass_threshold: float = PASSK_SUCCESS_THRESHOLD,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    total_trial_successes = 0
    total_trials = 0

    for case_id in cases:
        trials = [
            run_episode_with_env(
                env=LocalLedgerShieldEnv(db=db),
                case_id=case_id,
                client=client,
                emit_logs=emit_logs,
                temperature=temperature,
            )
            for _ in range(max(1, int(pass_k)))
        ]
        summary = summarize_case_trials(case_id, trials, pass_threshold=pass_threshold)
        results.append(summary)
        total_trial_successes += int(summary.get("successful_trials", 0) or 0)
        total_trials += int(summary.get("trial_count", 0) or 0)

    avg_score = sum(result.get("score", 0.0) for result in results) / max(len(results), 1)
    consistent_pass_rate = sum(bool(result.get("pass_k_consistent", False)) for result in results) / max(len(results), 1)
    any_pass_rate = sum(bool(result.get("pass_k_any", False)) for result in results) / max(len(results), 1)
    return {
        "results": results,
        "average_score": round(avg_score, 4),
        "temperature": round(float(temperature), 4),
        "pass_k": int(pass_k),
        "pass_threshold": round(float(pass_threshold), 4),
        "trial_pass_rate": round(total_trial_successes / max(total_trials, 1), 4),
        "consistent_pass_rate": round(consistent_pass_rate, 4),
        "any_pass_rate": round(any_pass_rate, 4),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LedgerShield baseline inference")
    parser.add_argument("--api-url", default=API_BASE_URL)
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--token", default=HF_TOKEN)
    parser.add_argument("--env-url", default=ENV_URL)
    parser.add_argument("--cases", nargs="+", default=DEFAULT_CASES)
    parser.add_argument("--temperature", type=float, default=TEMPERATURE)
    parser.add_argument("--passK", type=int, default=1)
    parser.add_argument("--pass-threshold", type=float, default=PASSK_SUCCESS_THRESHOLD)
    parser.add_argument("--output-artifact", default="")
    parser.add_argument("--no-logs", action="store_true")
    return parser.parse_args()


def main() -> None:
    global API_BASE_URL, MODEL_NAME, HF_TOKEN, ENV_URL

    args = parse_args()
    API_BASE_URL = args.api_url
    MODEL_NAME = args.model
    HF_TOKEN = args.token
    ENV_URL = args.env_url
    emit_logs = True

    if args.no_logs:
        trace("[DEBUG] Ignoring --no-logs to preserve benchmark stdout format.")

    payload = run_baseline_inference(
        env_url=args.env_url,
        cases=args.cases,
        temperature=float(args.temperature),
        pass_k=max(1, int(args.passK)),
        pass_threshold=float(args.pass_threshold),
        emit_logs=emit_logs,
    )
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    payload["model"] = MODEL_NAME
    payload["env_url"] = args.env_url

    if args.output_artifact:
        write_run_artifact(args.output_artifact, payload)


if __name__ == "__main__":
    main()
