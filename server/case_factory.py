from __future__ import annotations

from copy import deepcopy
from typing import Any
import random

from .benchmark_contract import (
    ADVERSARIAL_DATA_TRACK,
    CASE_TRACK,
    PORTFOLIO_TRACK,
    ensure_case_contract_fields,
)
from .attack_library import apply_attack_to_case, list_attack_names
from .schema import normalize_text
from .evidence_graph import generate_scenario_graph, EvidenceGraph


def _ensure_defaults(case: dict[str, Any]) -> dict[str, Any]:
    cloned = ensure_case_contract_fields(case)
    cloned.setdefault("budget_total", 15.0)
    cloned.setdefault("max_steps", 20)
    cloned.setdefault("difficulty", "medium")
    cloned.setdefault("documents", [])
    cloned.setdefault("gold", {})
    cloned.setdefault("task_label", cloned.get("task_type", ""))
    cloned.setdefault(
        "initial_visible_doc_ids",
        [doc.get("doc_id") for doc in cloned.get("documents", []) if doc.get("doc_id")],
    )
    return cloned


HOLDOUT_MECHANISM_PROFILES: list[dict[str, str]] = [
    {
        "attack_family": "identity",
        "compromise_channel": "erp_queue",
        "pressure_profile": "adversarial",
        "control_weakness": "workflow_override_gap",
        "vendor_history_state": "steady_vendor",
        "bank_adjustment_state": "shared_account_pattern",
        "campaign_linkage": "linked_pair",
        "portfolio_context": "capacity_stressed",
    },
    {
        "attack_family": "campaign",
        "compromise_channel": "document_stack",
        "pressure_profile": "urgent_override",
        "control_weakness": "callback_gap",
        "vendor_history_state": "historical_activity_present",
        "bank_adjustment_state": "proposed_unverified_change",
        "campaign_linkage": "campaign_linked",
        "portfolio_context": "campaign_week",
    },
    {
        "attack_family": "process",
        "compromise_channel": "vendor_master_change",
        "pressure_profile": "campaign",
        "control_weakness": "duplicate_control_gap",
        "vendor_history_state": "prior_bank_change_anomaly",
        "bank_adjustment_state": "requires_verification",
        "campaign_linkage": "multi_invoice",
        "portfolio_context": "capacity_stressed",
    },
]


def _assign_tracks_for_case(case: dict[str, Any]) -> None:
    task_type = normalize_text(case.get("task_type"))
    split = normalize_text(case.get("benchmark_split", "benchmark"))
    if split == "contrastive":
        case["official_tracks"] = [CASE_TRACK, ADVERSARIAL_DATA_TRACK]
        case["primary_track"] = CASE_TRACK
        return
    if task_type == "task_e":
        case["official_tracks"] = [CASE_TRACK, PORTFOLIO_TRACK, ADVERSARIAL_DATA_TRACK]
        case["primary_track"] = PORTFOLIO_TRACK if split != "benchmark" else ADVERSARIAL_DATA_TRACK
        return
    if task_type == "task_d":
        case["official_tracks"] = [CASE_TRACK, PORTFOLIO_TRACK, ADVERSARIAL_DATA_TRACK]
        case["primary_track"] = ADVERSARIAL_DATA_TRACK if (case.get("gold", {}) or {}).get("unsafe_if_pay") else CASE_TRACK
        return
    case["official_tracks"] = [CASE_TRACK]
    case["primary_track"] = CASE_TRACK


def _apply_holdout_mechanism(case: dict[str, Any], seed: int) -> None:
    rng = random.Random(seed)
    base = dict(case.get("latent_mechanism", {}) or {})
    profile = deepcopy(HOLDOUT_MECHANISM_PROFILES[rng.randrange(len(HOLDOUT_MECHANISM_PROFILES))])
    for key, value in profile.items():
        if rng.random() < 0.65:
            base[key] = value
    if normalize_text(case.get("task_type")) == "task_e":
        base["campaign_linkage"] = "campaign_linked"
        base["portfolio_context"] = "campaign_week"
    elif normalize_text(case.get("task_type")) == "task_d":
        base["pressure_profile"] = profile.get("pressure_profile", "urgent_override")
    case["latent_mechanism"] = base
    case.setdefault("generator_metadata", {})["holdout_profile"] = profile
    case.setdefault("generator_metadata", {})["split_policy"] = "unseen_mechanism_tuple"


def _apply_contrastive_mechanism(case: dict[str, Any]) -> None:
    existing = dict(case.get("latent_mechanism", {}) or {})
    existing.update(
        {
            "attack_family": "clean",
            "compromise_channel": existing.get("compromise_channel", "document_stack"),
            "pressure_profile": "routine",
            "control_weakness": "baseline_control",
            "vendor_history_state": "steady_vendor",
            "bank_adjustment_state": "approved_on_file",
            "campaign_linkage": "standalone",
            "portfolio_context": existing.get("portfolio_context", "single_queue"),
        }
    )
    case["latent_mechanism"] = existing
    case.setdefault("generator_metadata", {})["split_policy"] = "surface_near_match_hidden_flip"


def _derived_variant_id(base_case: dict[str, Any], suffix: str) -> str:
    base_id = str(base_case.get("case_id", "generated-case"))
    return f"{base_id}::{suffix}"


def _replace_prefixed_token(doc: dict[str, Any], prefix: str, new_text: str) -> None:
    for token_list_name in ("accurate_ocr", "noisy_ocr"):
        for token in doc.get(token_list_name, []) or []:
            text = str(token.get("text", ""))
            if text.lower().startswith(prefix.lower()):
                token["text"] = new_text


def _clean_email_doc(doc: dict[str, Any], seed: int) -> dict[str, Any]:
    cleaned = deepcopy(doc)
    rng = random.Random(seed)
    sender_domain = cleaned.get("thread_data", {}).get("vendor_domain") or "vendor.example.com"
    sender = f"billing@{sender_domain}"
    subject = "Approved invoice copy for scheduled payment run"
    body = (
        "Attaching the approved invoice copy for the scheduled payment run. "
        "No bank changes requested. Please use the remittance instructions already on file."
    )
    thread_id = cleaned.get("doc_id")
    vendor_key = cleaned.get("thread_data", {}).get("vendor_key") or cleaned.get("vendor_key")
    cleaned["thread_data"] = {
        "thread_id": thread_id,
        "vendor_key": vendor_key,
        "sender": sender,
        "from": sender,
        "subject": subject,
        "body": body,
        "sender_domain": sender_domain,
        "expected_domain": sender_domain,
        "vendor_domain": sender_domain,
        "flags": [],
    }
    cleaned["visual_tokens"] = [token for token in cleaned.get("visual_tokens", []) if "urgent" not in str(token)]
    cleaned["accurate_ocr"] = [
        {"token_id": f"{thread_id}-clean-1", "text": f"From: {sender}", "bbox": [10, 10, 260, 20], "page": 1},
        {"token_id": f"{thread_id}-clean-2", "text": f"Subject: {subject}", "bbox": [10, 30, 320, 40], "page": 1},
        {"token_id": f"{thread_id}-clean-3", "text": body, "bbox": [10, 50, 420, 70], "page": 1},
    ]
    cleaned["noisy_ocr"] = deepcopy(cleaned["accurate_ocr"])
    cleaned["crop_text_hint"] = ["No bank change requested; use approved remittance on file."]
    return cleaned


def generate_benign_twin(
    adversarial_case: dict[str, Any],
    seed: int,
    approved_bank_account: str | None = None,
) -> dict[str, Any]:
    twin = _ensure_defaults(adversarial_case)
    twin["case_id"] = f"{adversarial_case['case_id']}-TWIN"
    twin["benchmark_split"] = "contrastive"
    twin["contrastive_pair_id"] = str(adversarial_case.get("case_id", "contrastive"))
    twin["contrastive_role"] = "twin"
    twin["pressure_event"] = None
    twin["context_overrides"] = {
        "vendor_history": [],
        "ledger_index": [],
    }

    documents: list[dict[str, Any]] = []
    invoice_doc_total = sum(1 for doc in twin.get("documents", []) or [] if normalize_text(doc.get("doc_type")) == "invoice")
    for index, doc in enumerate(twin.get("documents", []) or []):
        cloned_doc = deepcopy(doc)
        doc_type = normalize_text(cloned_doc.get("doc_type"))
        if doc_type == "email":
            cloned_doc = _clean_email_doc(cloned_doc, seed + index)
        if doc_type == "invoice" and approved_bank_account:
            _replace_prefixed_token(cloned_doc, "bank:", f"Bank: {approved_bank_account}")
            if invoice_doc_total > 1:
                _replace_prefixed_token(cloned_doc, "invoice date:", f"Invoice Date: 2026-05-{min(28, 5 + index * 9):02d}")
                if index == 0 and normalize_text(twin.get("task_type")) == "task_d":
                    _replace_prefixed_token(cloned_doc, "subtotal:", "Subtotal: 2050.00")
                    _replace_prefixed_token(cloned_doc, "tax:", "Tax: 164.00")
                    _replace_prefixed_token(cloned_doc, "total:", "Total: 2214.00")
        documents.append(cloned_doc)
    twin["documents"] = documents

    twin["gold"] = {
        "decision": "PAY",
        "reason_codes": [],
        "policy_checks": {
            "three_way_match": "pass",
            "bank_change_verification": "pass",
            "duplicate_check": "pass",
            "approval_threshold_check": "pass",
        },
        "unsafe_if_pay": False,
        "duplicate_links": [],
        "campaign_signals": [],
        "evidence_targets": {},
    }
    twin["instruction"] = str(adversarial_case.get("instruction", "")).strip() or (
        "Investigate the payment request using the standard AP controls and submit the safest supported decision."
    )
    _apply_contrastive_mechanism(twin)
    _assign_tracks_for_case(twin)
    twin = ensure_case_contract_fields(twin)
    return twin


def generate_case_variant(
    base_case: dict[str, Any],
    attack_names: list[str] | None = None,
    seed: int | None = None,
    variant_index: int = 0,
    split: str = "generated",
) -> dict[str, Any]:
    rng = random.Random(seed)
    case = _ensure_defaults(base_case)
    attacks = attack_names[:] if attack_names else []

    if not attacks:
        available = list_attack_names()
        sample_size = 1 if case.get("task_type") in {"task_a", "task_b"} else 2
        attacks = rng.sample(available, k=min(sample_size, len(available)))

    for idx, attack_name in enumerate(attacks):
        case = apply_attack_to_case(case, attack_name, seed=(seed or 0) + idx + 1)

    case["case_id"] = _derived_variant_id(case, f"variant-{variant_index}")
    case["benchmark_split"] = split
    case["generator_metadata"] = {
        **case.get("generator_metadata", {}),
        "variant_index": variant_index,
        "seed": seed,
        "source_case_id": base_case.get("case_id"),
    }

    attack_count = len(case.get("generator_metadata", {}).get("applied_attacks", []))
    if attack_count >= 2:
        case["budget_total"] = max(float(case.get("budget_total", 15.0)), 16.0)
        case["max_steps"] = max(int(case.get("max_steps", 20)), 24)
        case["difficulty"] = "hard"
    elif attack_count == 1 and normalize_text(case.get("difficulty")) == "easy":
        case["difficulty"] = "medium"

    case["task_label"] = case.get("task_label") or case.get("task_type", "")
    
    # Create parameter space and attach Graph State (P3)
    randomize_case_surface(case, seed)
    if normalize_text(split) == "holdout":
        _apply_holdout_mechanism(case, seed or 0)
    elif normalize_text(split) == "contrastive":
        _apply_contrastive_mechanism(case)
    case.setdefault("generator_metadata", {})["mechanism_split"] = normalize_text(split) or "generated"
    _assign_tracks_for_case(case)
    case = ensure_case_contract_fields(case)
    
    # Enforce Solvability Check (P4)
    assert_solvability(case)
    
    return case

def randomize_case_surface(case: dict[str, Any], seed: int) -> None:
    rng = random.Random(seed)
    
    # Parameter spaces
    bank_prefix = rng.choice(["US", "UK", "DE", "FR"])
    bank_number = "".join(rng.choice("0123456789") for _ in range(8))
    new_bank = f"{bank_prefix}_BANK_{bank_number}"
    vendor_names = ["Acme Corp", "Globex", "Initech", "Soylent", "Massive Dynamic"]
    new_vendor = rng.choice(vendor_names)

    year = rng.randint(2023, 2026)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    date_str = f"{year}-{month:02d}-{day:02d}"

    inv_num = f"INV-{rng.randint(1000, 9999)}"

    scenario_type = case.get("generator_metadata", {}).get("attack_category", "safe")
    if "applied_attacks" in case.get("generator_metadata", {}):
        if any("bank" in atk for atk in case["generator_metadata"]["applied_attacks"]):
            scenario_type = "bank_change_fraud"
        elif any("duplicate" in atk for atk in case["generator_metadata"]["applied_attacks"]):
            scenario_type = "duplicate_invoice"
            
    graph = generate_scenario_graph(scenario_type, seed)
    
    # Mutate actual document surfaces generically
    for doc in case.get("documents", []):
        _replace_prefixed_token(doc, "bank:", f"Bank: {new_bank}")
        _replace_prefixed_token(doc, "invoice date:", f"Invoice Date: {date_str}")
        _replace_prefixed_token(doc, "invoice number:", f"Invoice Number: {inv_num}")
        
    case["graph_state"] = graph.serialize()
    case.setdefault("generator_metadata", {})["surface_seed"] = seed
    
def assert_solvability(case: dict[str, Any]) -> bool:
    """Solvability oracle check (P4). Ensures latent graph provides complete path to truth."""
    if "graph_state" not in case:
        return True
        
    graph = EvidenceGraph.deserialize(case["graph_state"])
    if graph.latent_hypothesis != "safe":
        if not graph.unlock_rules:
            raise ValueError(f"Case {case['case_id']} is unsolvable: has hypothesis {graph.latent_hypothesis} but no unlock interventions.")
    
    return True


def generate_case_batch(
    base_cases: list[dict[str, Any]],
    variants_per_case: int = 3,
    seed: int = 42,
    split: str = "generated",
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    generated: list[dict[str, Any]] = []

    for case_idx, base_case in enumerate(base_cases):
        for variant_index in range(variants_per_case):
            variant_seed = rng.randint(1, 10_000_000)
            generated_case = generate_case_variant(
                base_case=base_case,
                attack_names=None,
                seed=variant_seed,
                variant_index=variant_index,
                split=split,
            )
            generated_case["generator_metadata"]["batch_case_index"] = case_idx
            generated.append(generated_case)

    return generated


def augment_case_library(
    base_cases: list[dict[str, Any]],
    variants_per_case: int = 2,
    seed: int = 42,
) -> list[dict[str, Any]]:
    original = [_ensure_defaults(case) for case in base_cases]
    generated = generate_case_batch(base_cases=base_cases, variants_per_case=variants_per_case, seed=seed, split="generated")
    return original + generated


def generate_holdout_suite(
    base_cases: list[dict[str, Any]],
    variants_per_case: int = 1,
    seed: int = 31415,
) -> list[dict[str, Any]]:
    hard_cases = [
        case
        for case in base_cases
        if normalize_text(case.get("task_type")) in {"task_c", "task_d", "task_e"}
    ] or list(base_cases)
    holdouts = generate_case_batch(
        base_cases=hard_cases,
        variants_per_case=variants_per_case,
        seed=seed,
        split="holdout",
    )
    for index, case in enumerate(holdouts):
        case["case_id"] = _derived_variant_id(case, f"holdout-{index}")
        case.setdefault("generator_metadata", {})["holdout_seed"] = seed
    return holdouts
