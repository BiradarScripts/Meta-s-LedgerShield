from __future__ import annotations

from copy import deepcopy
from typing import Any
import random

from .attack_library import apply_attack_to_case, list_attack_names
from .schema import normalize_text


def _ensure_defaults(case: dict[str, Any]) -> dict[str, Any]:
    cloned = deepcopy(case)
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


def _derived_variant_id(base_case: dict[str, Any], suffix: str) -> str:
    base_id = str(base_case.get("case_id", "generated-case"))
    return f"{base_id}::{suffix}"


def generate_case_variant(
    base_case: dict[str, Any],
    attack_names: list[str] | None = None,
    seed: int | None = None,
    variant_index: int = 0,
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
    return case


def generate_case_batch(
    base_cases: list[dict[str, Any]],
    variants_per_case: int = 3,
    seed: int = 42,
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
    generated = generate_case_batch(base_cases=base_cases, variants_per_case=variants_per_case, seed=seed)
    return original + generated