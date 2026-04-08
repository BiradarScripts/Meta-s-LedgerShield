"""
Improved LedgerShield inference with better LLM prompting and validation.
Fixes issues with SOTA models returning empty evidence/reasons.
"""

from __future__ import annotations

import os
import sys

if os.getenv("LEDGERSHIELD_DEBUG") != "1":
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import argparse
import json
import re
import warnings
from typing import Any, Optional

warnings.filterwarnings("ignore", category=DeprecationWarning)

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from openai import OpenAI
    from ledgershield_env import LedgerShieldAction, LedgerShieldEnv


API_BASE_URL = os.getenv("API_BASE_URL") or "https://api.openai.com/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "gpt-4o-mini"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_KEY = OPENAI_API_KEY or os.getenv("API_KEY")
ENV_URL = os.getenv("ENV_URL") or "http://localhost:8000"
BENCHMARK = "ledgershield"
MAX_STEPS = 20
TEMPERATURE = 0.0
MAX_TOKENS = 1024  # Increased for better reasoning
SUCCESS_SCORE_THRESHOLD = 0.85

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

def log_end(success: bool, steps: int, rewards: list[float]) -> None:
    rewards_str = ",".join(f"{reward:.2f}" for reward in rewards)
    print(
        "[END] "
        f"success={str(success).lower()} "
        f"steps={steps} "
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
    return normalize_text(fields.get("vendor_name"))

# =============================================================================
# IMPROVED LLM DECISION FUNCTIONS WITH VALIDATION
# =============================================================================

def validate_and_fix_decision(result: dict[str, Any], collected: dict[str, Any], task_type: str) -> dict[str, Any]:
    """
    Validate LLM decision and fix inconsistencies.
    Ensures evidence_map and reason_codes match the decision.
    """
    decision = result.get("decision", "ESCALATE_FRAUD")
    reason_codes = result.get("reason_codes", [])
    evidence_map = result.get("evidence_map", {})
    policy_checks = result.get("policy_checks", {})
    
    # Build proper evidence from collected data
    invoice_records = collected.get("invoice_records", []) or []
    primary_record = invoice_records[0] if invoice_records else {"evidence": collected.get("invoice_evidence", {})}
    invoice_evidence = primary_record.get("evidence", {})
    email_evidence = collected.get("email_evidence", {})
    email_thread = collected.get("email_thread") or {}
    ledger_hits = collected.get("ledger_hits", []) or []
    bank_compares = collected.get("bank_compares", [])
    
    # Detect actual fraud indicators
    actual_reasons = []
    actual_evidence = {}
    
    # Check for bank mismatch
    bank_mismatch = any(compare and not bool(compare.get("matched")) for compare in bank_compares)
    if bank_mismatch:
        actual_reasons.append("bank_override_attempt")
        if "bank_account" in invoice_evidence:
            actual_evidence["bank_override_attempt"] = invoice_evidence["bank_account"]
    
    # Check for duplicates
    if ledger_hits:
        actual_reasons.append("duplicate_near_match")
        if "invoice_number" in invoice_evidence:
            actual_evidence["duplicate_near_match"] = invoice_evidence["invoice_number"]
    
    # Check for email fraud
    email_flags = {normalize_text(flag) for flag in email_thread.get("derived_flags", []) or email_thread.get("flags", []) or []}
    if "sender_domain_spoof" in email_flags or "sender_domain_spoof" in email_evidence:
        actual_reasons.append("sender_domain_spoof")
        if "from_header" in email_evidence:
            actual_evidence["sender_domain_spoof"] = email_evidence["from_header"]
    
    if "policy_bypass_attempt" in email_flags or "policy_bypass_attempt" in email_evidence:
        actual_reasons.append("policy_bypass_attempt")
        if email_evidence.get("policy_bypass_attempt"):
            actual_evidence["policy_bypass_attempt"] = email_evidence["policy_bypass_attempt"]
    
    if "approval_threshold_evasion" in email_flags or email_evidence.get("approval_threshold_evasion"):
        actual_reasons.append("approval_threshold_evasion")
        if email_evidence.get("approval_threshold_evasion"):
            actual_evidence["approval_threshold_evasion"] = email_evidence["approval_threshold_evasion"]
    
    # Determine correct decision based on actual evidence
    has_fraud = len(actual_reasons) > 0
    correct_decision = "ESCALATE_FRAUD" if has_fraud else "PAY"
    
    # If LLM decision conflicts with evidence, use evidence-based decision
    if decision == "ESCALATE_FRAUD" and not has_fraud:
        # LLM says fraud but no evidence - downgrade to PAY
        trace(f"[VALIDATION] LLM said ESCALATE but no fraud evidence found. Correcting to PAY.")
        decision = "PAY"
        reason_codes = []
        evidence_map = {}
    elif decision == "PAY" and has_fraud:
        # LLM says PAY but fraud exists - upgrade to ESCALATE
        trace(f"[VALIDATION] LLM said PAY but fraud evidence found. Correcting to ESCALATE_FRAUD.")
        decision = "ESCALATE_FRAUD"
        reason_codes = actual_reasons
        evidence_map = actual_evidence
    elif decision == "ESCALATE_FRAUD" and has_fraud:
        # LLM is correct - ensure evidence is complete
        if not reason_codes:
            reason_codes = actual_reasons
        if not evidence_map:
            evidence_map = actual_evidence
    
    # Ensure policy_checks match reason_codes
    if not policy_checks or not isinstance(policy_checks, dict):
        policy_checks = {
            "three_way_match": "pass",
            "bank_change_verification": "fail" if "bank_override_attempt" in reason_codes else "pass",
            "duplicate_check": "fail" if "duplicate_near_match" in reason_codes else "pass",
            "approval_threshold_check": "fail" if "approval_threshold_evasion" in reason_codes else "pass",
        }
    
    # Generate counterfactual if missing
    counterfactual = result.get("counterfactual", "")
    if not counterfactual:
        if decision == "ESCALATE_FRAUD":
            counterfactual = "Would PAY if " + ", ".join([
                "bank account matched vendor master",
                "no duplicate invoices found",
                "email domain verified",
                "no policy bypass attempts"
            ][:min(2, len(reason_codes) if reason_codes else 1)]) + "."
        else:
            counterfactual = "Would HOLD if discrepancies found or fraud indicators present."
    
    return {
        "decision": decision,
        "confidence": clamp(float(result.get("confidence", 0.9)), 0.0, 1.0),
        "reason_codes": reason_codes,
        "policy_checks": policy_checks,
        "evidence_map": evidence_map,
        "counterfactual": counterfactual,
    }

def llm_decision_task_b(client: Optional[OpenAI], collected: dict[str, Any]) -> dict[str, Any]:
    """Use LLM to analyze evidence and decide PAY or HOLD for Task B."""
    if not client:
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

IMPORTANT: You must identify specific discrepancies and provide evidence.

Return JSON format:
{
  "decision": "PAY" or "HOLD",
  "confidence": float (0.0-1.0),
  "discrepancies": [list of discrepancy types],
  "reasoning": "brief explanation of your analysis"
}"""
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": compact_json(context)},
            ],
            temperature=TEMPERATURE,
            max_completion_tokens=MAX_TOKENS,
        )
        content = response.choices[0].message.content or "{}"
        track_api_usage(response.usage)
        result = json.loads(content)
        
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

IMPORTANT: If escalating, you MUST specify which fraud indicators were found.

Return JSON format:
{
  "decision": "PAY" or "ESCALATE_FRAUD",
  "confidence": float (0.0-1.0),
  "fraud_flags": ["bank_override_attempt", "duplicate_near_match"],
  "reasoning": "explanation of fraud indicators found"
}"""
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": compact_json(context)},
            ],
            temperature=TEMPERATURE,
            max_completion_tokens=MAX_TOKENS,
        )
        content = response.choices[0].message.content or "{}"
        track_api_usage(response.usage)
        result = json.loads(content)
        
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
        
        return {
            "decision": decision,
            "confidence": clamp(float(result.get("confidence", 0.9)), 0.0, 1.0),
            "duplicate_links": duplicate_links if decision == "ESCALATE_FRAUD" else [],
            "fraud_flags": fraud_flags,
            "evidence_map": evidence_map,
        }
    except Exception as e:
        trace(f"[LLM ERROR] Task C: {e}")
        return heuristic_task_c(collected)

def heuristic_task_c(collected: dict[str, Any]) -> dict[str, Any]:
    """Original deterministic logic as fallback."""
    invoice_evidence = collected["invoice_evidence"]
    ledger_search = collected.get("ledger_search") or {}
    duplicate_links = [hit.get("ledger_id") for hit in collected.get("ledger_hits", []) if hit.get("ledger_id")]
    bank_compare = collected.get("bank_compare") or {}
    bank_mismatch = bool(bank_compare) and not bool(bank_compare.get("matched"))
    duplicate_detected = bool(duplicate_links) or int(ledger_search.get("exact_duplicate_count", 0) or 0) > 0
    suspicious = bank_mismatch or duplicate_detected

    evidence_map = {}
    fraud_flags = []
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

def llm_decision_task_d(client: Optional[OpenAI], collected: dict[str, Any]) -> dict[str, Any]:
    """Use LLM to analyze complex fraud patterns for Task D with validation."""
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

CRITICAL INSTRUCTIONS:
1. If you detect ANY fraud indicator, you MUST include it in reason_codes
2. The evidence_map and reason_codes MUST match - every reason needs evidence
3. Be thorough - check bank accounts, email headers, invoice amounts, duplicates

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
  "counterfactual": "What conditions would make this PAY instead of ESCALATE?",
  "reasoning": "detailed analysis"
}"""
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": compact_json(context)},
            ],
            temperature=TEMPERATURE,
            max_completion_tokens=MAX_TOKENS,
        )
        content = response.choices[0].message.content or "{}"
        track_api_usage(response.usage)
        result = json.loads(content)
        
        # Validate and fix the decision
        validated = validate_and_fix_decision(result, collected, "task_d")
        
        return validated
        
    except Exception as e:
        trace(f"[LLM ERROR] Task D: {e}")
        return heuristic_task_d(collected)

def heuristic_task_d(collected: dict[str, Any]) -> dict[str, Any]:
    """Original deterministic logic as fallback."""
    invoice_records = collected.get("invoice_records", []) or []
    primary_record = invoice_records[0] if invoice_records else {"fields": collected.get("invoice_fields", {}), "evidence": collected.get("invoice_evidence", {})}
    invoice_evidence = primary_record.get("evidence", {})
    email_evidence = collected.get("email_evidence", {})
    email_thread = collected.get("email_thread") or {}
    ledger_search = collected.get("ledger_search") or {}
    bank_compares = collected.get("bank_compares", [])
    vendor_history = collected.get("vendor_history", []) or []
    email_flags = {normalize_text(flag) for flag in email_thread.get("derived_flags", []) or email_thread.get("flags", []) or []}
    ledger_hits = collected.get("ledger_hits", []) or []
    duplicate_detected = bool(ledger_hits) or int(ledger_search.get("exact_duplicate_count", 0) or 0) > 0
    bank_mismatch = any(compare and not bool(compare.get("matched")) for compare in bank_compares)
    invoice_totals = [safe_float(record.get("fields", {}).get("total")) for record in invoice_records]
    threshold_split = (len(invoice_totals) >= 2 and sum(invoice_totals) >= 3000.0 and all(0.0 < total < 2000.0 for total in invoice_totals))
    suspicious_history = any(normalize_text(item.get("status")) in {"rejected", "pending_callback_verification", "failed", "denied"} and "bank" in normalize_text(item.get("change_type") or item.get("event_type")) for item in vendor_history)
    suspicious = duplicate_detected or bank_mismatch or bool(email_flags) or suspicious_history or threshold_split

    evidence_map = {}
    reason_codes = []
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
        evidence_map["approval_threshold_evasion"] = email_evidence.get("approval_threshold_evasion") or email_evidence.get("subject_header") or duplicate_evidence
        reason_codes.append("approval_threshold_evasion")
    if "policy_bypass_attempt" in email_flags or "policy_bypass_attempt" in email_evidence:
        evidence_map["policy_bypass_attempt"] = email_evidence.get("policy_bypass_attempt") or email_evidence.get("subject_header") or email_evidence.get("from_header")
        reason_codes.append("policy_bypass_attempt")

    if not suspicious:
        return {
            "decision": "PAY",
            "confidence": 0.88,
            "reason_codes": [],
            "policy_checks": {"three_way_match": "pass", "bank_change_verification": "pass", "duplicate_check": "pass", "approval_threshold_check": "pass"},
            "evidence_map": {},
            "counterfactual": "Would HOLD if sender domain changed, bank account mismatched, or duplicate cluster appeared.",
        }

    checks = {"three_way_match": "pass", "bank_change_verification": "fail" if bank_mismatch or "sender_domain_spoof" in reason_codes or "policy_bypass_attempt" in reason_codes else "pass", "duplicate_check": "fail" if duplicate_detected else "pass"}
    if "approval_threshold_evasion" in reason_codes:
        checks["approval_threshold_check"] = "fail"

    return {
        "decision": "ESCALATE_FRAUD",
        "confidence": 0.99,
        "reason_codes": sorted(set(reason_codes)),
        "policy_checks": checks,
        "evidence_map": evidence_map,
        "counterfactual": "Would PAY if all required policy checks passed.",
    }

# =============================================================================
# MAIN INFERENCE LOGIC
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

        for invoice_doc_id in invoice_doc_ids:
            ocr_invoice_result, step_no = perform_step(
                env, step_no, rewards,
                LedgerShieldAction(action_type="ocr", payload={"doc_id": invoice_doc_id, "mode": "accurate"}),
            )
            steps_taken = step_no - 1
            capture_invoice_data(collected, ocr_invoice_result.observation.last_tool_result)
            if task_type != "task_d":
                break

        if task_type == "task_a":
            invoice_doc_id = invoice_doc_ids[0]
            zoom_result, step_no = perform_step(
                env, step_no, rewards,
                LedgerShieldAction(action_type="zoom", payload={"doc_id": invoice_doc_id, "bbox": [0, 0, 400, 400]}),
            )
            steps_taken = step_no - 1
            if zoom_result.done:
                final_score = float(zoom_result.info.get("final_score", rewards[-1] if rewards else 0.0))
                success = final_score >= SUCCESS_SCORE_THRESHOLD
            submit_payload = build_final_submission(task_type, collected, client)
            final_result, step_no = perform_step(
                env, step_no, rewards,
                LedgerShieldAction(action_type="submit_decision", payload=submit_payload),
            )
            steps_taken = step_no - 1
            final_score = float(final_result.info.get("final_score", final_result.reward or 0.0))
            success = final_score >= SUCCESS_SCORE_THRESHOLD
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

        if task_type == "task_b":
            action_plan = [
                LedgerShieldAction(action_type="lookup_policy", payload={}),
                LedgerShieldAction(action_type="lookup_po", payload={"po_id": po_id}),
                LedgerShieldAction(action_type="lookup_receipt", payload={"receipt_id": receipt_id or po_id.replace("PO-", "GRN-")}),
            ]
        elif task_type == "task_c":
            action_plan = [
                LedgerShieldAction(action_type="search_ledger", payload={"vendor_key": vendor_key, "invoice_number": invoice_number, "amount": invoice_total}),
                LedgerShieldAction(action_type="compare_bank_account", payload={"vendor_key": vendor_key, "proposed_bank_account": proposed_bank_account}),
            ]
        else:
            action_plan = []
            if email_doc_id:
                action_plan.extend([
                    LedgerShieldAction(action_type="ocr", payload={"doc_id": email_doc_id, "mode": "accurate"}),
                    LedgerShieldAction(action_type="inspect_email_thread", payload={"thread_id": email_doc_id}),
                ])
            action_plan.extend([
                LedgerShieldAction(action_type="lookup_vendor_history", payload={"vendor_key": vendor_key}),
                LedgerShieldAction(action_type="lookup_policy", payload={}),
            ])
            for record in collected.get("invoice_records", []) or []:
                record_fields = record.get("fields", {})
                action_plan.append(LedgerShieldAction(action_type="compare_bank_account", payload={"vendor_key": vendor_key, "proposed_bank_account": str(record_fields.get("bank_account", "")).strip()}))
                action_plan.append(LedgerShieldAction(action_type="search_ledger", payload={"vendor_key": vendor_key, "invoice_number": str(record_fields.get("invoice_number", "")).strip(), "amount": safe_float(record_fields.get("total"))}))

        for action in action_plan:
            if step_no > MAX_STEPS:
                break
            result, step_no = perform_step(env, step_no, rewards, action)
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

            if result.done:
                final_score = float(result.info.get("final_score", result.reward or 0.0))
                success = final_score >= SUCCESS_SCORE_THRESHOLD
                return {"case_id": case_id, "task_type": task_type, "score": final_score, "steps": steps_taken}

        submit_payload = build_final_submission(task_type, collected, client)
        
        if task_type == "task_b" and submit_payload["decision"] == "HOLD" and step_no <= MAX_STEPS:
            result, step_no = perform_step(env, step_no, rewards, LedgerShieldAction(action_type="request_callback_verification", payload={}))
            steps_taken = step_no - 1
            if result.done:
                final_score = float(result.info.get("final_score", result.reward or 0.0))
                success = final_score >= SUCCESS_SCORE_THRESHOLD
                return {"case_id": case_id, "task_type": task_type, "score": final_score, "steps": steps_taken}

        if task_type == "task_c" and submit_payload["decision"] == "ESCALATE_FRAUD":
            for action in [LedgerShieldAction(action_type="request_callback_verification", payload={}), LedgerShieldAction(action_type="flag_duplicate_cluster_review", payload={}), LedgerShieldAction(action_type="route_to_security", payload={}), LedgerShieldAction(action_type="freeze_vendor_profile", payload={})]:
                if step_no > MAX_STEPS:
                    break
                result, step_no = perform_step(env, step_no, rewards, action)
                steps_taken = step_no - 1
                if result.done:
                    final_score = float(result.info.get("final_score", result.reward or 0.0))
                    success = final_score >= SUCCESS_SCORE_THRESHOLD
                    return {"case_id": case_id, "task_type": task_type, "score": final_score, "steps": steps_taken}

        if task_type == "task_d" and submit_payload["decision"] == "ESCALATE_FRAUD":
            for action in [LedgerShieldAction(action_type="request_callback_verification", payload={}), LedgerShieldAction(action_type="route_to_security", payload={}), LedgerShieldAction(action_type="freeze_vendor_profile", payload={})]:
                if step_no > MAX_STEPS:
                    break
                result, step_no = perform_step(env, step_no, rewards, action)
                steps_taken = step_no - 1
                if result.done:
                    final_score = float(result.info.get("final_score", result.reward or 0.0))
                    success = final_score >= SUCCESS_SCORE_THRESHOLD
                    return {"case_id": case_id, "task_type": task_type, "score": final_score, "steps": steps_taken}

        if step_no <= MAX_STEPS:
            final_result, step_no = perform_step(env, step_no, rewards, LedgerShieldAction(action_type="submit_decision", payload=submit_payload))
            steps_taken = step_no - 1
            final_score = float(final_result.info.get("final_score", final_result.reward or 0.0))
            success = final_score >= SUCCESS_SCORE_THRESHOLD
        else:
            final_score = clamp(rewards[-1] if rewards else 0.0, 0.0, 1.0)
            success = False

        return {"case_id": case_id, "task_type": task_type, "score": final_score, "steps": steps_taken}

    except Exception as exc:
        trace(f"[ERROR] episode failed for {case_id}: {exc}")
        return {"case_id": case_id, "task_type": task_type, "score": 0.0, "steps": steps_taken, "error": str(exc)}
    finally:
        try:
            env.close()
        except Exception as exc:
            trace(f"[DEBUG] env.close failed for {case_id}: {exc}")
        log_end(success=success, steps=steps_taken, rewards=rewards)

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
    parser = argparse.ArgumentParser(description="LedgerShield improved LLM-powered inference with validation")
    parser.add_argument("--api-url", default=API_BASE_URL)
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--token", default=API_KEY)
    parser.add_argument("--env-url", default=ENV_URL)
    parser.add_argument("--cases", nargs="+", default=DEFAULT_CASES)
    return parser.parse_args()

def main() -> None:
    global API_BASE_URL, MODEL_NAME, API_KEY

    args = parse_args()
    API_BASE_URL = args.api_url
    MODEL_NAME = args.model
    API_KEY = args.token

    reset_api_tracking()
    run_baseline_inference(env_url=args.env_url, cases=args.cases)
    print_api_summary()

if __name__ == "__main__":
    main()
