from __future__ import annotations

from server.categorical_composition import BASE_INVESTIGATION, DUPLICATE_DETECTION, compose_tasks, task_family_component


def test_categorical_pushout_unions_spaces():
    composed = compose_tasks(BASE_INVESTIGATION, DUPLICATE_DETECTION)

    assert "case" in composed.state_space
    assert "search_ledger" in composed.action_space
    assert "documents" in composed.required_observations


def test_task_family_component_builds_larger_tasks():
    task_c = task_family_component("task_c")
    task_e = task_family_component("task_e")

    assert len(task_e.action_space) >= len(task_c.action_space)
    assert "route_to_security" in task_e.action_space
