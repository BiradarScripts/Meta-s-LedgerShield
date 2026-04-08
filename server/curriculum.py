"""
Dynamic difficulty adaptation (curriculum learning) for LedgerShield.

Implements an adaptive curriculum that adjusts case difficulty and attack
complexity based on the agent's running performance. This ensures:

1. **Warm-up**: New agents start with easier cases to learn the tool API.
2. **Progressive challenge**: As performance improves, harder cases and
   more sophisticated attacks are introduced.
3. **Plateau-breaking**: If performance stagnates, difficulty is modulated
   to expose specific weaknesses.
4. **Mastery gating**: Expert-level cases (Task E, APT scenarios) are only
   unlocked after demonstrating competence on prerequisite tasks.

The curriculum tracks a sliding-window ELO-like competence score and maps
it to difficulty tiers:

    Tier 0 (Novice):    score < 0.30  → task_a, task_b only, no attacks
    Tier 1 (Competent): 0.30 ≤ score < 0.55 → task_a–c, basic attacks
    Tier 2 (Proficient): 0.55 ≤ score < 0.75 → task_a–d, medium attacks
    Tier 3 (Expert):    score ≥ 0.75 → all tasks, full attack library

Design Decision:
    We use exponential moving average (EMA) rather than raw windowed mean
    to give more weight to recent performance while maintaining stability.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any

from .schema import normalize_text


# --- Difficulty tiers ---

TIER_NOVICE = 0
TIER_COMPETENT = 1
TIER_PROFICIENT = 2
TIER_EXPERT = 3

TIER_NAMES = {
    TIER_NOVICE: "novice",
    TIER_COMPETENT: "competent",
    TIER_PROFICIENT: "proficient",
    TIER_EXPERT: "expert",
}

TIER_THRESHOLDS = [0.0, 0.30, 0.55, 0.75]

TIER_ALLOWED_TASKS: dict[int, list[str]] = {
    TIER_NOVICE: ["task_a", "task_b"],
    TIER_COMPETENT: ["task_a", "task_b", "task_c"],
    TIER_PROFICIENT: ["task_a", "task_b", "task_c", "task_d"],
    TIER_EXPERT: ["task_a", "task_b", "task_c", "task_d", "task_e"],
}

TIER_ALLOWED_ATTACKS: dict[int, list[str]] = {
    TIER_NOVICE: [],
    TIER_COMPETENT: ["urgency_spoof_attack", "fake_receipt_attack"],
    TIER_PROFICIENT: [
        "urgency_spoof_attack",
        "fake_receipt_attack",
        "near_duplicate_invoice_attack",
        "approval_threshold_evasion_attack",
        "bank_override_attack",
    ],
    TIER_EXPERT: [],  # Empty means ALL attacks are allowed
}

TIER_MAX_STEPS: dict[int, int] = {
    TIER_NOVICE: 25,
    TIER_COMPETENT: 22,
    TIER_PROFICIENT: 20,
    TIER_EXPERT: 18,
}

TIER_BUDGET_MULTIPLIER: dict[int, float] = {
    TIER_NOVICE: 1.3,
    TIER_COMPETENT: 1.15,
    TIER_PROFICIENT: 1.0,
    TIER_EXPERT: 0.9,
}


@dataclass
class CurriculumState:
    """Tracks the agent's progression through the curriculum.

    Attributes:
        competence_ema: Exponential moving average of task scores (0.0–1.0).
        ema_alpha: Smoothing factor for EMA updates.
        episode_count: Total episodes completed.
        tier: Current difficulty tier (0–3).
        tier_history: List of (episode, tier) transitions.
        score_history: Sliding window of recent scores.
        window_size: Number of recent scores to retain for diagnostics.
        task_scores: Per-task-type running averages {task_type: [scores]}.
        weakest_task: Task type with the lowest running average.
        stagnation_counter: Episodes since last meaningful improvement.
        last_improvement_episode: Episode number of last score improvement.
    """
    competence_ema: float = 0.10
    ema_alpha: float = 0.15
    episode_count: int = 0
    tier: int = TIER_NOVICE
    tier_history: list[dict[str, Any]] = field(default_factory=list)
    score_history: list[float] = field(default_factory=list)
    window_size: int = 20
    task_scores: dict[str, list[float]] = field(default_factory=dict)
    weakest_task: str = ""
    stagnation_counter: int = 0
    last_improvement_episode: int = 0


def _score_to_tier(score: float) -> int:
    """Map a competence score to a difficulty tier.

    Args:
        score: Competence EMA value in [0.0, 1.0].

    Returns:
        Integer tier level (0–3).
    """
    tier = TIER_NOVICE
    for threshold_tier, threshold in enumerate(TIER_THRESHOLDS):
        if score >= threshold:
            tier = threshold_tier
    return min(tier, TIER_EXPERT)


def update_curriculum(
    state: CurriculumState,
    task_type: str,
    episode_score: float,
) -> CurriculumState:
    """Update the curriculum state after an episode completes.

    Applies EMA smoothing to the competence score, updates per-task
    statistics, detects stagnation, and adjusts the difficulty tier.

    Args:
        state: Current curriculum state (mutated in place).
        task_type: The task type just completed (e.g. 'task_c').
        episode_score: The score achieved (0.0–1.0).

    Returns:
        The updated CurriculumState.
    """
    state.episode_count += 1
    clamped_score = max(0.0, min(1.0, float(episode_score)))

    # Update EMA
    state.competence_ema = (
        state.ema_alpha * clamped_score
        + (1.0 - state.ema_alpha) * state.competence_ema
    )

    # Update score history (sliding window)
    state.score_history.append(clamped_score)
    if len(state.score_history) > state.window_size:
        state.score_history = state.score_history[-state.window_size:]

    # Update per-task scores
    task_norm = normalize_text(task_type)
    state.task_scores.setdefault(task_norm, []).append(clamped_score)
    if len(state.task_scores[task_norm]) > state.window_size:
        state.task_scores[task_norm] = state.task_scores[task_norm][-state.window_size:]

    # Identify weakest task
    task_averages: dict[str, float] = {}
    for t_type, scores in state.task_scores.items():
        if scores:
            task_averages[t_type] = sum(scores) / len(scores)
    if task_averages:
        state.weakest_task = min(task_averages, key=task_averages.get)  # type: ignore[arg-type]

    # Detect stagnation
    if clamped_score > state.competence_ema + 0.02:
        state.stagnation_counter = 0
        state.last_improvement_episode = state.episode_count
    else:
        state.stagnation_counter += 1

    # Update tier
    new_tier = _score_to_tier(state.competence_ema)
    if new_tier != state.tier:
        state.tier_history.append({
            "episode": state.episode_count,
            "from_tier": state.tier,
            "to_tier": new_tier,
            "competence_ema": round(state.competence_ema, 4),
        })
        state.tier = new_tier

    return state


def select_next_case(
    state: CurriculumState,
    available_cases: list[dict[str, Any]],
    seed: int | None = None,
) -> dict[str, Any]:
    """Select the next case from available cases based on curriculum state.

    Selection strategy:
    1. Filter cases to those allowed by current tier.
    2. If stagnating, bias toward the weakest task type.
    3. Otherwise, sample uniformly from allowed cases.

    Args:
        state: Current curriculum state.
        available_cases: List of all available case dicts.
        seed: Optional random seed for reproducibility.

    Returns:
        Selected case dictionary.

    Raises:
        ValueError: If no cases are available for the current tier.
    """
    rng = random.Random(seed)
    allowed_tasks = set(TIER_ALLOWED_TASKS.get(state.tier, ["task_a"]))

    eligible = [
        case for case in available_cases
        if normalize_text(case.get("task_type", "")) in allowed_tasks
    ]

    if not eligible:
        # Fallback: allow all cases
        eligible = list(available_cases)

    if not eligible:
        raise ValueError("No cases available for curriculum selection.")

    # Stagnation override: bias toward weakest task
    if state.stagnation_counter > 5 and state.weakest_task:
        weak_cases = [
            case for case in eligible
            if normalize_text(case.get("task_type", "")) == state.weakest_task
        ]
        if weak_cases:
            eligible = weak_cases

    return rng.choice(eligible)


def adjust_case_for_tier(
    case: dict[str, Any],
    tier: int,
) -> dict[str, Any]:
    """Adjust case parameters based on the current difficulty tier.

    Modifies max_steps and budget_total to match the tier's difficulty.

    Args:
        case: Case dictionary to adjust (not mutated, returns a copy).
        tier: Current difficulty tier (0–3).

    Returns:
        Adjusted case dictionary.
    """
    from copy import deepcopy
    adjusted = deepcopy(case)

    tier_max_steps = TIER_MAX_STEPS.get(tier, 20)
    tier_budget_mult = TIER_BUDGET_MULTIPLIER.get(tier, 1.0)

    case_max_steps = int(adjusted.get("max_steps", 20) or 20)
    adjusted["max_steps"] = max(case_max_steps, tier_max_steps)

    case_budget = float(adjusted.get("budget_total", 15.0) or 15.0)
    adjusted["budget_total"] = round(case_budget * tier_budget_mult, 2)

    return adjusted


def curriculum_summary(state: CurriculumState) -> dict[str, Any]:
    """Generate a human-readable summary of the curriculum state.

    Args:
        state: Current curriculum state.

    Returns:
        Dictionary with summary statistics.
    """
    recent_avg = (
        sum(state.score_history[-5:]) / max(len(state.score_history[-5:]), 1)
        if state.score_history else 0.0
    )

    return {
        "tier": state.tier,
        "tier_name": TIER_NAMES.get(state.tier, "unknown"),
        "competence_ema": round(state.competence_ema, 4),
        "episode_count": state.episode_count,
        "recent_5_avg": round(recent_avg, 4),
        "weakest_task": state.weakest_task,
        "stagnation_counter": state.stagnation_counter,
        "tier_transitions": len(state.tier_history),
        "allowed_tasks": TIER_ALLOWED_TASKS.get(state.tier, []),
    }
