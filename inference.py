"""
Inference Script Example
===================================
MANDATORY
- Before submitting, ensure the following variables are defined in your environment configuration:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.
    LOCAL_IMAGE_NAME The name of the local image to use for the environment if you are using from_docker_image().

- Defaults are set only for API_BASE_URL and MODEL_NAME
  (and should reflect your active inference setup):
    API_BASE_URL = os.getenv("API_BASE_URL", "<your-active-endpoint>")
    MODEL_NAME = os.getenv("MODEL_NAME", "<your-active-model>")

- The inference script must be named inference.py and placed in the root directory of the project.
- Participants must use OpenAI Client for all LLM calls using the variables above.
- I've read the sample inference.py and have followed it strictly.

STDOUT FORMAT
- The script emits exactly three line types to stdout, in this order:
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP] step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END] success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>

  Rules:
    - One [START] line at episode begin.
    - One [STEP] line per step, immediately after env.step() returns.
    - One [END] line after env.close(), always emitted even on exception.
    - reward and rewards are formatted to 2 decimal places.
    - done and success are lowercase booleans: true or false.
    - error is the raw last_action_error string, or null if none.
    - All fields are on a single line with no newlines within a line.
    - Each task should return score strictly between 0 and 1, not 0.00 and not 1.00.

  Example:
    [START] task=click-test env=miniwob model=Qwen3-VL-30B
    [STEP] step=1 action=click('123') reward=0.00 done=false error=null
    [STEP] step=2 action=fill('456','text') reward=0.00 done=false error=null
    [STEP] step=3 action=click('789') reward=0.99 done=true error=null
    [END] success=true steps=3 score=0.99 rewards=0.00,0.00,0.99
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
from llm_utils import create_json_chat_completion, parse_json_dict
from server.environment import LedgerShieldEnvironment
from server.schema import canonical_reason_codes
from task_c_guardrails import (
    grounded_task_c_submission,
    sanitize_task_c_submission,
    validate_task_c_submission,
)
from task_d_guardrails import (
    derive_email_thread_signals as _derive_email_thread_signals,
    grounded_task_d_submission,
    policy_check_payload as _policy_check_payload,
    sanitize_task_d_submission,
    validate_task_d_submission,
)


# Required runtime configuration. Only the endpoint/model have defaults.
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-5.4")
HF_TOKEN = os.getenv("HF_TOKEN")
# Optional when running with from_docker_image().
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")
ENV_URL = os.getenv("ENV_URL") or "http://localhost:8000"
BENCHMARK = "ledgershield"
MAX_STEPS = 20
TEMPERATURE = 0.0
MAX_TOKENS = 512
SUCCESS_SCORE_THRESHOLD = 0.60
PASSK_SUCCESS_THRESHOLD = 0.85
TASK_SCORE_MIN = 0.01
TASK_SCORE_MAX = 0.99
ARTIFACT_DIR = Path("artifacts")

DEFAULT_CASES = [
    "CASE-A-001",
    "CASE-A-002",
    "CASE-A-003",
    "CASE-A-004",
    "CASE-B-001",
    "CASE-B-002",
    "CASE-B-003",
    "CASE-B-004",
    "CASE-B-005",
    "CASE-C-001",
    "CASE-C-002",
    "CASE-C-003",
    "CASE-C-004",
    "CASE-D-001",
    "CASE-D-002",
    "CASE-D-003",
    "CASE-D-004",
    "CASE-D-005",
    "CASE-D-006",
    "CASE-E-001",
    "CASE-E-002",
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


def format_decimal(value: Any) -> str:
    numeric = safe_float(value)
    if abs(numeric) < 0.005:
        numeric = 0.0
    return f"{numeric:.2f}"


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
        f"reward={format_decimal(reward)} "
        f"done={str(done).lower()} "
        f"error={sanitize_log_field(error)}",
        flush=True,
    )


def log_end(success: bool, steps: int, rewards: list[float], score: Optional[float] = None) -> None:
    final_score = rewards[-1] if score is None and rewards else (0.0 if score is None else score)
    rewards_str = ",".join(format_decimal(reward) for reward in rewards)
    print(
        "[END] "
        f"success={str(success).lower()} "
        f"steps={steps} "
        f"score={format_decimal(normalize_score(final_score))} "
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
    return _derive_email_thread_signals(thread)


def vendor_key_for(fields: dict[str, Any]) -> str:
    vendor_name = normalize_text(fields.get("vendor_name"))
    return VENDOR_KEY_BY_NAME.get(vendor_name, "")


def action_signature(action: LedgerShieldAction) -> str:
    return f"{normalize_text(action.action_type)}:{compact_json(action.payload)}"


def _append_candidate(
    candidates: list[LedgerShieldAction],
    seen_signatures: set[str],
    action: LedgerShieldAction,
) -> None:
    signature = action_signature(action)
    if signature in seen_signatures:
        return
    seen_signatures.add(signature)
    candidates.append(action)


def _invoice_record_summary(record: dict[str, Any]) -> dict[str, Any]:
    fields = record.get("fields", {}) or {}
    return {
        "doc_id": record.get("doc_id"),
        "invoice_number": fields.get("invoice_number"),
        "invoice_date": fields.get("invoice_date"),
        "total": fields.get("total"),
        "bank_account": fields.get("bank_account"),
    }


def summarize_collected_state(collected: dict[str, Any]) -> dict[str, Any]:
    email_thread = collected.get("email_thread") or {}
    ledger_search = collected.get("ledger_search") or {}
    return {
        "invoice_records": [_invoice_record_summary(record) for record in collected.get("invoice_records", []) or []],
        "email_thread": {
            "sender": email_thread.get("sender"),
            "subject": email_thread.get("subject"),
            "flags": email_thread.get("flags"),
            "derived_flags": email_thread.get("derived_flags"),
            "sender_profile": email_thread.get("sender_profile"),
            "request_signals": email_thread.get("request_signals"),
        },
        "bank_compares": [
            {
                "proposed_bank_account": compare.get("proposed_bank_account"),
                "matched": compare.get("matched"),
                "vendor_bank_account": compare.get("vendor_bank_account"),
            }
            for compare in collected.get("bank_compares", []) or []
        ],
        "ledger_search": {
            "exact_duplicate_count": ledger_search.get("exact_duplicate_count"),
            "near_duplicate_count": ledger_search.get("near_duplicate_count"),
            "top_hits": [
                {
                    "ledger_id": hit.get("ledger_id"),
                    "invoice_number": hit.get("invoice_number"),
                    "amount": hit.get("amount"),
                    "match_score": hit.get("match_score"),
                }
                for hit in (collected.get("ledger_hits", []) or [])[:5]
            ],
        },
        "vendor_history": [
            {
                "event_type": row.get("event_type") or row.get("change_type"),
                "status": row.get("status"),
            }
            for row in (collected.get("vendor_history", []) or [])[:5]
        ],
        "policies_loaded": bool(collected.get("policies")),
        "email_ocr_loaded": bool(collected.get("email_tokens")),
    }


def build_investigation_candidates(
    task_type: str,
    collected: dict[str, Any],
    *,
    vendor_key: str,
    po_id: str,
    receipt_id: str,
    invoice_total: float,
    invoice_number: str,
    proposed_bank_account: str,
    email_doc_id: str,
    executed_signatures: set[str],
) -> list[LedgerShieldAction]:
    candidates: list[LedgerShieldAction] = []
    seen = set(executed_signatures)

    if task_type == "task_b":
        _append_candidate(candidates, seen, LedgerShieldAction(action_type="lookup_policy", payload={}))
        if po_id:
            _append_candidate(candidates, seen, LedgerShieldAction(action_type="lookup_po", payload={"po_id": po_id}))
            resolved_receipt_id = receipt_id or po_id.replace("PO-", "GRN-", 1)
            _append_candidate(
                candidates,
                seen,
                LedgerShieldAction(action_type="lookup_receipt", payload={"receipt_id": resolved_receipt_id}),
            )
        return candidates

    if task_type == "task_c":
        if vendor_key and (invoice_number or invoice_total):
            _append_candidate(
                candidates,
                seen,
                LedgerShieldAction(
                    action_type="search_ledger",
                    payload={
                        "vendor_key": vendor_key,
                        "invoice_number": invoice_number,
                        "amount": invoice_total,
                    },
                ),
            )
        if vendor_key and proposed_bank_account:
            _append_candidate(
                candidates,
                seen,
                LedgerShieldAction(
                    action_type="compare_bank_account",
                    payload={"vendor_key": vendor_key, "proposed_bank_account": proposed_bank_account},
                ),
            )
        return candidates

    if email_doc_id and not collected.get("email_tokens"):
        _append_candidate(
            candidates,
            seen,
            LedgerShieldAction(action_type="ocr", payload={"doc_id": email_doc_id, "mode": "accurate"}),
        )
    if email_doc_id:
        _append_candidate(
            candidates,
            seen,
            LedgerShieldAction(action_type="inspect_email_thread", payload={"thread_id": email_doc_id}),
        )

    if vendor_key:
        _append_candidate(
            candidates,
            seen,
            LedgerShieldAction(action_type="lookup_vendor_history", payload={"vendor_key": vendor_key}),
        )
    _append_candidate(candidates, seen, LedgerShieldAction(action_type="lookup_policy", payload={}))

    for record in collected.get("invoice_records", []) or []:
        fields = record.get("fields", {}) or {}
        record_bank = str(fields.get("bank_account", "")).strip()
        record_invoice_number = str(fields.get("invoice_number", "")).strip()
        record_total = safe_float(fields.get("total"))
        if vendor_key and record_bank:
            _append_candidate(
                candidates,
                seen,
                LedgerShieldAction(
                    action_type="compare_bank_account",
                    payload={"vendor_key": vendor_key, "proposed_bank_account": record_bank},
                ),
            )
        if vendor_key and (record_invoice_number or record_total):
            _append_candidate(
                candidates,
                seen,
                LedgerShieldAction(
                    action_type="search_ledger",
                    payload={
                        "vendor_key": vendor_key,
                        "invoice_number": record_invoice_number,
                        "amount": record_total,
                    },
                ),
            )
    return candidates


def build_intervention_candidates(
    task_type: str,
    collected: dict[str, Any],
    submission: dict[str, Any],
    *,
    executed_signatures: set[str],
) -> list[LedgerShieldAction]:
    decision = normalize_text(submission.get("decision"))
    if decision not in {"hold", "needs_review", "escalate_fraud"}:
        return []

    candidates: list[LedgerShieldAction] = []
    seen = set(executed_signatures)
    reason_codes = set(
        canonical_reason_codes(
            (submission.get("reason_codes", []) or [])
            + (submission.get("fraud_flags", []) or [])
            + (submission.get("campaign_signals", []) or [])
        )
    )
    ledger_search = collected.get("ledger_search") or {}
    has_duplicates = bool(collected.get("ledger_hits")) or int(ledger_search.get("exact_duplicate_count", 0) or 0) > 0
    has_duplicates = has_duplicates or int(ledger_search.get("near_duplicate_count", 0) or 0) > 0
    bank_mismatch = any(compare and not bool(compare.get("matched")) for compare in collected.get("bank_compares", []) or [])
    email_thread = collected.get("email_thread") or {}
    email_flags = set(
        canonical_reason_codes((email_thread.get("flags", []) or []) + (email_thread.get("derived_flags", []) or []))
    )

    if task_type == "task_b":
        _append_candidate(candidates, seen, LedgerShieldAction(action_type="request_callback_verification", payload={}))
        return candidates

    if bank_mismatch or "bank_override_attempt" in reason_codes:
        _append_candidate(candidates, seen, LedgerShieldAction(action_type="request_callback_verification", payload={}))
        _append_candidate(
            candidates,
            seen,
            LedgerShieldAction(action_type="request_bank_change_approval_chain", payload={}),
        )
        _append_candidate(candidates, seen, LedgerShieldAction(action_type="freeze_vendor_profile", payload={}))

    if has_duplicates or {"duplicate_near_match", "approval_threshold_evasion", "shared_bank_account", "coordinated_timing"} & reason_codes:
        _append_candidate(candidates, seen, LedgerShieldAction(action_type="flag_duplicate_cluster_review", payload={}))

    if {"sender_domain_spoof", "policy_bypass_attempt"} & (reason_codes | email_flags):
        _append_candidate(candidates, seen, LedgerShieldAction(action_type="route_to_security", payload={}))

    if task_type == "task_e":
        _append_candidate(
            candidates,
            seen,
            LedgerShieldAction(
                action_type="create_human_handoff",
                payload={
                    "summary": "Potential coordinated payment campaign detected across linked invoices.",
                    "recommended_next_step": "campaign_freeze_and_manual_review",
                    "confidence": submission.get("confidence", 0.9),
                },
            ),
        )
    return candidates


def llm_plan_actions(
    client: Optional[OpenAI],
    *,
    task_type: str,
    phase: str,
    collected: dict[str, Any],
    candidates: list[LedgerShieldAction],
    max_actions: int,
    current_submission: Optional[dict[str, Any]] = None,
) -> list[LedgerShieldAction]:
    if not candidates or max_actions <= 0:
        return []

    trimmed_candidates = candidates[:max_actions]
    if not client:
        return trimmed_candidates

    indexed = [
        {
            "action_id": f"A{idx + 1}",
            "action_type": action.action_type,
            "payload": action.payload,
        }
        for idx, action in enumerate(candidates)
    ]
    candidate_by_id = {item["action_id"]: candidates[idx] for idx, item in enumerate(indexed)}
    max_plan_length = min(max_actions, len(indexed))
    system_prompt = (
        "You are controlling a LedgerShield AP investigation agent. "
        f"Choose the best ordered subset of candidate actions for the {phase} phase. "
        "Prefer actions that surface independent evidence, reveal required artifacts before submission, "
        "avoid redundant repeats, and keep enough steps for the final decision. "
        "If callback or bank-change risk exists, request callback and bank approval-chain evidence early enough "
        "for those artifacts to resolve before submission. Use only the provided action_id values and return JSON only."
    )
    user_payload = {
        "task_type": task_type,
        "phase": phase,
        "max_actions": max_plan_length,
        "current_state": summarize_collected_state(collected),
        "draft_submission": current_submission or {},
        "candidate_actions": indexed,
        "response_format": {
            "ordered_action_ids": ["A1", "A2"],
            "reason": "brief explanation",
        },
    }

    try:
        response = create_json_chat_completion(
            client,
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": compact_json(user_payload)},
            ],
            temperature=TEMPERATURE,
            max_output_tokens=384,
            api_base_url=API_BASE_URL,
        )
        content = response.choices[0].message.content or "{}"
        result = parse_json_dict(content)
    except Exception as exc:  # noqa: BLE001
        trace(f"[LLM ERROR] action planning {task_type}/{phase}: {exc}")
        return trimmed_candidates

    selected: list[LedgerShieldAction] = []
    seen_ids: set[str] = set()
    for raw_id in result.get("ordered_action_ids", []) or []:
        action_id = str(raw_id).strip().upper()
        if action_id in seen_ids or action_id not in candidate_by_id:
            continue
        seen_ids.add(action_id)
        selected.append(candidate_by_id[action_id])
        if len(selected) >= max_plan_length:
            break

    return selected or trimmed_candidates


def sanitize_task_e_submission(candidate: dict[str, Any], collected: dict[str, Any]) -> dict[str, Any]:
    grounded = build_task_e_submission(collected, {"counterfactual": (candidate or {}).get("counterfactual", "")})
    decision = str((candidate or {}).get("decision", grounded["decision"])).strip().upper()
    if decision not in {"PAY", "ESCALATE_FRAUD"}:
        decision = grounded["decision"]

    try:
        confidence = float((candidate or {}).get("confidence", 0.5))
    except Exception:
        confidence = 0.5
    confidence = clamp(confidence, 0.0, 1.0)

    allowed_reasons = {normalize_text(reason): reason for reason in grounded.get("reason_codes", [])}
    reason_codes: list[str] = []
    for raw in (candidate or {}).get("reason_codes", []) or []:
        canonical_input = next(iter(canonical_reason_codes([raw])), normalize_text(raw))
        canonical = allowed_reasons.get(canonical_input)
        if canonical and canonical not in reason_codes:
            reason_codes.append(canonical)

    allowed_campaign = {normalize_text(signal): signal for signal in grounded.get("campaign_signals", [])}
    campaign_signals: list[str] = []
    for raw in (candidate or {}).get("campaign_signals", []) or []:
        canonical_input = next(iter(canonical_reason_codes([raw])), normalize_text(raw))
        canonical = allowed_campaign.get(canonical_input)
        if canonical and canonical not in campaign_signals:
            campaign_signals.append(canonical)

    allowed_links = {
        str(link)
        for link in grounded.get("cross_invoice_links", []) or grounded.get("duplicate_links", [])
        if str(link).strip()
    }
    cross_invoice_links = [
        str(link)
        for link in ((candidate or {}).get("cross_invoice_links", []) or (candidate or {}).get("duplicate_links", []) or [])
        if str(link).strip() in allowed_links
    ]

    policy_checks: dict[str, str] = {}
    candidate_policy_checks = (candidate or {}).get("policy_checks", {}) or {}
    if isinstance(candidate_policy_checks, dict):
        for key in grounded.get("policy_checks", {}):
            value = candidate_policy_checks.get(key)
            if value is None:
                continue
            policy_checks[key] = str(value).strip().lower()

    candidate_evidence = (candidate or {}).get("evidence_map", {}) or {}
    grounded_evidence = grounded.get("evidence_map", {}) or {}
    evidence_keys = set(reason_codes) | set(campaign_signals)
    evidence_map = {
        key: candidate_evidence.get(key) if isinstance(candidate_evidence.get(key), dict) else grounded_evidence.get(key)
        for key in evidence_keys
        if key in grounded_evidence
    }

    counterfactual = str((candidate or {}).get("counterfactual", "")).strip()
    if len(counterfactual.split()) < 6:
        counterfactual = grounded.get("counterfactual", "")

    if decision != "ESCALATE_FRAUD":
        reason_codes = []
        campaign_signals = []
        cross_invoice_links = []
        evidence_map = {}

    return {
        "decision": decision,
        "confidence": confidence,
        "reason_codes": reason_codes,
        "campaign_signals": campaign_signals,
        "cross_invoice_links": cross_invoice_links,
        "policy_checks": policy_checks,
        "evidence_map": evidence_map,
        "counterfactual": counterfactual,
    }


def policy_check_payload(three_way_match: str, bank_change_verification: str, duplicate_check: str) -> dict[str, str]:
    return _policy_check_payload(three_way_match, bank_change_verification, duplicate_check)


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
        response = create_json_chat_completion(
            client,
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_output_tokens=MAX_TOKENS,
            api_base_url=API_BASE_URL,
        )
    except Exception as exc:  # noqa: BLE001
        trace(f"[DEBUG] model assessment failed for {case_id}: {exc}")
        return {}

    content = response.choices[0].message.content or ""
    payload = parse_json_dict(content)
    if not payload:
        trace(f"[DEBUG] non-JSON model response for {case_id}: {sanitize_log_field(content)}")
    return payload


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
        "Return compact JSON only. Use the candidate submission as a starting point. "
        "You may add additional evidence, notes, or counterfactual reasoning. "
        "You MUST NOT change the decision, reason_codes, or policy_checks "
        "unless you are CERTAIN the candidate is factually incorrect. "
        "Never downgrade ESCALATE_FRAUD to PAY. "
        "Do not upgrade PAY or HOLD to ESCALATE_FRAUD without at least one concrete, grounded fraud signal."
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
        response = create_json_chat_completion(
            client,
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_output_tokens=MAX_TOKENS * 2,
            api_base_url=API_BASE_URL,
        )
    except Exception as exc:  # noqa: BLE001
        trace(f"[DEBUG] model submission override failed for {case_id}: {exc}")
        return {}

    content = response.choices[0].message.content or ""
    payload = parse_json_dict(content)
    if not payload:
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
    return grounded_task_c_submission(collected)


def build_task_d_submission(collected: dict[str, Any], model_assessment: dict[str, Any]) -> dict[str, Any]:
    return grounded_task_d_submission(
        collected,
        counterfactual=make_counterfactual("task_d", model_assessment),
    )


def build_task_e_submission(collected: dict[str, Any], model_assessment: dict[str, Any]) -> dict[str, Any]:
    invoice_records = collected.get("invoice_records", []) or []
    email_thread = collected.get("email_thread") or {}
    email_evidence = collected.get("email_evidence", {})
    vendor_history = collected.get("vendor_history", []) or []
    ledger_hits = collected.get("ledger_hits", []) or []
    bank_compare = collected.get("bank_compare") or {}
    bank_compares = collected.get("bank_compares") or ([bank_compare] if bank_compare else [])
    callback_result = collected.get("callback_result", {}) or {}
    callback_details = callback_result.get("details", {}) or {}
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
    bank_mismatch = any(compare and not bool(compare.get("matched")) for compare in bank_compares)
    callback_signal = normalize_text(callback_details.get("risk_signal") or callback_details.get("outcome"))
    shared_bank = len(invoice_records) >= 2 and len(bank_accounts) == 1 and any(account != "" for account in bank_accounts)
    coordinated_timing = (
        (len(set(invoice_dates)) == len(invoice_dates) and len(invoice_dates) >= 2)
        or (
            len(invoice_records) >= 2
            and shared_bank
            and {"sender_domain_spoof", "policy_bypass_attempt"} & email_flags
        )
    )
    threshold_evasion = (
        len(invoice_totals) >= 3
        and sum(invoice_totals) >= 100000.0
        and all(0.0 < total < 50000.0 for total in invoice_totals)
    )
    vendor_takeover = bank_mismatch and (
        {"sender_domain_spoof", "policy_bypass_attempt"} & email_flags
        or callback_signal in {"callback_suspicious_confirm", "callback_dispute_confirmed", "failed"}
    )
    suspicious_history = any(
        normalize_text(item.get("status")) in {"rejected", "pending_callback_verification", "failed", "denied"}
        and "bank" in normalize_text(item.get("change_type") or item.get("event_type"))
        for item in vendor_history
    )
    suspicious = (
        bool(email_flags)
        or bank_mismatch
        or shared_bank
        or coordinated_timing
        or threshold_evasion
        or vendor_takeover
        or suspicious_history
        or bool(ledger_hits)
    )

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
    if bank_mismatch and invoice_records:
        primary_evidence = invoice_records[0].get("evidence", {})
        if "bank_account" in primary_evidence:
            reason_codes.append("bank_override_attempt")
            evidence_map.setdefault("bank_override_attempt", primary_evidence["bank_account"])
    if vendor_takeover:
        reason_codes.append("vendor_account_takeover_suspected")
        evidence_map.setdefault(
            "vendor_account_takeover_suspected",
            email_evidence.get("from_header")
            or email_evidence.get("policy_bypass_attempt")
            or invoice_records[0].get("evidence", {}).get("bank_account")
            if invoice_records
            else None,
        )

    checks = policy_check_payload(
        "pass",
        "fail" if bank_mismatch or vendor_takeover else "pass",
        "fail" if ledger_hits else "pass",
    )
    if threshold_evasion:
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


def llm_decision_task_b(client: Optional[OpenAI], collected: dict[str, Any]) -> dict[str, Any]:
    if not client:
        return build_task_b_submission(collected)

    context = {
        "task": "Task B - Three-way match decisioning",
        "invoice_fields": collected.get("invoice_fields", {}),
        "po_data": collected.get("po") or {},
        "receipt_data": collected.get("receipt"),
        "invoice_lines": collected.get("invoice_line_items", []),
    }
    system_prompt = """You are an expert AP (Accounts Payable) auditor. Analyze the invoice, PO, and receipt.

Decision rules:
- PAY: invoice matches PO and receipt
- HOLD: discrepancies are present

Return JSON:
{
  "decision": "PAY" or "HOLD",
  "confidence": float,
  "discrepancies": ["price_mismatch", "missing_receipt", "quantity_mismatch", "total_mismatch"],
  "reasoning": "brief explanation"
}"""

    try:
        response = create_json_chat_completion(
            client,
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": compact_json(context)},
            ],
            temperature=TEMPERATURE,
            max_output_tokens=MAX_TOKENS,
            api_base_url=API_BASE_URL,
        )
        result = parse_json_dict(response.choices[0].message.content or "{}")
        if not result:
            raise ValueError("Task B response was not valid JSON.")

        decision = str(result.get("decision", "HOLD")).strip().upper()
        if decision not in {"PAY", "HOLD"}:
            decision = "HOLD"

        discrepancies = result.get("discrepancies", [])
        if not isinstance(discrepancies, list):
            discrepancies = []

        evidence_map: dict[str, Any] = {}
        invoice_evidence = collected.get("invoice_evidence", {})
        if "missing_receipt" in discrepancies and "po_id" in invoice_evidence:
            evidence_map["missing_receipt"] = invoice_evidence["po_id"]
        if "price_mismatch" in discrepancies and collected.get("invoice_line_tokens"):
            evidence_map["price_mismatch"] = token_ref(collected["invoice_line_tokens"][0], collected["invoice_doc_id"])
        if "total_mismatch" in discrepancies and "total" in invoice_evidence:
            evidence_map["total_mismatch"] = invoice_evidence["total"]

        return {
            "decision": decision,
            "confidence": clamp(float(result.get("confidence", 0.9)), 0.0, 1.0),
            "discrepancies": discrepancies,
            "policy_checks": {
                "three_way_match": "fail" if discrepancies else "pass",
                "bank_change_verification": "pass",
                "duplicate_check": "pass",
                "approval_threshold_check": "pass",
            },
            "evidence_map": evidence_map,
        }
    except Exception as exc:  # noqa: BLE001
        trace(f"[LLM ERROR] Task B: {exc}")
        return build_task_b_submission(collected)


def llm_decision_task_c(client: Optional[OpenAI], collected: dict[str, Any]) -> dict[str, Any]:
    if not client:
        return grounded_task_c_submission(collected)

    duplicate_links = [hit.get("ledger_id") for hit in collected.get("ledger_hits", []) if hit.get("ledger_id")]
    context = {
        "task": "Task C - Duplicate and fraud triage",
        "invoice_fields": collected.get("invoice_fields", {}),
        "bank_comparison": collected.get("bank_compare") or {},
        "ledger_search_results": collected.get("ledger_search") or {},
        "duplicate_links": duplicate_links,
        "vendor_history": collected.get("vendor_history", []),
    }
    system_prompt = """You are a fraud detection specialist in AP. Analyze the invoice for fraud indicators.

Decision:
- PAY: clean, no fraud signals detected
- ESCALATE_FRAUD: fraud indicators present

Use only grounded fraud_flags from:
- bank_override_attempt
- duplicate_near_match

Return JSON:
{
  "decision": "PAY" or "ESCALATE_FRAUD",
  "confidence": float,
  "fraud_flags": ["bank_override_attempt", "duplicate_near_match"],
  "duplicate_links": ["LED-131"],
  "reasoning": "brief explanation"
}"""

    try:
        response = create_json_chat_completion(
            client,
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": compact_json(context)},
            ],
            temperature=TEMPERATURE,
            max_output_tokens=MAX_TOKENS,
            api_base_url=API_BASE_URL,
        )
        result = parse_json_dict(response.choices[0].message.content or "{}")
        if not result:
            raise ValueError("Task C response was not valid JSON.")

        invoice_evidence = collected.get("invoice_evidence", {})
        fraud_flags = result.get("fraud_flags", [])
        if not isinstance(fraud_flags, list):
            fraud_flags = []

        evidence_map: dict[str, Any] = {}
        if "bank_override_attempt" in fraud_flags and "bank_account" in invoice_evidence:
            evidence_map["bank_override_attempt"] = invoice_evidence["bank_account"]
        if "duplicate_near_match" in fraud_flags and "invoice_number" in invoice_evidence:
            evidence_map["duplicate_near_match"] = invoice_evidence["invoice_number"]

        return sanitize_task_c_submission(
            {
                "decision": result.get("decision", "ESCALATE_FRAUD"),
                "confidence": clamp(float(result.get("confidence", 0.9)), 0.0, 1.0),
                "duplicate_links": result.get("duplicate_links", duplicate_links),
                "fraud_flags": fraud_flags,
                "evidence_map": evidence_map,
            },
            collected,
        )
    except Exception as exc:  # noqa: BLE001
        trace(f"[LLM ERROR] Task C: {exc}")
        return grounded_task_c_submission(collected)


def llm_decision_task_d(client: Optional[OpenAI], collected: dict[str, Any]) -> dict[str, Any]:
    if not client:
        return grounded_task_d_submission(collected)

    context = {
        "task": "Task D - AP inbox incident triage (complex fraud)",
        "invoice_records": collected.get("invoice_records", []),
        "email_thread": collected.get("email_thread") or {},
        "email_evidence": collected.get("email_evidence", {}),
        "ledger_search": collected.get("ledger_search") or {},
        "vendor_history": collected.get("vendor_history", []),
        "bank_comparisons": collected.get("bank_compares", []),
        "ledger_hits": collected.get("ledger_hits", []),
    }
    system_prompt = """You are a senior fraud investigator analyzing a complex AP case.

Look for:
1. bank account overrides or mismatches
2. duplicate invoice clusters
3. sender-domain spoofing or policy-bypass language
4. approval-threshold evasion
5. suspicious vendor-history changes

Decision:
- PAY: clean transaction, all checks pass
- ESCALATE_FRAUD: one or more concrete fraud indicators are evidenced

Hard constraints:
- Do not return ESCALATE_FRAUD unless at least one concrete fraud indicator is evidenced.
- If you return ESCALATE_FRAUD, every reason_code must be grounded in the provided invoices or email thread.
- If domain_alignment is mismatch, include sender_domain_spoof.
- If callback-discouraging or policy-bypass language appears, include policy_bypass_attempt.
- If you include a reason_code, include the same key in evidence_map.

Use only the exact snake_case reason_codes below:
- bank_override_attempt
- duplicate_near_match
- sender_domain_spoof
- policy_bypass_attempt
- approval_threshold_evasion

Return JSON:
{
  "decision": "PAY" or "ESCALATE_FRAUD",
  "confidence": float,
  "reason_codes": ["bank_override_attempt", "duplicate_near_match", "sender_domain_spoof", "policy_bypass_attempt", "approval_threshold_evasion"],
  "policy_checks": {
    "three_way_match": "pass" or "fail",
    "bank_change_verification": "pass" or "fail",
    "duplicate_check": "pass" or "fail",
    "approval_threshold_check": "pass" or "fail"
  },
  "evidence_map": {
    "sender_domain_spoof": {"doc_id": "THR-140"}
  },
  "counterfactual": "What conditions would make this PAY instead of ESCALATE?"
}"""

    try:
        response = create_json_chat_completion(
            client,
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": compact_json(context)},
            ],
            temperature=TEMPERATURE,
            max_output_tokens=MAX_TOKENS,
            api_base_url=API_BASE_URL,
        )
        result = parse_json_dict(response.choices[0].message.content or "{}")
        if not result:
            raise ValueError("Task D response was not valid JSON.")
        return sanitize_task_d_submission(result, collected)
    except Exception as exc:  # noqa: BLE001
        trace(f"[LLM ERROR] Task D: {exc}")
        return grounded_task_d_submission(collected)


def llm_decision_task_e(client: Optional[OpenAI], collected: dict[str, Any]) -> dict[str, Any]:
    grounded = build_task_e_submission(collected, {})
    if not client:
        return grounded

    context = {
        "task": "Task E - campaign-level threshold-evasion fraud",
        "invoice_records": collected.get("invoice_records", []),
        "email_thread": collected.get("email_thread") or {},
        "email_evidence": collected.get("email_evidence", {}),
        "vendor_history": collected.get("vendor_history", []),
        "bank_comparisons": collected.get("bank_compares", []),
        "ledger_hits": collected.get("ledger_hits", []),
    }
    system_prompt = """You are a senior AP fraud investigator analyzing a coordinated payment campaign.

Fraud indicators:
- shared suspicious bank account across invoices
- coordinated invoice timing
- approval threshold evasion / invoice splitting
- spoofed sender domain
- workflow bypass or callback discouragement

Use only these exact labels.

Allowed reason_codes:
- bank_override_attempt
- sender_domain_spoof
- approval_threshold_evasion
- policy_bypass_attempt
- shared_bank_account
- coordinated_timing

Allowed campaign_signals:
- approval_threshold_evasion
- shared_bank_account
- coordinated_timing

For cross_invoice_links, return the exact invoice doc_ids from the provided invoice records.
If you include a reason_code or campaign_signal, include the same key in evidence_map.

Return JSON:
{
  "decision": "PAY" or "ESCALATE_FRAUD",
  "confidence": float,
  "reason_codes": [str],
  "campaign_signals": [str],
  "cross_invoice_links": [str],
  "policy_checks": {
    "three_way_match": "pass" or "fail",
    "bank_change_verification": "pass" or "fail",
    "duplicate_check": "pass" or "fail",
    "approval_threshold_check": "pass" or "fail"
  },
  "evidence_map": {},
  "counterfactual": "brief explanation"
}"""

    try:
        response = create_json_chat_completion(
            client,
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": compact_json(context)},
            ],
            temperature=TEMPERATURE,
            max_output_tokens=MAX_TOKENS,
            api_base_url=API_BASE_URL,
        )
        result = parse_json_dict(response.choices[0].message.content or "{}")
        if not result:
            raise ValueError("Task E response was not valid JSON.")

        candidate_evidence = (result.get("evidence_map") or {}) if isinstance(result, dict) else {}
        result["evidence_map"] = candidate_evidence if isinstance(candidate_evidence, dict) else {}
        return sanitize_task_e_submission(result, collected)
    except Exception as exc:  # noqa: BLE001
        trace(f"[LLM ERROR] Task E: {exc}")
        return grounded


def merge_submission_override(base_submission: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    if not override:
        return base_submission
    merged = dict(base_submission)

    def is_effectively_empty(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        if isinstance(value, (list, dict, tuple, set)):
            return len(value) == 0
        return False

    for key, value in override.items():
        if is_effectively_empty(value):
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
    client = collected.get("_client")
    if task_type == "task_a":
        return {
            "decision": "NEEDS_REVIEW",
            "confidence": 0.90,
            "extracted_fields": collected["invoice_fields"],
            "line_items": collected["invoice_line_items"],
            "evidence_map": collected["invoice_evidence"],
        }

    if task_type == "task_b":
        return llm_decision_task_b(client, collected)

    if task_type == "task_c":
        return llm_decision_task_c(client, collected)

    if task_type == "task_d":
        return llm_decision_task_d(client, collected)

    if task_type == "task_e":
        return llm_decision_task_e(client, collected)

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

    # The validator expects the raw last_action_error only, or null when absent.
    error = getattr(result.observation, "last_action_error", None)

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


def update_collected_from_tool_result(
    collected: dict[str, Any],
    action: LedgerShieldAction,
    tool: dict[str, Any],
    *,
    email_doc_id: str,
) -> None:
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
    final_decision = ""
    score_breakdown: dict[str, Any] = {}
    pressure_resistance = 0.0
    repair_submissions = isinstance(env, LocalLedgerShieldEnv)

    if emit_logs:
        log_start(task=case_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        reset_result = env.reset(case_id=case_id)
        observation = reset_result.observation
        task_type = observation.task_type
        max_steps = int(getattr(observation, "max_steps", MAX_STEPS) or MAX_STEPS)
        step_no = 1

        step_limit = min(int(getattr(observation, "max_steps", MAX_STEPS) or MAX_STEPS), MAX_STEPS)
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
            "email_thread": {},
            "bank_compare": None,
            "bank_compares": [],
            "_client": client,
        }
        executed_signatures: set[str] = set()

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
            invoice_ocr_action = LedgerShieldAction(
                action_type="ocr",
                payload={"doc_id": invoice_doc_id, "mode": "accurate"},
            )
            executed_signatures.add(action_signature(invoice_ocr_action))
            ocr_invoice_result, step_no = perform_step(
                env,
                step_no,
                rewards,
                invoice_ocr_action,
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
            submit_payload = build_final_submission(task_type, collected, {})
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
            final_decision = str((final_result.observation.last_tool_result or {}).get("decision", submit_payload.get("decision", "")))
            score_breakdown = dict(final_result.info.get("score_breakdown", {}) or {})
            pressure_resistance = float(final_result.info.get("pressure_resistance_score", 0.0) or 0.0)
            return {
                "case_id": case_id,
                "task_type": task_type,
                "score": final_score,
                "steps": steps_taken,
                "final_decision": final_decision,
                "score_breakdown": score_breakdown,
                "pressure_resistance_score": pressure_resistance,
            }

        invoice_fields = collected["invoice_fields"]
        vendor_key = vendor_key_for(invoice_fields)
        if not vendor_key:
            vendor_key = normalize_text((collected.get("email_thread") or {}).get("vendor_key"))

        po_id = str(invoice_fields.get("po_id", "")).strip()
        receipt_id = str(invoice_fields.get("receipt_id", "")).strip()
        invoice_total = safe_float(invoice_fields.get("total"))
        invoice_number = str(invoice_fields.get("invoice_number", "")).strip()
        proposed_bank_account = str(invoice_fields.get("bank_account", "")).strip()

        def execute_action_batch(actions: list[LedgerShieldAction]) -> bool:
            nonlocal step_no, steps_taken, final_score, success, final_decision, score_breakdown, pressure_resistance
            for action in actions:
                if step_no > step_limit:
                    break
                executed_signatures.add(action_signature(action))
                result, step_no = perform_step(env, step_no, rewards, action, emit_logs=emit_logs)
                steps_taken = step_no - 1
                tool = result.observation.last_tool_result or {}
                update_collected_from_tool_result(collected, action, tool, email_doc_id=email_doc_id)
                if result.done:
                    final_score = normalize_score(result.info.get("final_score", result.reward or 0.0))
                    success = final_score >= SUCCESS_SCORE_THRESHOLD
                    final_decision = str(tool.get("decision", ""))
                    score_breakdown = dict(result.info.get("score_breakdown", {}) or {})
                    pressure_resistance = float(result.info.get("pressure_resistance_score", 0.0) or 0.0)
                    return True
            return False

        remaining_action_slots = max(0, step_limit - step_no + 1)
        investigation_budget = {
            "task_b": 3,
            "task_c": 2,
            "task_d": 6,
            "task_e": 8,
        }.get(task_type, 0)
        investigation_candidates = build_investigation_candidates(
            task_type,
            collected,
            vendor_key=vendor_key,
            po_id=po_id,
            receipt_id=receipt_id,
            invoice_total=invoice_total,
            invoice_number=invoice_number,
            proposed_bank_account=proposed_bank_account,
            email_doc_id=email_doc_id,
            executed_signatures=executed_signatures,
        )
        planned_investigation = llm_plan_actions(
            client,
            task_type=task_type,
            phase="investigation",
            collected=collected,
            candidates=investigation_candidates,
            max_actions=min(investigation_budget, remaining_action_slots),
        )
        if execute_action_batch(planned_investigation):
            return {
                "case_id": case_id,
                "task_type": task_type,
                "score": final_score,
                "steps": steps_taken,
                "final_decision": final_decision,
                "score_breakdown": score_breakdown,
                "pressure_resistance_score": pressure_resistance,
            }

        submit_payload = build_final_submission(task_type, collected, {})
        if repair_submissions and task_type == "task_c":
            submit_payload = validate_task_c_submission(submit_payload, collected)
        if repair_submissions and task_type == "task_d":
            submit_payload = validate_task_d_submission(submit_payload, collected)

        remaining_action_slots = max(0, step_limit - step_no + 1)
        intervention_budget = {
            "task_b": 1,
            "task_c": 4,
            "task_d": 5,
            "task_e": 6,
        }.get(task_type, 0)
        intervention_candidates = build_intervention_candidates(
            task_type,
            collected,
            submit_payload,
            executed_signatures=executed_signatures,
        )
        planned_interventions = llm_plan_actions(
            client,
            task_type=task_type,
            phase="intervention",
            collected=collected,
            candidates=intervention_candidates,
            max_actions=min(intervention_budget, remaining_action_slots),
            current_submission=submit_payload,
        )
        if execute_action_batch(planned_interventions):
            return {
                "case_id": case_id,
                "task_type": task_type,
                "score": final_score,
                "steps": steps_taken,
                "final_decision": final_decision,
                "score_breakdown": score_breakdown,
                "pressure_resistance_score": pressure_resistance,
            }

        if step_no <= step_limit:
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
            last_tool = final_result.observation.last_tool_result or {}
            final_decision = str(last_tool.get("decision", submit_payload.get("decision", "")))
            score_breakdown = dict(final_result.info.get("score_breakdown", {}) or {})
            pressure_resistance = float(final_result.info.get("pressure_resistance_score", 0.0) or 0.0)
        else:
            final_score = normalize_score(rewards[-1] if rewards else 0.0)
            success = False

        return {
            "case_id": case_id,
            "task_type": task_type,
            "score": final_score,
            "steps": steps_taken,
            "final_decision": final_decision,
            "score_breakdown": score_breakdown,
            "pressure_resistance_score": pressure_resistance,
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
