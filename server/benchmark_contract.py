from __future__ import annotations

from copy import deepcopy
from typing import Any

from .schema import normalize_text


CASE_TRACK = "case"
PORTFOLIO_TRACK = "portfolio"
ADVERSARIAL_DATA_TRACK = "adversarial"

OFFICIAL_TRACKS = {
    CASE_TRACK: {
        "label": "Case Track",
        "description": "Single-case control performance under enterprise AP controls.",
    },
    PORTFOLIO_TRACK: {
        "label": "Portfolio Track",
        "description": "Persistent AP-week performance with institutional memory and capacity tradeoffs.",
    },
    ADVERSARIAL_DATA_TRACK: {
        "label": "Adversarial Data Track",
        "description": "Robustness to deceptive content inside emails, documents, and tool outputs.",
    },
}

LATENT_MECHANISM_FIELDS = (
    "attack_family",
    "compromise_channel",
    "pressure_profile",
    "control_weakness",
    "vendor_history_state",
    "bank_adjustment_state",
    "campaign_linkage",
    "portfolio_context",
)

RESULT_CLASSES = {
    "valid_success",
    "correct_but_policy_incomplete",
    "unsafe_release",
    "unsupported_certificate",
    "malformed_submission",
    "false_positive_overcontrol",
    "incorrect_resolution",
}


def normalize_track(track: str | None) -> str:
    candidate = normalize_text(track)
    aliases = {
        "case_track": CASE_TRACK,
        "case": CASE_TRACK,
        "portfolio_track": PORTFOLIO_TRACK,
        "portfolio": PORTFOLIO_TRACK,
        "adversarial_track": ADVERSARIAL_DATA_TRACK,
        "adversarial_data_track": ADVERSARIAL_DATA_TRACK,
        "adversarial_data": ADVERSARIAL_DATA_TRACK,
        "adversarial": ADVERSARIAL_DATA_TRACK,
    }
    return aliases.get(candidate, CASE_TRACK)


def track_label(track: str | None) -> str:
    normalized = normalize_track(track)
    return str(OFFICIAL_TRACKS.get(normalized, OFFICIAL_TRACKS[CASE_TRACK])["label"])


def track_description(track: str | None) -> str:
    normalized = normalize_track(track)
    return str(OFFICIAL_TRACKS.get(normalized, OFFICIAL_TRACKS[CASE_TRACK])["description"])


def _infer_attack_family(case: dict[str, Any]) -> str:
    generator_metadata = case.get("generator_metadata", {}) or {}
    attack_category = normalize_text(generator_metadata.get("attack_category"))
    if attack_category:
        return attack_category
    task_type = normalize_text(case.get("task_type"))
    gold = case.get("gold", {}) or {}
    campaign_signals = {normalize_text(signal) for signal in gold.get("campaign_signals", []) or []}
    reason_codes = {normalize_text(code) for code in gold.get("reason_codes", []) or []}
    if task_type == "task_e" or campaign_signals & {"shared_bank_account", "coordinated_timing"}:
        return "campaign"
    if reason_codes & {"bank_override_attempt", "sender_domain_spoof", "vendor_account_takeover_suspected"}:
        return "identity"
    if reason_codes & {"duplicate_near_match", "approval_threshold_evasion"}:
        return "process"
    if reason_codes & {"missing_po", "partial_receipt_only", "price_mismatch", "quantity_mismatch", "total_mismatch"}:
        return "document"
    return "clean"


def _infer_compromise_channel(case: dict[str, Any]) -> str:
    documents = case.get("documents", []) or []
    doc_types = {normalize_text(doc.get("doc_type")) for doc in documents}
    reason_codes = {normalize_text(code) for code in (case.get("gold", {}) or {}).get("reason_codes", []) or []}
    if "email" in doc_types and reason_codes & {"sender_domain_spoof", "policy_bypass_attempt", "urgent_payment_pressure"}:
        return "email_thread"
    if reason_codes & {"bank_override_attempt", "vendor_account_takeover_suspected"}:
        return "vendor_master_change"
    if reason_codes & {"duplicate_near_match", "approval_threshold_evasion"}:
        return "ledger_pattern"
    if doc_types & {"invoice", "receipt"}:
        return "document_stack"
    return "erp_queue"


def _infer_pressure_profile(case: dict[str, Any]) -> str:
    campaign_context = case.get("campaign_context", {}) or {}
    queue_pressure = normalize_text(campaign_context.get("queue_pressure"))
    reason_codes = {normalize_text(code) for code in (case.get("gold", {}) or {}).get("reason_codes", []) or []}
    if reason_codes & {"urgent_payment_pressure", "policy_bypass_attempt"}:
        return "urgent_override"
    if queue_pressure in {"campaign", "elevated", "adversarial"}:
        return queue_pressure
    if (case.get("gold", {}) or {}).get("unsafe_if_pay"):
        return "elevated"
    return "routine"


def _infer_control_weakness(case: dict[str, Any]) -> str:
    reason_codes = {normalize_text(code) for code in (case.get("gold", {}) or {}).get("reason_codes", []) or []}
    task_type = normalize_text(case.get("task_type"))
    if reason_codes & {"bank_override_attempt", "vendor_account_takeover_suspected"}:
        return "callback_gap"
    if reason_codes & {"duplicate_near_match", "approval_threshold_evasion"}:
        return "duplicate_control_gap"
    if reason_codes & {"policy_bypass_attempt", "sender_domain_spoof"}:
        return "workflow_override_gap"
    if task_type == "task_b":
        return "three_way_match_gap"
    if task_type == "task_a":
        return "document_extraction_gap"
    return "baseline_control"


def _infer_vendor_history_state(case: dict[str, Any]) -> str:
    context = case.get("context_overrides", {}) or {}
    vendor_history = context.get("vendor_history")
    if vendor_history:
        flags = {normalize_text(row.get("change_type")) for row in vendor_history if isinstance(row, dict)}
        if flags & {"bank_account_change_request", "historical_bank_change_rejected"}:
            return "prior_bank_change_anomaly"
        return "historical_activity_present"
    reason_codes = {normalize_text(code) for code in (case.get("gold", {}) or {}).get("reason_codes", []) or []}
    if reason_codes & {"vendor_account_takeover_suspected"}:
        return "compromised_history_signal"
    return "steady_vendor"


def _infer_bank_adjustment_state(case: dict[str, Any]) -> str:
    reason_codes = {normalize_text(code) for code in (case.get("gold", {}) or {}).get("reason_codes", []) or []}
    if reason_codes & {"bank_override_attempt", "callback_verification_failed"}:
        return "proposed_unverified_change"
    if reason_codes & {"shared_bank_account"}:
        return "shared_account_pattern"
    if (case.get("gold", {}) or {}).get("unsafe_if_pay"):
        return "requires_verification"
    return "approved_on_file"


def _infer_campaign_linkage(case: dict[str, Any]) -> str:
    gold = case.get("gold", {}) or {}
    links = list(gold.get("cross_invoice_links", []) or []) + list(gold.get("duplicate_links", []) or [])
    campaign_signals = {normalize_text(signal) for signal in gold.get("campaign_signals", []) or []}
    if campaign_signals & {"shared_bank_account", "coordinated_timing"}:
        return "campaign_linked"
    if len(links) >= 2:
        return "multi_invoice"
    if links:
        return "linked_pair"
    return "standalone"


def _infer_portfolio_context(case: dict[str, Any]) -> str:
    campaign_context = case.get("campaign_context", {}) or {}
    queue_pressure = normalize_text(campaign_context.get("queue_pressure"))
    linked_invoice_count = int(campaign_context.get("linked_invoice_count", 1) or 1)
    if queue_pressure == "campaign" or linked_invoice_count >= 3:
        return "campaign_week"
    if queue_pressure in {"elevated", "adversarial"} or linked_invoice_count == 2:
        return "capacity_stressed"
    return "single_queue"


def infer_latent_mechanism(case: dict[str, Any]) -> dict[str, str]:
    existing = case.get("latent_mechanism")
    if isinstance(existing, dict):
        output = {field: normalize_text(existing.get(field)) for field in LATENT_MECHANISM_FIELDS}
    else:
        output = {}
    hints = (case.get("generator_metadata", {}) or {}).get("mechanism_hints", {}) or {}
    for field in LATENT_MECHANISM_FIELDS:
        hint_value = normalize_text(hints.get(field))
        if hint_value:
            output.setdefault(field, hint_value)
    output.setdefault("attack_family", _infer_attack_family(case))
    output.setdefault("compromise_channel", _infer_compromise_channel(case))
    output.setdefault("pressure_profile", _infer_pressure_profile(case))
    output.setdefault("control_weakness", _infer_control_weakness(case))
    output.setdefault("vendor_history_state", _infer_vendor_history_state(case))
    output.setdefault("bank_adjustment_state", _infer_bank_adjustment_state(case))
    output.setdefault("campaign_linkage", _infer_campaign_linkage(case))
    output.setdefault("portfolio_context", _infer_portfolio_context(case))
    return {field: normalize_text(output.get(field)) or "unspecified" for field in LATENT_MECHANISM_FIELDS}


def mechanism_signature(case: dict[str, Any]) -> str:
    mechanism = infer_latent_mechanism(case)
    return "|".join(str(mechanism[field]) for field in LATENT_MECHANISM_FIELDS)


def mechanism_family(case: dict[str, Any]) -> str:
    mechanism = infer_latent_mechanism(case)
    return str(mechanism.get("attack_family", "unspecified"))


def infer_official_tracks(case: dict[str, Any]) -> list[str]:
    if isinstance(case.get("official_tracks"), list):
        tracks = [normalize_track(track) for track in case.get("official_tracks", [])]
        return sorted({track for track in tracks if track})
    task_type = normalize_text(case.get("task_type"))
    gold = case.get("gold", {}) or {}
    tracks = {CASE_TRACK}
    if task_type in {"task_d", "task_e"} or bool(gold.get("campaign_signals")) or len(gold.get("duplicate_links", []) or []) >= 1:
        tracks.add(ADVERSARIAL_DATA_TRACK)
    if task_type in {"task_d", "task_e"} or len(gold.get("cross_invoice_links", []) or []) >= 1:
        tracks.add(PORTFOLIO_TRACK)
    return sorted(tracks)


def primary_track_for_case(case: dict[str, Any]) -> str:
    tracks = infer_official_tracks(case)
    if CASE_TRACK in tracks and len(tracks) == 1:
        return CASE_TRACK
    task_type = normalize_text(case.get("task_type"))
    gold = case.get("gold", {}) or {}
    if task_type == "task_e" or len(gold.get("cross_invoice_links", []) or []) >= 2:
        return PORTFOLIO_TRACK
    if bool(gold.get("unsafe_if_pay")) and task_type in {"task_d", "task_e"}:
        return ADVERSARIAL_DATA_TRACK
    return CASE_TRACK


def holdout_bucket_for_case(case: dict[str, Any]) -> str:
    mechanism = infer_latent_mechanism(case)
    parts = (
        mechanism["attack_family"],
        mechanism["compromise_channel"],
        mechanism["control_weakness"],
        mechanism["campaign_linkage"],
    )
    return "|".join(parts)


def ensure_case_contract_fields(case: dict[str, Any]) -> dict[str, Any]:
    cloned = deepcopy(case)
    cloned["latent_mechanism"] = infer_latent_mechanism(cloned)
    cloned["latent_mechanism_signature"] = mechanism_signature(cloned)
    cloned["mechanism_family"] = mechanism_family(cloned)
    cloned.setdefault("benchmark_split", "benchmark")
    cloned["official_tracks"] = infer_official_tracks(cloned)
    cloned["primary_track"] = primary_track_for_case(cloned)
    cloned["holdout_bucket"] = holdout_bucket_for_case(cloned)
    return cloned


def case_matches_track(case: dict[str, Any], track: str | None) -> bool:
    normalized_track = normalize_track(track)
    return normalized_track in infer_official_tracks(case)


def case_track_metadata(case: dict[str, Any]) -> dict[str, Any]:
    normalized_track = primary_track_for_case(case)
    return {
        "track": normalized_track,
        "track_label": track_label(normalized_track),
        "track_description": track_description(normalized_track),
        "official_tracks": infer_official_tracks(case),
        "benchmark_split": normalize_text(case.get("benchmark_split", "benchmark")) or "benchmark",
        "mechanism_family": mechanism_family(case),
    }
