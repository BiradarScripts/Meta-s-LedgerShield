"""Tests for the curriculum (dynamic difficulty) module (Phase 5.2)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.curriculum import (
    CurriculumState,
    TIER_NOVICE,
    TIER_COMPETENT,
    TIER_PROFICIENT,
    TIER_EXPERT,
    TIER_ALLOWED_TASKS,
    update_curriculum,
    select_next_case,
    adjust_case_for_tier,
    curriculum_summary,
)


class TestCurriculumTierProgression:
    def test_starts_at_novice(self):
        state = CurriculumState()
        assert state.tier == TIER_NOVICE

    def test_progresses_to_competent(self):
        state = CurriculumState()
        for _ in range(20):
            update_curriculum(state, "task_a", 0.5)
        assert state.tier >= TIER_COMPETENT

    def test_progresses_to_expert(self):
        state = CurriculumState()
        for _ in range(40):
            update_curriculum(state, "task_d", 0.9)
        assert state.tier == TIER_EXPERT

    def test_low_scores_stay_novice(self):
        state = CurriculumState()
        for _ in range(10):
            update_curriculum(state, "task_a", 0.1)
        assert state.tier == TIER_NOVICE


class TestCaseSelection:
    def test_novice_only_gets_easy_tasks(self):
        state = CurriculumState(tier=TIER_NOVICE)
        cases = [
            {"case_id": "A1", "task_type": "task_a"},
            {"case_id": "D1", "task_type": "task_d"},
            {"case_id": "E1", "task_type": "task_e"},
        ]
        selected = select_next_case(state, cases, seed=42)
        assert selected["task_type"] in TIER_ALLOWED_TASKS[TIER_NOVICE]

    def test_expert_can_get_any_task(self):
        state = CurriculumState(tier=TIER_EXPERT)
        cases = [{"case_id": f"C{i}", "task_type": f"task_{'abcde'[i % 5]}"}
                 for i in range(20)]
        selected = select_next_case(state, cases, seed=42)
        assert selected["task_type"] in TIER_ALLOWED_TASKS[TIER_EXPERT]

    def test_stagnation_biases_weak_task(self):
        state = CurriculumState(tier=TIER_COMPETENT, stagnation_counter=10,
                                weakest_task="task_c")
        cases = [
            {"case_id": "A1", "task_type": "task_a"},
            {"case_id": "C1", "task_type": "task_c"},
            {"case_id": "B1", "task_type": "task_b"},
        ]
        selected = select_next_case(state, cases, seed=42)
        assert selected["task_type"] == "task_c"


class TestCaseAdjustment:
    def test_novice_gets_more_steps(self):
        case = {"max_steps": 15, "budget_total": 15.0}
        adjusted = adjust_case_for_tier(case, TIER_NOVICE)
        assert adjusted["max_steps"] >= 15

    def test_expert_gets_tighter_budget(self):
        case = {"max_steps": 20, "budget_total": 15.0}
        adjusted = adjust_case_for_tier(case, TIER_EXPERT)
        assert adjusted["budget_total"] < 15.0


class TestCurriculumSummary:
    def test_summary_structure(self):
        state = CurriculumState()
        update_curriculum(state, "task_a", 0.6)
        summary = curriculum_summary(state)
        assert "tier" in summary
        assert "competence_ema" in summary
        assert "allowed_tasks" in summary
