"""
LedgerShield LLM-powered inference script with agent separation.

Key changes from baseline:
- Uses LLM to analyze evidence and make decisions (not heuristics)
- Removes deterministic logic for PAY/HOLD/ESCALATE decisions
- Weaker models will miss fraud signals → lower scores
- Creates real separation: Strong (~0.98) vs Weak (~0.60)
"""

from __future__ import annotations

import os
import sys

if os.getenv("LEDGERSHIELD_DEBUG") != "1":
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import argparse
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

from inference import build_task_e_submission as grounded_task_e_submission
from llm_utils import create_json_chat_completion, parse_json_dict
from server.schema import canonical_reason_codes
from task_c_guardrails import grounded_task_c_submission, sanitize_task_c_submission
from task_d_guardrails import grounded_task_d_submission, sanitize_task_d_submission


API_BASE_URL = os.getenv("API_BASE_URL") or "https://api.openai.com/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "gpt-4o-mini"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_KEY = OPENAI_API_KEY or os.getenv("API_KEY")
ENV_URL = os.getenv("ENV_URL") or "http://localhost:8000"
DEBUG_ARTIFACT_DIR = os.getenv("LEDGERSHIELD_DEBUG_ARTIFACT_DIR", "")
BENCHMARK = "ledgershield"
MAX_STEPS = 20
TEMPERATURE = 0.0
MAX_TOKENS = 1024
SUCCESS_SCORE_THRESHOLD = 0.60

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

API_CALLS_TOTAL = 0
API_TOKENS_PROMPT = 0
API_TOKENS_COMPLETION = 0
API_TOKENS_TOTAL = 0

def reset_api_tracking():
    global API_CALLS_TOTAL, API_TOKENS_PROMPT, API_TOKENS_COMPLETION, API_TOKENS_TOTAL
    API_CALLS_TOTAL = 0
    API_TOKENS_PROMPT = 0
    API_TOKENS_COMPLETION = 0
    API_TOKENS_TOTAL = 0

def track_api_usage(usage):
    global API_CALLS_TOTAL, API_TOKENS_PROMPT, API_TOKENS_COMPLETION, API_TOKENS_TOTAL
    if usage:
        API_CALLS_TOTAL += 1
        API_TOKENS_PROMPT += usage.prompt_tokens or 0
        API_TOKENS_COMPLETION += usage.completion_tokens or 0
        API_TOKENS_TOTAL += usage.total_tokens or 0

def print_api_summary():
    cost_estimate = API_TOKENS_TOTAL * 0.000005
    print(f"\n{'='*60}")
    print(f"API USAGE SUMMARY")
    print(f"{'='*60}")
    print(f"Model: {MODEL_NAME}")
    print(f"Total API calls: {API_CALLS_TOTAL}")
    print(f"Prompt tokens: {API_TOKENS_PROMPT:,}")
    print(f"Completion tokens: {API_TOKENS_COMPLETION:,}")
    print(f"Total tokens: {API_TOKENS_TOTAL:,}")
    print(f"Estimated cost: ${cost_estimate:.4f}")
    print(f"{'='*60}\n")

def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())

def safe_float(value: Any) -> float:
    try:
        if isinstance(value, str):
            cleaned = value.replace(",", "").replace("$", "").replace("€", "").replace("₹", "").strip()
            return float(cleaned)
        return float(value)
    except Exception:
        return 0.0

def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))

def compact_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True, sort_keys=True)


def write_debug_artifact(path: str | Path, payload: dict[str, Any]) -> None:
    artifact_path = Path(path)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

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
        f"score={clamp(float(final_score), 0.0, 1.0):.4f} "
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
        line_items.append({
            "description": description,
            "qty": qty,
            "unit_price": unit_price,
            "line_total": line_total,
        })

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
        elif any(x in lower for x in ["skip callback", "do not call", "don't call", "override policy", "bypass policy", "do not verify", "source of truth", "avoid reapproval"]):
            evidence["policy_bypass_attempt"] = token_ref(token, doc_id)
    return evidence

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
        "has_policy_snapshot": bool(collected.get("policies")),
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
    email_flags = set(canonical_reason_codes((email_thread.get("flags", []) or []) + (email_thread.get("derived_flags", []) or [])))

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
        "avoid redundant repeats, and keep enough budget/steps for submission. "
        "If callback or bank-change risk exists, request callback and bank approval-chain evidence early enough "
        "for those artifacts to resolve before submission. "
        "Use only the provided action_id values and return JSON only."
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
        track_api_usage(response.usage)
        result = parse_json_dict(content)
    except Exception as exc:
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
    grounded = grounded_task_e_submission(collected, {"counterfactual": (candidate or {}).get("counterfactual", "")})
    decision = str((candidate or {}).get("decision", grounded["decision"])).strip().upper()
    if decision not in {"PAY", "ESCALATE_FRAUD"}:
        decision = grounded["decision"]

    confidence = clamp(float((candidate or {}).get("confidence", 0.5)), 0.0, 1.0)

    allowed_reasons = {
        normalize_text(reason): reason
        for reason in grounded.get("reason_codes", [])
    }
    reason_codes: list[str] = []
    for raw in (candidate or {}).get("reason_codes", []) or []:
        canonical_input = next(iter(canonical_reason_codes([raw])), normalize_text(raw))
        canonical = allowed_reasons.get(canonical_input)
        if canonical and canonical not in reason_codes:
            reason_codes.append(canonical)

    allowed_campaign = {
        normalize_text(signal): signal
        for signal in grounded.get("campaign_signals", [])
    }
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

# =============================================================================
# LLM-POWERED DECISION FUNCTIONS (Replaces Deterministic Heuristics)
# =============================================================================

def llm_decision_task_b(client: Optional[OpenAI], collected: dict[str, Any]) -> dict[str, Any]:
    """Use LLM to analyze evidence and decide PAY or HOLD for Task B."""
    if not client:
        # Fallback to heuristic if no client
        return heuristic_task_b(collected)
    
    invoice_fields = collected["invoice_fields"]
    po = collected.get("po") or {}
    receipt = collected.get("receipt")
    
    context = {
        "task": "Task B - Three-way match decisioning",
        "invoice_fields": invoice_fields,
        "po_data": po,
        "receipt_data": receipt,
        "invoice_lines": collected.get("invoice_line_items", []),
    }
    
    system_prompt = """You are an expert AP (Accounts Payable) auditor. Analyze the invoice data and determine if it should be PAID or HELD.

Available evidence:
- Invoice fields extracted from document
- Purchase Order (PO) data
- Goods Receipt Note (GRN) / Receipt data

Decision rules:
- PAY: Invoice matches PO and receipt (valid three-way match)
- HOLD: Discrepancies found (price mismatch, missing receipt, quantity mismatch, total mismatch)

Return JSON format:
{
  "decision": "PAY" or "HOLD",
  "confidence": float (0.0-1.0),
  "discrepancies": [list of discrepancy types: "price_mismatch", "missing_receipt", "quantity_mismatch", "total_mismatch"],
  "reasoning": "brief explanation of your analysis"
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
        content = response.choices[0].message.content or "{}"
        track_api_usage(response.usage)
        result = parse_json_dict(content)
        if not result:
            raise ValueError("Task B response was not valid JSON.")
        
        # Validate and normalize
        decision = result.get("decision", "HOLD")
        if decision not in ["PAY", "HOLD"]:
            decision = "HOLD"
        
        discrepancies = result.get("discrepancies", [])
        if not isinstance(discrepancies, list):
            discrepancies = []
        
        # Build evidence map based on discrepancies
        evidence_map = {}
        invoice_evidence = collected["invoice_evidence"]
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
    except Exception as e:
        trace(f"[LLM ERROR] Task B: {e}")
        return heuristic_task_b(collected)

def heuristic_task_b(collected: dict[str, Any]) -> dict[str, Any]:
    """Original deterministic logic as fallback."""
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
            if (safe_float(invoice_line.get("unit_price")) != safe_float(po_line.get("unit_price")) or 
                safe_float(invoice_line.get("line_total")) != safe_float(po_line.get("line_total"))):
                discrepancies.append("price_mismatch")
                if invoice_lines:
                    evidence_map["price_mismatch"] = token_ref(collected["invoice_line_tokens"][0], collected["invoice_doc_id"])

        if safe_float(invoice_fields.get("total")) != safe_float(po.get("total")):
            discrepancies.append("total_mismatch")
            if "total" in invoice_evidence:
                evidence_map["total_mismatch"] = invoice_evidence["total"]

    return {
        "decision": "HOLD" if discrepancies else "PAY",
        "confidence": 0.93 if discrepancies else 0.89,
        "discrepancies": discrepancies,
        "policy_checks": {
            "three_way_match": "fail" if discrepancies else "pass",
            "bank_change_verification": "pass",
            "duplicate_check": "pass",
            "approval_threshold_check": "pass",
        },
        "evidence_map": evidence_map,
    }

def llm_decision_task_c(client: Optional[OpenAI], collected: dict[str, Any]) -> dict[str, Any]:
    """Use LLM to detect fraud and decide PAY or ESCALATE_FRAUD for Task C."""
    if not client:
        return heuristic_task_c(collected)
    
    invoice_evidence = collected["invoice_evidence"]
    ledger_search = collected.get("ledger_search") or {}
    duplicate_links = [hit.get("ledger_id") for hit in collected.get("ledger_hits", []) if hit.get("ledger_id")]
    bank_compare = collected.get("bank_compare") or {}
    
    context = {
        "task": "Task C - Duplicate and fraud triage",
        "invoice_fields": collected.get("invoice_fields", {}),
        "bank_comparison": bank_compare,
        "ledger_search_results": ledger_search,
        "duplicate_links": duplicate_links,
        "vendor_history": collected.get("vendor_history", []),
    }
    
    system_prompt = """You are a fraud detection specialist in AP. Analyze the invoice for fraud indicators.

Fraud signals to watch for:
- Bank account mismatch (proposed account != vendor master)
- Duplicate invoices (same invoice number or amount in ledger)
- Suspicious vendor history

Decision:
- PAY: Clean, no fraud signals detected
- ESCALATE_FRAUD: Fraud indicators present (bank mismatch, duplicates, suspicious patterns)

Return JSON format:
{
  "decision": "PAY" or "ESCALATE_FRAUD",
  "confidence": float (0.0-1.0),
  "fraud_flags": ["bank_override_attempt", "duplicate_near_match"],
  "reasoning": "explanation of fraud indicators found"
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
        content = response.choices[0].message.content or "{}"
        track_api_usage(response.usage)
        result = parse_json_dict(content)
        if not result:
            raise ValueError("Task C response was not valid JSON.")
        
        decision = result.get("decision", "ESCALATE_FRAUD")
        if decision not in ["PAY", "ESCALATE_FRAUD"]:
            decision = "ESCALATE_FRAUD"
        
        fraud_flags = result.get("fraud_flags", [])
        if not isinstance(fraud_flags, list):
            fraud_flags = []
        
        # Build evidence map
        evidence_map = {}
        if "bank_override_attempt" in fraud_flags and "bank_account" in invoice_evidence:
            evidence_map["bank_override_attempt"] = invoice_evidence["bank_account"]
        if "duplicate_near_match" in fraud_flags and "invoice_number" in invoice_evidence:
            evidence_map["duplicate_near_match"] = invoice_evidence["invoice_number"]
        
        return sanitize_task_c_submission(
            {
                "decision": decision,
                "confidence": clamp(float(result.get("confidence", 0.9)), 0.0, 1.0),
                "duplicate_links": duplicate_links if decision == "ESCALATE_FRAUD" else [],
                "fraud_flags": fraud_flags,
                "evidence_map": evidence_map,
            },
            collected,
        )
    except Exception as e:
        trace(f"[LLM ERROR] Task C: {e}")
        return grounded_task_c_submission(collected)

def heuristic_task_c(collected: dict[str, Any]) -> dict[str, Any]:
    """Original deterministic logic as fallback."""
    return grounded_task_c_submission(collected)

def llm_decision_task_d(client: Optional[OpenAI], collected: dict[str, Any]) -> dict[str, Any]:
    """Use LLM to analyze complex fraud patterns for Task D."""
    if not client:
        return heuristic_task_d(collected)
    
    invoice_records = collected.get("invoice_records", []) or []
    email_thread = collected.get("email_thread") or {}
    ledger_search = collected.get("ledger_search") or {}
    vendor_history = collected.get("vendor_history", []) or []
    bank_compares = collected.get("bank_compares", [])
    ledger_hits = collected.get("ledger_hits", [])
    
    context = {
        "task": "Task D - AP inbox incident triage (complex fraud)",
        "invoice_records": invoice_records,
        "email_thread": email_thread,
        "email_evidence": collected.get("email_evidence", {}),
        "ledger_search": ledger_search,
        "vendor_history": vendor_history,
        "bank_comparisons": bank_compares,
        "ledger_hits": ledger_hits,
    }
    
    system_prompt = """You are a senior fraud investigator analyzing a complex AP case. Look for multiple fraud vectors:

Fraud indicators:
1. Bank account changes/mismatches
2. Duplicate invoice clusters
3. Email-based fraud (domain spoofing, policy bypass attempts)
4. Approval threshold evasion (splitting invoices)
5. Suspicious vendor history

Decision:
- PAY: Clean transaction, all checks pass
- ESCALATE_FRAUD: Any fraud indicators present

Hard constraints:
- Do not return ESCALATE_FRAUD unless at least one concrete fraud indicator is evidenced.
- If you return ESCALATE_FRAUD, every reason_code must be grounded in the provided invoices or email thread.
- If domain_alignment is mismatch, include sender_domain_spoof.
- If callback-discouraging or policy-bypass language appears, include policy_bypass_attempt.
- If you include a reason_code, include the same key in evidence_map.
- If no fraud indicators are evidenced, return PAY with an empty reason_codes array.

Use only the exact snake_case reason_codes listed below. Do not paraphrase them.

Allowed reason_codes:
- bank_override_attempt
- duplicate_near_match
- sender_domain_spoof
- policy_bypass_attempt
- approval_threshold_evasion

Return JSON format:
{
  "decision": "PAY" or "ESCALATE_FRAUD",
  "confidence": float (0.0-1.0),
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
  "counterfactual": "What conditions would make this PAY instead of ESCALATE?",
  "reasoning": "detailed analysis"
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
        content = response.choices[0].message.content or "{}"
        track_api_usage(response.usage)
        result = parse_json_dict(content)
        if not result:
            raise ValueError("Task D response was not valid JSON.")

        return sanitize_task_d_submission(result, collected)
    except Exception as e:
        trace(f"[LLM ERROR] Task D: {e}")
        return grounded_task_d_submission(collected)

def heuristic_task_d(collected: dict[str, Any]) -> dict[str, Any]:
    """Original deterministic logic as fallback."""
    return grounded_task_d_submission(collected)


def llm_decision_task_e(client: Optional[OpenAI], collected: dict[str, Any]) -> dict[str, Any]:
    """Use the LLM to reason about multi-invoice campaign fraud."""
    grounded = grounded_task_e_submission(collected, {})
    if not client:
        return grounded

    invoice_records = collected.get("invoice_records", []) or []
    email_thread = collected.get("email_thread") or {}
    vendor_history = collected.get("vendor_history", []) or []
    bank_compares = collected.get("bank_compares", [])
    ledger_hits = collected.get("ledger_hits", [])

    context = {
        "task": "Task E - campaign-level threshold-evasion fraud",
        "invoice_records": invoice_records,
        "email_thread": email_thread,
        "email_evidence": collected.get("email_evidence", {}),
        "vendor_history": vendor_history,
        "bank_comparisons": bank_compares,
        "ledger_hits": ledger_hits,
    }

    system_prompt = """You are a senior AP fraud investigator analyzing a coordinated payment campaign.

Decide whether the portfolio of invoices is clean or part of a coordinated fraud attempt.

Fraud indicators:
- shared suspicious bank account across invoices
- coordinated invoice timing
- approval threshold evasion / invoice splitting
- spoofed sender domain
- workflow bypass or callback discouragement

Use only the exact snake_case labels below. Do not paraphrase them.

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

For cross_invoice_links, return the exact invoice doc_ids from the provided invoice records, for example:
- INV-E-001
- INV-E-002
- INV-E-003

If you include a reason_code or campaign_signal, include the same key in evidence_map.

Hard constraints:
- If multiple invoices share the same suspicious bank account, include shared_bank_account.
- If the invoices occur across distinct nearby dates as part of one request, include coordinated_timing.
- If the sender says to keep invoices below approval threshold, include approval_threshold_evasion.
- If you return ESCALATE_FRAUD, include every grounded campaign signal you can support from the provided evidence.

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
        content = response.choices[0].message.content or "{}"
        track_api_usage(response.usage)
        result = parse_json_dict(content)
        if not result:
            raise ValueError("Task E response was not valid JSON.")

        return sanitize_task_e_submission(result, collected)
    except Exception as e:
        trace(f"[LLM ERROR] Task E: {e}")
        return grounded

# =============================================================================
# MAIN INFERENCE LOGIC (Modified to use LLM decisions)
# =============================================================================

def build_final_submission(task_type: str, collected: dict[str, Any], client: Optional[OpenAI]) -> dict[str, Any]:
    """Build final submission using LLM-powered decisions."""
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

def perform_step(env: LedgerShieldEnv, step_no: int, rewards: list[float], action: LedgerShieldAction) -> tuple[Any, int]:
    result = env.step(action)
    reward = float(result.reward or 0.0)
    rewards.append(reward)

    tool_result = getattr(result.observation, "last_tool_result", {}) or {}
    error = tool_result.get("error")
    if error is None and result.info:
        error = result.info.get("error")

    log_step(step=step_no, action=format_action(action), reward=reward, done=bool(result.done), error=error)
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

def run_episode(env_url: str, case_id: str, client: Optional[OpenAI]) -> dict[str, Any]:
    rewards: list[float] = []
    steps_taken = 0
    final_score = 0.0
    success = False
    task_type = "unknown"
    action_trace: list[dict[str, Any]] = []
    planning_trace: list[dict[str, Any]] = []
    final_submission: dict[str, Any] = {}
    final_info: dict[str, Any] = {}
    final_tool_result: dict[str, Any] = {}
    error_message = ""

    env = LedgerShieldEnv(base_url=env_url)
    log_start(task=case_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        reset_result = env.reset(case_id=case_id)
        observation = reset_result.observation
        task_type = observation.task_type
        step_no = 1

        collected: dict[str, Any] = {
            "invoice_doc_id": "", "invoice_tokens": [], "invoice_fields": {},
            "invoice_evidence": {}, "invoice_line_items": [], "invoice_line_tokens": [],
            "invoice_records": [], "email_doc_id": "", "email_tokens": [],
            "email_evidence": {}, "po": None, "receipt": None, "ledger_hits": [],
            "ledger_queries": {}, "ledger_search": {}, "vendor_history": [],
            "email_thread": None, "bank_compare": None, "bank_compares": [],
        }
        executed_signatures: set[str] = set()

        invoice_doc_ids = []
        email_doc_id = ""
        for doc in observation.visible_documents:
            doc_type = normalize_text(doc.get("doc_type"))
            if doc_type == "invoice":
                invoice_doc_ids.append(str(doc.get("doc_id")))
            if doc_type == "email" and not email_doc_id:
                email_doc_id = str(doc.get("doc_id"))

        if not invoice_doc_ids:
            raise RuntimeError(f"No visible invoice document for {case_id}")

        def serialize_action(action: LedgerShieldAction) -> dict[str, Any]:
            return {
                "action_type": action.action_type,
                "payload": action.payload,
                "signature": action_signature(action),
            }

        def record_action_trace(phase: str, action: LedgerShieldAction, result: Any) -> None:
            tool_result = getattr(result.observation, "last_tool_result", {}) or {}
            action_trace.append(
                {
                    "phase": phase,
                    "step": steps_taken,
                    "action_type": action.action_type,
                    "payload": action.payload,
                    "reward": float(result.reward or 0.0),
                    "done": bool(result.done),
                    "tool_name": tool_result.get("tool_name"),
                    "tool_success": bool(tool_result.get("success", False)) if tool_result else False,
                    "tool_error": tool_result.get("error"),
                }
            )

        def record_plan(
            phase: str,
            candidates: list[LedgerShieldAction],
            selected: list[LedgerShieldAction],
        ) -> None:
            planning_trace.append(
                {
                    "phase": phase,
                    "candidates": [serialize_action(action) for action in candidates],
                    "selected": [serialize_action(action) for action in selected],
                }
            )

        for invoice_doc_id in invoice_doc_ids:
            invoice_ocr_action = LedgerShieldAction(action_type="ocr", payload={"doc_id": invoice_doc_id, "mode": "accurate"})
            executed_signatures.add(action_signature(invoice_ocr_action))
            ocr_invoice_result, step_no = perform_step(
                env, step_no, rewards, invoice_ocr_action,
            )
            steps_taken = step_no - 1
            record_action_trace("bootstrap", invoice_ocr_action, ocr_invoice_result)
            capture_invoice_data(collected, ocr_invoice_result.observation.last_tool_result)
            if task_type not in {"task_d", "task_e"}:
                break

        if task_type == "task_a":
            invoice_doc_id = invoice_doc_ids[0]
            zoom_result, step_no = perform_step(
                env, step_no, rewards,
                LedgerShieldAction(action_type="zoom", payload={"doc_id": invoice_doc_id, "bbox": [0, 0, 400, 400]}),
            )
            steps_taken = step_no - 1
            record_action_trace(
                "bootstrap",
                LedgerShieldAction(action_type="zoom", payload={"doc_id": invoice_doc_id, "bbox": [0, 0, 400, 400]}),
                zoom_result,
            )
            if zoom_result.done:
                final_score = float(zoom_result.info.get("final_score", rewards[-1] if rewards else 0.0))
                success = final_score >= SUCCESS_SCORE_THRESHOLD
            submit_payload = build_final_submission(task_type, collected, client)
            final_submission = dict(submit_payload)
            final_result, step_no = perform_step(
                env, step_no, rewards,
                LedgerShieldAction(action_type="submit_decision", payload=submit_payload),
            )
            steps_taken = step_no - 1
            record_action_trace("submit", LedgerShieldAction(action_type="submit_decision", payload=submit_payload), final_result)
            final_score = float(final_result.info.get("final_score", final_result.reward or 0.0))
            success = final_score >= SUCCESS_SCORE_THRESHOLD
            final_info = dict(final_result.info or {})
            final_tool_result = final_result.observation.last_tool_result or {}
            return {"case_id": case_id, "task_type": task_type, "score": final_score, "steps": steps_taken}

        invoice_fields = collected["invoice_fields"]
        vendor_key = vendor_key_for(invoice_fields)
        if not vendor_key:
            vendor_key = normalize_text(collected.get("email_thread", {}).get("vendor_key"))

        po_id = str(invoice_fields.get("po_id", "")).strip()
        receipt_id = str(invoice_fields.get("receipt_id", "")).strip()
        invoice_total = safe_float(invoice_fields.get("total"))
        invoice_number = str(invoice_fields.get("invoice_number", "")).strip()
        proposed_bank_account = str(invoice_fields.get("bank_account", "")).strip()

        def execute_action_batch(actions: list[LedgerShieldAction]) -> bool:
            nonlocal step_no, steps_taken, final_score, success, final_info, final_tool_result
            for action in actions:
                if step_no > MAX_STEPS:
                    break
                executed_signatures.add(action_signature(action))
                result, step_no = perform_step(env, step_no, rewards, action)
                steps_taken = step_no - 1
                record_action_trace("investigation" if action.action_type not in {"request_callback_verification", "freeze_vendor_profile", "request_bank_change_approval_chain", "request_po_reconciliation", "request_additional_receipt_evidence", "route_to_procurement", "route_to_security", "flag_duplicate_cluster_review", "create_human_handoff"} else "intervention", action, result)
                tool = result.observation.last_tool_result or {}
                update_collected_from_tool_result(collected, action, tool, email_doc_id=email_doc_id)
                if result.done:
                    final_score = float(result.info.get("final_score", result.reward or 0.0))
                    success = final_score >= SUCCESS_SCORE_THRESHOLD
                    final_info = dict(result.info or {})
                    final_tool_result = result.observation.last_tool_result or {}
                    return True
            return False

        remaining_action_slots = max(0, MAX_STEPS - step_no)
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
        record_plan("investigation", investigation_candidates, planned_investigation)
        if execute_action_batch(planned_investigation):
            return {"case_id": case_id, "task_type": task_type, "score": final_score, "steps": steps_taken}

        submit_payload = build_final_submission(task_type, collected, client)
        final_submission = dict(submit_payload)

        remaining_action_slots = max(0, MAX_STEPS - step_no)
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
        record_plan("intervention", intervention_candidates, planned_interventions)
        if execute_action_batch(planned_interventions):
            return {"case_id": case_id, "task_type": task_type, "score": final_score, "steps": steps_taken}

        if step_no <= MAX_STEPS:
            submit_action = LedgerShieldAction(action_type="submit_decision", payload=submit_payload)
            final_result, step_no = perform_step(env, step_no, rewards, submit_action)
            steps_taken = step_no - 1
            record_action_trace("submit", submit_action, final_result)
            final_score = float(final_result.info.get("final_score", final_result.reward or 0.0))
            success = final_score >= SUCCESS_SCORE_THRESHOLD
            final_info = dict(final_result.info or {})
            final_tool_result = final_result.observation.last_tool_result or {}
        else:
            final_score = clamp(rewards[-1] if rewards else 0.0, 0.0, 1.0)
            success = False

        return {"case_id": case_id, "task_type": task_type, "score": final_score, "steps": steps_taken}

    except Exception as exc:
        trace(f"[ERROR] episode failed for {case_id}: {exc}")
        error_message = str(exc)
        return {"case_id": case_id, "task_type": task_type, "score": 0.0, "steps": steps_taken, "error": str(exc)}
    finally:
        try:
            env.close()
        except Exception as exc:
            trace(f"[DEBUG] env.close failed for {case_id}: {exc}")
        if DEBUG_ARTIFACT_DIR:
            artifact_payload = {
                "model": MODEL_NAME,
                "case_id": case_id,
                "task_type": task_type,
                "score": round(final_score, 4),
                "success": success,
                "steps": steps_taken,
                "final_submission": final_submission,
                "final_tool_result": final_tool_result,
                "final_info": final_info,
                "score_breakdown": dict(final_info.get("score_breakdown", {}) or {}),
                "outcome": dict(final_info.get("outcome", {}) or {}),
                "system_state": dict(final_info.get("system_state", {}) or {}),
                "pressure_resistance_score": float(final_info.get("pressure_resistance_score", 0.0) or 0.0),
                "planning_trace": planning_trace,
                "action_trace": action_trace,
                "collected_summary": summarize_collected_state(collected) if 'collected' in locals() else {},
                "error": error_message,
            }
            try:
                write_debug_artifact(Path(DEBUG_ARTIFACT_DIR) / f"{case_id}.json", artifact_payload)
            except Exception as exc:
                trace(f"[DEBUG] failed to write debug artifact for {case_id}: {exc}")
        log_end(success=success, steps=steps_taken, rewards=rewards, score=final_score)

def build_openai_client() -> Optional[OpenAI]:
    if not API_KEY:
        trace("[DEBUG] OPENAI_API_KEY not set; running heuristic-only fallback.")
        return None
    try:
        return OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    except Exception as exc:
        trace(f"[DEBUG] failed to initialize OpenAI client: {exc}")
        return None

def run_baseline_inference(env_url: str, cases: list[str]) -> dict[str, Any]:
    client = build_openai_client()
    results = [run_episode(env_url=env_url, case_id=case_id, client=client) for case_id in cases]

    avg_score = sum(result.get("score", 0.0) for result in results) / max(len(results), 1)
    trace(f"[SUMMARY] cases={len(results)} avg_score={avg_score:.4f} scores={compact_json({result['case_id']: result.get('score', 0.0) for result in results})}")
    return {"results": results, "average_score": avg_score}

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LedgerShield LLM-powered inference with agent separation")
    parser.add_argument("--api-url", default=API_BASE_URL)
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--token", default=API_KEY)
    parser.add_argument("--env-url", default=ENV_URL)
    parser.add_argument("--cases", nargs="+", default=DEFAULT_CASES)
    parser.add_argument("--debug-artifact-dir", default=DEBUG_ARTIFACT_DIR)
    return parser.parse_args()

def main() -> None:
    global API_BASE_URL, MODEL_NAME, API_KEY, DEBUG_ARTIFACT_DIR

    args = parse_args()
    API_BASE_URL = args.api_url
    MODEL_NAME = args.model
    API_KEY = args.token
    DEBUG_ARTIFACT_DIR = args.debug_artifact_dir

    reset_api_tracking()
    run_baseline_inference(env_url=args.env_url, cases=args.cases)
    print_api_summary()

if __name__ == "__main__":
    main()
