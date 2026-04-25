#!/usr/bin/env python3
"""OpenEnv-connected TRL training runner for LedgerShield.

The important property of this script is that the dataset is collected from the
live LedgerShield environment at run time. It does not train only from a static
JSONL file. A deterministic teacher policy is rolled out through reset/step,
those action traces become SFT records, and optional TRL SFT fine-tunes a small
causal language model to emit executable LedgerShield action plans.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import inference  # noqa: E402
from models import LedgerShieldAction  # noqa: E402
from server.data_loader import load_all  # noqa: E402


DEFAULT_MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "trl-openenv-run"
POLICY_ORDER = ["random_baseline", "naive_baseline", "base_model", "trained_model", "teacher_policy"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return 0.0
        return value
    return str(value)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(to_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8"
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(to_jsonable(row), sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    columns = sorted({key for row in rows for key in row.keys()})
    lines = [",".join(columns)]
    for row in rows:
        values = []
        for column in columns:
            value = row.get(column, "")
            text = str(value).replace('"', '""')
            if "," in text or "\n" in text or '"' in text:
                text = f'"{text}"'
            values.append(text)
        lines.append(",".join(values))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def rel_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def compact_json(payload: Any) -> str:
    return json.dumps(
        to_jsonable(payload), ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def runtime_context() -> dict[str, Any]:
    return {
        "remote_job": os.environ.get("LEDGERSHIELD_REMOTE_JOB", "0") == "1",
        "hf_hardware_requested": os.environ.get("LEDGERSHIELD_HF_HARDWARE", ""),
        "run_label": os.environ.get("LEDGERSHIELD_RUN_LABEL", ""),
        "python": sys.version.split()[0],
    }


def case_ids_from_db(db: dict[str, Any], requested: list[str], limit: int, split: str = "benchmark") -> list[str]:
    if requested:
        cases = [case.strip() for case in requested if case.strip()]
    else:
        split = split.strip().lower()
        cases = [
            str(case.get("case_id", ""))
            for case in db.get("cases", [])
            if split == "all" or str(case.get("benchmark_split", "benchmark")).strip().lower() == split
        ]
    cases = [case for case in cases if case]
    if limit > 0:
        cases = cases[:limit]
    return cases


def observation_for_prompt(observation: Any) -> dict[str, Any]:
    obs = to_jsonable(observation)
    if not isinstance(obs, dict):
        return {"raw_observation": str(obs)}
    visible_docs = []
    for doc in obs.get("visible_documents", []) or []:
        if not isinstance(doc, dict):
            continue
        visible_docs.append(
            {
                "doc_id": doc.get("doc_id"),
                "doc_type": doc.get("doc_type"),
                "language": doc.get("language"),
                "page_count": doc.get("page_count"),
                "thumbnail": doc.get("thumbnail"),
            }
        )
    metadata = obs.get("case_metadata", {}) or {}
    return {
        "case_id": obs.get("case_id"),
        "task_type": obs.get("task_type"),
        "instruction": obs.get("instruction"),
        "budget_remaining": obs.get("budget_remaining"),
        "max_steps": obs.get("max_steps"),
        "visible_documents": visible_docs,
        "track_mode": metadata.get("track_mode"),
        "benchmark_track": metadata.get("benchmark_track"),
        "portfolio_context": obs.get("portfolio_context", {}),
    }


def build_prompt(observation: Any) -> str:
    context = observation_for_prompt(observation)
    return (
        "You are training as a LedgerShield AP control agent. The environment is "
        "partially observable: use tools before submitting a payment decision.\n"
        "Return ONLY valid JSON with this schema:\n"
        '{"actions":[{"action_type":"ocr","payload":{"doc_id":"...","mode":"accurate"}}]}\n'
        "Allowed action_type values: zoom, get_doc_crop, ocr, lookup_vendor, "
        "lookup_vendor_history, lookup_policy, lookup_po, lookup_receipt, "
        "search_ledger, inspect_email_thread, compare_bank_account, "
        "request_callback_verification, freeze_vendor_profile, "
        "request_bank_change_approval_chain, request_po_reconciliation, "
        "request_additional_receipt_evidence, route_to_procurement, "
        "route_to_security, flag_duplicate_cluster_review, create_human_handoff, "
        "submit_decision.\n"
        "Case context:\n"
        f"{json.dumps(context, indent=2, sort_keys=True)}\n"
        "Return JSON only. Do not explain the plan.\n"
    )


def action_to_dict(action: LedgerShieldAction) -> dict[str, Any]:
    payload = dict(to_jsonable(getattr(action, "payload", {}) or {}))
    payload.pop("decision_certificate", None)
    return {
        "action_type": str(getattr(action, "action_type", "")),
        "payload": payload,
    }


def trim_info(info: dict[str, Any]) -> dict[str, Any]:
    keep = {
        "final_score",
        "score_breakdown",
        "reward_model",
        "benchmark_track",
        "track_mode",
        "pressure_resistance_score",
        "authority_gate",
        "institutional_metrics",
    }
    return {key: to_jsonable(value) for key, value in info.items() if key in keep}


class ActionRecorderEnv:
    """Wraps a LedgerShield env and records every action/reward pair."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.initial_observation: Any = None
        self.steps: list[dict[str, Any]] = []

    def reset(
        self,
        seed: int | None = None,
        case_id: str | None = None,
        track: str | None = None,
    ) -> Any:
        result = self.inner.reset(seed=seed, case_id=case_id, track=track)
        self.initial_observation = getattr(result, "observation", result)
        self.steps = []
        return result

    def step(self, action: LedgerShieldAction) -> Any:
        result = self.inner.step(action)
        observation = to_jsonable(getattr(result, "observation", {}))
        info = dict(to_jsonable(getattr(result, "info", {}) or {}))
        last_tool_result = (
            observation.get("last_tool_result", {})
            if isinstance(observation, dict)
            else {}
        )
        self.steps.append(
            {
                "step": len(self.steps) + 1,
                "action": action_to_dict(action),
                "reward": safe_float(getattr(result, "reward", 0.0)),
                "done": bool(getattr(result, "done", False)),
                "info": trim_info(info),
                "last_tool_result": to_jsonable(last_tool_result),
            }
        )
        return result

    def close(self) -> None:
        close = getattr(self.inner, "close", None)
        if callable(close):
            close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


def compact_action(action: dict[str, Any]) -> dict[str, Any]:
    action_type = str(action.get("action_type", ""))
    payload = action.get("payload", {}) if isinstance(action.get("payload"), dict) else {}
    if action_type != "submit_decision":
        return {"action_type": action_type, "payload": payload}

    def trim_nested(value: Any, depth: int = 0) -> Any:
        if depth > 3:
            return str(value)[:120]
        if isinstance(value, dict):
            return {
                str(key)[:80]: trim_nested(item, depth + 1)
                for key, item in list(value.items())[:12]
            }
        if isinstance(value, list):
            return [trim_nested(item, depth + 1) for item in value[:12]]
        if isinstance(value, str):
            return value[:240]
        return to_jsonable(value)

    compact_payload: dict[str, Any] = {
        "decision": payload.get("decision", "NEEDS_REVIEW"),
        "confidence": round(safe_float(payload.get("confidence"), 0.75), 3),
    }
    for key in ["reason_codes", "fraud_flags", "discrepancies", "campaign_signals", "duplicate_invoice_ids"]:
        value = payload.get(key)
        if isinstance(value, list) and value:
            compact_payload[key] = [str(item)[:80] for item in value[:5]]
    for key in [
        "policy_checks",
        "evidence_map",
        "extracted_fields",
        "line_items",
        "predicted_probabilities",
        "counterfactual",
    ]:
        value = payload.get(key)
        if value:
            compact_payload[key] = trim_nested(value)
    return {"action_type": action_type, "payload": compact_payload}


def build_completion(steps: list[dict[str, Any]], *, compact: bool = False) -> str:
    actions = [
        step["action"] for step in steps if step.get("action", {}).get("action_type")
    ]
    if compact:
        actions = [compact_action(action) for action in actions]
    return compact_json({"actions": actions})


def collect_live_examples(
    cases: list[str], db: dict[str, Any], output_dir: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    examples: list[dict[str, Any]] = []
    trajectories: list[dict[str, Any]] = []
    for case_id in cases:
        recorder = ActionRecorderEnv(inference.LocalLedgerShieldEnv(db=db))
        result = inference.run_episode_with_env(
            env=recorder,
            case_id=case_id,
            client=None,
            emit_logs=False,
        )
        prompt = build_prompt(recorder.initial_observation)
        teacher_completion = build_completion(recorder.steps, compact=False)
        completion = build_completion(recorder.steps, compact=True)
        final_step = recorder.steps[-1] if recorder.steps else {}
        final_info = final_step.get("info", {}) if isinstance(final_step, dict) else {}
        score_breakdown = (
            final_info.get("score_breakdown", {})
            if isinstance(final_info, dict)
            else {}
        )
        example = {
            "prompt": prompt,
            "completion": completion,
            "teacher_completion": teacher_completion,
            "metadata": {
                "case_id": case_id,
                "task_type": result.get("task_type", ""),
                "score": safe_float(result.get("score", 0.0)),
                "steps": len(recorder.steps),
                "final_decision": result.get("final_decision", ""),
                "result_class": score_breakdown.get(
                    "result_class", result.get("result_class", "")
                ),
            },
        }
        trajectory = {
            "case_id": case_id,
            "initial_observation": observation_for_prompt(recorder.initial_observation),
            "steps": recorder.steps,
            "result": result,
        }
        examples.append(example)
        trajectories.append(trajectory)
    write_jsonl(output_dir / "openenv_sft_examples.jsonl", examples)
    write_json(output_dir / "openenv_trajectories.json", trajectories)
    return examples, trajectories


def format_training_text(
    prompt: str,
    completion: str,
    eos_token: str | None = None,
    tokenizer: Any | None = None,
) -> str:
    suffix = eos_token or ""
    return (
        f"### LedgerShield Prompt\n{prompt}\n### JSON Action Plan\n{completion}{suffix}"
    )


def split_examples_for_training(
    examples: list[dict[str, Any]],
    eval_limit: int,
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if len(examples) <= 1 or eval_limit <= 0:
        return list(examples), list(examples)

    shuffled = list(examples)
    random.Random(seed).shuffle(shuffled)
    eval_count = min(max(1, eval_limit), len(shuffled) - 1)
    eval_examples = shuffled[:eval_count]
    train_examples = shuffled[eval_count:]
    if not train_examples:
        train_examples = shuffled[:-1]
        eval_examples = shuffled[-1:]
    return train_examples, eval_examples


def recover_action_objects(text: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    actions: list[dict[str, Any]] = []
    index = 0
    while True:
        match = re.search(r'\{\s*"action_type"\s*:', text[index:])
        if not match:
            break
        start = index + match.start()
        try:
            obj, consumed = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            index = start + 1
            continue
        if isinstance(obj, dict) and obj.get("action_type"):
            payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
            actions.append({"action_type": str(obj.get("action_type")), "payload": payload})
        index = start + max(consumed, 1)
    return actions


def parse_actions_from_completion(text: str) -> tuple[list[dict[str, Any]], bool, str]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    start = cleaned.find("{")
    if start >= 0:
        cleaned = cleaned[start:]
    try:
        payload, _ = json.JSONDecoder().raw_decode(cleaned)
    except json.JSONDecodeError as exc:
        recovered = recover_action_objects(cleaned)
        if recovered:
            return recovered, True, f"partial_json_recovery: {exc}"
        return [], False, f"json_parse_error: {exc}"
    actions = payload.get("actions") if isinstance(payload, dict) else None
    if not isinstance(actions, list):
        recovered = recover_action_objects(cleaned)
        if recovered:
            return recovered, True, "partial_json_recovery: missing_actions_list"
        return [], False, "missing_actions_list"
    valid_actions = [
        action
        for action in actions
        if isinstance(action, dict) and action.get("action_type")
    ]
    return valid_actions, bool(valid_actions), ""


def fallback_review_action(reason: str) -> dict[str, Any]:
    return {
        "action_type": "submit_decision",
        "payload": {
            "decision": "NEEDS_REVIEW",
            "confidence": 0.35,
            "reason_codes": ["model_output_unparseable"],
            "policy_checks": {},
            "evidence_map": {},
            "notes": reason[:300],
        },
    }


def naive_pay_action() -> dict[str, Any]:
    return {
        "action_type": "submit_decision",
        "payload": {
            "decision": "PAY",
            "confidence": 0.50,
            "reason_codes": ["naive_untrained_release"],
            "policy_checks": {},
            "evidence_map": {},
            "notes": "Naive baseline releases without investigation.",
        },
    }


def random_baseline_actions(example: dict[str, Any]) -> list[dict[str, Any]]:
    case_id = str((example.get("metadata") or {}).get("case_id", ""))
    rng = random.Random(f"random-baseline::{case_id}")
    decision = rng.choice(["PAY", "HOLD", "NEEDS_REVIEW", "ESCALATE_FRAUD"])
    return [
        {
            "action_type": "submit_decision",
            "payload": {
                "decision": decision,
                "confidence": round(rng.uniform(0.25, 0.95), 3),
                "reason_codes": ["random_untrained_policy"],
                "policy_checks": {},
                "evidence_map": {},
                "notes": "Seeded random untrained baseline; no investigation.",
            },
        }
    ]


def run_action_plan(
    case_id: str,
    actions: list[dict[str, Any]],
    db: dict[str, Any],
    *,
    parse_success: bool = True,
    parse_error: str = "",
    max_actions: int = 30,
) -> dict[str, Any]:
    env = inference.LocalLedgerShieldEnv(db=db)
    rewards: list[float] = []
    done = False
    last_info: dict[str, Any] = {}
    last_tool: dict[str, Any] = {}
    errors: list[str] = []
    try:
        env.reset(case_id=case_id)
        executable_actions = actions[:max_actions]
        if not executable_actions:
            executable_actions = [
                fallback_review_action(parse_error or "empty_action_plan")
            ]
        for action_spec in executable_actions:
            action_type = str(action_spec.get("action_type", ""))
            payload = action_spec.get("payload", {}) or {}
            if not isinstance(payload, dict):
                payload = {}
            try:
                result = env.step(
                    LedgerShieldAction(action_type=action_type, payload=payload)
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{action_type}: {exc}")
                continue
            rewards.append(safe_float(getattr(result, "reward", 0.0)))
            last_info = dict(to_jsonable(getattr(result, "info", {}) or {}))
            observation = to_jsonable(getattr(result, "observation", {}) or {})
            if isinstance(observation, dict):
                last_tool = observation.get("last_tool_result", {}) or {}
            done = bool(getattr(result, "done", False))
            if done:
                break
        if not done:
            result = env.step(
                LedgerShieldAction(
                    **fallback_review_action("plan_did_not_submit_decision")
                )
            )
            rewards.append(safe_float(getattr(result, "reward", 0.0)))
            last_info = dict(to_jsonable(getattr(result, "info", {}) or {}))
            observation = to_jsonable(getattr(result, "observation", {}) or {})
            if isinstance(observation, dict):
                last_tool = observation.get("last_tool_result", {}) or {}
            done = bool(getattr(result, "done", False))
    finally:
        env.close()
    score_breakdown = (
        last_info.get("score_breakdown", {}) if isinstance(last_info, dict) else {}
    )
    if not isinstance(score_breakdown, dict):
        score_breakdown = {}
    final_score = safe_float(
        last_info.get("final_score"), rewards[-1] if rewards else 0.0
    )
    result_class = str(score_breakdown.get("result_class", "") or "")
    return {
        "case_id": case_id,
        "score": round(final_score, 4),
        "total_reward": round(sum(rewards), 4),
        "steps": len(rewards),
        "done": done,
        "parse_success": parse_success,
        "parse_error": parse_error,
        "errors": errors,
        "final_decision": str(
            last_tool.get("decision", last_tool.get("effective_decision", "")) or ""
        ),
        "result_class": result_class,
        "unsafe_release": result_class == "unsafe_release",
        "control_satisfied_resolution": safe_float(
            score_breakdown.get("control_satisfied_resolution")
        ),
        "institutional_utility": safe_float(
            score_breakdown.get("institutional_utility")
        ),
        "institutional_loss_score": safe_float(
            score_breakdown.get("institutional_loss_score")
        ),
        "certificate_score": safe_float(score_breakdown.get("certificate_score")),
    }


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    count = max(len(results), 1)
    result_class_counts: dict[str, int] = {}
    for row in results:
        result_class = str(row.get("result_class", "unknown") or "unknown")
        result_class_counts[result_class] = result_class_counts.get(result_class, 0) + 1
    return {
        "case_count": len(results),
        "mean_score": round(
            sum(safe_float(row.get("score")) for row in results) / count, 4
        ),
        "mean_total_reward": round(
            sum(safe_float(row.get("total_reward")) for row in results) / count, 4
        ),
        "mean_steps": round(
            sum(safe_float(row.get("steps")) for row in results) / count, 4
        ),
        "done_rate": round(sum(1.0 for row in results if row.get("done")) / count, 4),
        "parse_success_rate": round(
            sum(1.0 for row in results if row.get("parse_success")) / count, 4
        ),
        "unsafe_release_rate": round(
            sum(1.0 for row in results if row.get("unsafe_release")) / count, 4
        ),
        "control_satisfied_resolution_rate": round(
            sum(safe_float(row.get("control_satisfied_resolution")) for row in results)
            / count,
            4,
        ),
        "institutional_utility_mean": round(
            sum(safe_float(row.get("institutional_utility")) for row in results)
            / count,
            4,
        ),
        "institutional_loss_score_mean": round(
            sum(safe_float(row.get("institutional_loss_score")) for row in results)
            / count,
            4,
        ),
        "certificate_score_mean": round(
            sum(safe_float(row.get("certificate_score")) for row in results) / count,
            4,
        ),
        "result_class_counts": result_class_counts,
    }


def evaluate_fixed_policy(
    name: str,
    examples: list[dict[str, Any]],
    db: dict[str, Any],
    action_builder: Any,
) -> dict[str, Any]:
    results = []
    for example in examples:
        case_id = str(example["metadata"]["case_id"])
        actions = action_builder(example)
        results.append(run_action_plan(case_id, actions, db))
    return {"name": name, "summary": summarize_results(results), "results": results}


def teacher_actions(example: dict[str, Any]) -> list[dict[str, Any]]:
    actions, _, _ = parse_actions_from_completion(
        str(example.get("teacher_completion") or example.get("completion", ""))
    )
    return actions


def load_training_stack() -> dict[str, Any]:
    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            TrainingArguments,
            set_seed,
        )

        try:
            from trl import SFTConfig, SFTTrainer
        except ImportError:
            from trl import SFTTrainer

            SFTConfig = None
        from transformers import TrainerCallback
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "TRL training dependencies are not available. Install them in a clean environment with: "
            "pip install -r training/requirements-training.txt"
        ) from exc
    return {
        "torch": torch,
        "Dataset": Dataset,
        "LoraConfig": LoraConfig,
        "AutoModelForCausalLM": AutoModelForCausalLM,
        "AutoTokenizer": AutoTokenizer,
        "TrainingArguments": TrainingArguments,
        "SFTConfig": SFTConfig,
        "SFTTrainer": SFTTrainer,
        "TrainerCallback": TrainerCallback,
        "set_seed": set_seed,
    }


def model_device(torch_module: Any) -> str:
    if torch_module.cuda.is_available():
        return "cuda"
    if (
        getattr(torch_module.backends, "mps", None)
        and torch_module.backends.mps.is_available()
    ):
        return "mps"
    return "cpu"


def hardware_info(torch_module: Any, device: str) -> dict[str, Any]:
    info: dict[str, Any] = {
        "device": device,
        "cuda_available": bool(torch_module.cuda.is_available()),
        "mps_available": bool(
            getattr(torch_module.backends, "mps", None)
            and torch_module.backends.mps.is_available()
        ),
        "cuda_version": getattr(torch_module.version, "cuda", None),
    }
    if torch_module.cuda.is_available():
        index = torch_module.cuda.current_device()
        props = torch_module.cuda.get_device_properties(index)
        info.update(
            {
                "cuda_device_index": int(index),
                "cuda_device_name": torch_module.cuda.get_device_name(index),
                "cuda_device_total_memory_gb": round(props.total_memory / (1024**3), 2),
                "cuda_device_capability": list(torch_module.cuda.get_device_capability(index)),
                "cuda_device_count": int(torch_module.cuda.device_count()),
            }
        )
    return info


def generate_completion(
    model: Any, tokenizer: Any, torch_module: Any, prompt: str, max_new_tokens: int
) -> str:
    device = next(model.parameters()).device
    input_text = f"### LedgerShield Prompt\n{prompt}\n### JSON Action Plan\n"
    inputs = tokenizer(
        input_text, return_tensors="pt", truncation=True, max_length=2048
    )
    inputs = {key: value.to(device) for key, value in inputs.items()}
    with torch_module.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    prompt_length = inputs["input_ids"].shape[-1]
    decoded = tokenizer.decode(output_ids[0][prompt_length:], skip_special_tokens=True)
    return decoded.strip()


def evaluate_model_policy(
    label: str,
    model: Any,
    tokenizer: Any,
    torch_module: Any,
    examples: list[dict[str, Any]],
    db: dict[str, Any],
    *,
    max_new_tokens: int,
) -> dict[str, Any]:
    results = []
    generations = []
    model.eval()
    for index, example in enumerate(examples, start=1):
        case_id = str(example["metadata"]["case_id"])
        print(f"[eval:{label}] {index}/{len(examples)} case={case_id}", flush=True)
        prompt = str(example.get("prompt", ""))
        generated = generate_completion(
            model, tokenizer, torch_module, prompt, max_new_tokens=max_new_tokens
        )
        actions, parse_success, parse_error = parse_actions_from_completion(generated)
        if not actions:
            actions = [
                fallback_review_action(parse_error or "model_generated_no_actions")
            ]
        result = run_action_plan(
            case_id,
            actions,
            db,
            parse_success=parse_success,
            parse_error=parse_error,
        )
        results.append(result)
        generations.append(
            {
                "case_id": case_id,
                "generated": generated,
                "parse_success": parse_success,
                "parse_error": parse_error,
                "executed_actions": actions,
            }
        )
    return {
        "name": label,
        "summary": summarize_results(results),
        "results": results,
        "generations": generations,
    }


def build_trainer(
    stack: dict[str, Any],
    model: Any,
    tokenizer: Any,
    dataset: Any,
    args: argparse.Namespace,
) -> Any:
    import inspect

    torch_module = stack["torch"]
    SFTConfig = stack.get("SFTConfig")
    TrainingArguments = stack["TrainingArguments"]
    SFTTrainer = stack["SFTTrainer"]
    LoraConfig = stack["LoraConfig"]
    fp16 = torch_module.cuda.is_available()
    training_args_cls = SFTConfig or TrainingArguments
    training_kwargs: dict[str, Any] = {
        "output_dir": str(args.output_dir / "checkpoints"),
        "max_steps": int(args.max_steps),
        "per_device_train_batch_size": int(args.batch_size),
        "gradient_accumulation_steps": int(args.gradient_accumulation_steps),
        "learning_rate": float(args.learning_rate),
        "logging_steps": 1,
        "save_strategy": "steps",
        "save_steps": max(10, int(args.max_steps)),
        "report_to": [],
        "remove_unused_columns": False,
        "fp16": fp16,
        "bf16": False,
        "optim": "adamw_torch",
    }
    arg_names = set(inspect.signature(training_args_cls).parameters)
    if "max_length" in arg_names:
        training_kwargs["max_length"] = int(args.max_seq_length)
    if "completion_only_loss" in arg_names:
        training_kwargs["completion_only_loss"] = True
    training_args = training_args_cls(**training_kwargs)
    lora_config = LoraConfig(
        r=int(args.lora_r),
        lora_alpha=int(args.lora_alpha),
        lora_dropout=float(args.lora_dropout),
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=args.lora_target_modules,
    )
    params = inspect.signature(SFTTrainer.__init__).parameters
    kwargs: dict[str, Any] = {
        "model": model,
        "args": training_args,
        "train_dataset": dataset,
    }
    if "tokenizer" in params:
        kwargs["tokenizer"] = tokenizer
    if "processing_class" in params:
        kwargs["processing_class"] = tokenizer
    if "peft_config" in params:
        kwargs["peft_config"] = lora_config
    if "max_seq_length" in params:
        kwargs["max_seq_length"] = int(args.max_seq_length)
    return SFTTrainer(**kwargs)


class RewardEvalCallback:
    def __init__(
        self,
        callback_cls: Any,
        tokenizer: Any,
        torch_module: Any,
        eval_examples: list[dict[str, Any]],
        db: dict[str, Any],
        *,
        interval: int,
        case_limit: int,
        max_new_tokens: int,
    ) -> None:
        self.history: list[dict[str, Any]] = []
        self._last_step = -1
        self.tokenizer = tokenizer
        self.torch_module = torch_module
        self.eval_examples = eval_examples[: max(0, int(case_limit))]
        self.db = db
        self.interval = max(0, int(interval))
        self.max_new_tokens = int(max_new_tokens)
        self.callback_cls = callback_cls

    def build(self) -> Any:
        outer = self

        class _Callback(outer.callback_cls):  # type: ignore[misc, valid-type]
            def on_step_end(self, args, state, control, **kwargs):  # type: ignore[no-untyped-def]
                step = int(getattr(state, "global_step", 0) or 0)
                if outer.interval <= 0 or not outer.eval_examples:
                    return control
                if step <= 0 or step == outer._last_step or step % outer.interval != 0:
                    return control
                model = kwargs.get("model")
                if model is None:
                    return control
                outer._last_step = step
                payload = evaluate_model_policy(
                    f"checkpoint_step_{step}",
                    model,
                    outer.tokenizer,
                    outer.torch_module,
                    outer.eval_examples,
                    outer.db,
                    max_new_tokens=outer.max_new_tokens,
                )
                summary = payload.get("summary", {}) or {}
                record = {
                    "step": step,
                    "mean_score": safe_float(summary.get("mean_score")),
                    "mean_total_reward": safe_float(summary.get("mean_total_reward")),
                    "parse_success_rate": safe_float(summary.get("parse_success_rate")),
                    "unsafe_release_rate": safe_float(summary.get("unsafe_release_rate")),
                    "control_satisfied_resolution_rate": safe_float(summary.get("control_satisfied_resolution_rate")),
                    "results": payload.get("results", []),
                }
                outer.history.append(record)
                print(
                    "[reward_eval] "
                    f"step={step} "
                    f"mean_score={record['mean_score']:.4f} "
                    f"parse_success={record['parse_success_rate']:.4f} "
                    f"unsafe_release={record['unsafe_release_rate']:.4f}",
                    flush=True,
                )
                return control

        return _Callback()


def run_trl_sft(
    train_examples: list[dict[str, Any]],
    eval_examples: list[dict[str, Any]],
    db: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    stack = load_training_stack()
    torch_module = stack["torch"]
    stack["set_seed"](int(args.seed))
    random.seed(int(args.seed))

    tokenizer = stack["AutoTokenizer"].from_pretrained(
        args.model, token=os.environ.get("HF_TOKEN") or None
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    dataset = stack["Dataset"].from_list(
        [
            {
                "prompt": f"### LedgerShield Prompt\n{row['prompt']}\n### JSON Action Plan\n",
                "completion": f"{row['completion']}{tokenizer.eos_token or ''}",
                "case_id": row["metadata"]["case_id"],
            }
            for row in train_examples
        ]
    )

    dtype = (
        torch_module.float16
        if torch_module.cuda.is_available()
        else torch_module.float32
    )
    model = stack["AutoModelForCausalLM"].from_pretrained(
        args.model,
        torch_dtype=dtype,
        token=os.environ.get("HF_TOKEN") or None,
    )
    device = model_device(torch_module)
    hw_info = hardware_info(torch_module, device)
    print(f"[hardware] {json.dumps(hw_info, sort_keys=True)}", flush=True)
    if device != "cuda":
        model.to(device)

    base_eval = None
    if eval_examples and not bool(args.skip_base_model_eval):
        base_eval = evaluate_model_policy(
            "base_model",
            model,
            tokenizer,
            torch_module,
            eval_examples,
            db,
            max_new_tokens=int(args.max_new_tokens),
        )

    reward_callback = RewardEvalCallback(
        stack["TrainerCallback"],
        tokenizer,
        torch_module,
        eval_examples,
        db,
        interval=int(args.reward_eval_interval),
        case_limit=int(args.reward_eval_case_limit),
        max_new_tokens=int(args.reward_eval_max_new_tokens or args.max_new_tokens),
    )
    trainer = build_trainer(stack, model, tokenizer, dataset, args)
    if int(args.reward_eval_interval) > 0 and eval_examples:
        trainer.add_callback(reward_callback.build())
    train_result = trainer.train()
    final_model_dir = args.output_dir / "final_model"
    final_model_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(final_model_dir))
    tokenizer.save_pretrained(str(args.output_dir / "tokenizer"))

    trained_eval = None
    if eval_examples:
        trained_eval = evaluate_model_policy(
            "trained_model",
            model,
            tokenizer,
            torch_module,
            eval_examples,
            db,
            max_new_tokens=int(args.max_new_tokens),
        )

    return {
        "status": "completed",
        "model": args.model,
        "final_model_dir": str(final_model_dir),
        "train_example_count": len(train_examples),
        "eval_example_count": len(eval_examples),
        "train_case_ids": [row["metadata"]["case_id"] for row in train_examples],
        "eval_case_ids": [row["metadata"]["case_id"] for row in eval_examples],
        "hardware": hw_info,
        "training_loss": safe_float(getattr(train_result, "training_loss", 0.0)),
        "train_runtime": safe_float(
            getattr(train_result, "metrics", {}).get("train_runtime", 0.0)
        ),
        "log_history": to_jsonable(getattr(trainer.state, "log_history", [])),
        "reward_eval_history": to_jsonable(reward_callback.history),
        "base_model_eval": base_eval,
        "trained_model_eval": trained_eval,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect live LedgerShield trajectories and optionally train with TRL SFT."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--cases", nargs="*", default=[])
    parser.add_argument("--case-limit", type=int, default=21)
    parser.add_argument("--case-split", default="benchmark", choices=["benchmark", "challenge", "all"])
    parser.add_argument(
        "--train",
        action="store_true",
        help="Run HF TRL SFT after live trajectory collection.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-steps", type=int, default=80)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--max-seq-length", type=int, default=2048)
    parser.add_argument("--max-new-tokens", type=int, default=900)
    parser.add_argument("--model-eval-case-limit", type=int, default=6)
    parser.add_argument("--skip-base-model-eval", action="store_true")
    parser.add_argument("--reward-eval-interval", type=int, default=0)
    parser.add_argument("--reward-eval-case-limit", type=int, default=3)
    parser.add_argument("--reward-eval-max-new-tokens", type=int, default=0)
    parser.add_argument("--lora-r", type=int, default=8)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument(
        "--lora-target-modules",
        nargs="+",
        default=["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--no-plots", action="store_true")
    return parser.parse_args()


def loss_history_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in (metrics.get("training", {}) or {}).get("log_history", []) or []:
        if "loss" not in row:
            continue
        rows.append(
            {
                "step": int(safe_float(row.get("step"), len(rows) + 1)),
                "loss": safe_float(row.get("loss")),
                "learning_rate": safe_float(row.get("learning_rate")),
                "grad_norm": safe_float(row.get("grad_norm")),
                "entropy": safe_float(row.get("entropy")),
                "mean_token_accuracy": safe_float(row.get("mean_token_accuracy")),
                "num_tokens": safe_float(row.get("num_tokens")),
                "epoch": safe_float(row.get("epoch")),
            }
        )
    return rows


def export_loss_history(metrics: dict[str, Any], output_dir: Path) -> dict[str, str]:
    rows = loss_history_rows(metrics)
    json_path = output_dir / "loss_history.json"
    csv_path = output_dir / "loss_history.csv"
    write_json(json_path, rows)
    write_csv(csv_path, rows)
    return {
        "loss_history_json": rel_path(json_path),
        "loss_history_csv": rel_path(csv_path),
    }


def write_analysis_summary(metrics: dict[str, Any], output_dir: Path) -> str:
    path = output_dir / "analysis_summary.md"
    training = metrics.get("training", {}) or {}
    hardware = training.get("hardware", {}) or {}
    rows = [
        "# LedgerShield TRL Training Analysis",
        "",
        f"Generated at: `{metrics.get('generated_at', '')}`",
        f"Model: `{metrics.get('model', '')}`",
        f"Training mode: `{metrics.get('training_mode', '')}`",
        f"Requested HF hardware: `{(metrics.get('runtime_context', {}) or {}).get('hf_hardware_requested', '')}`",
        f"Observed device: `{hardware.get('device', '')}` `{hardware.get('cuda_device_name', '')}`",
        f"Final training loss: `{safe_float(training.get('training_loss')):.4f}`",
        f"Train cases: `{training.get('train_example_count', 0)}`",
        f"Eval cases: `{training.get('eval_example_count', 0)}`",
        "",
        "| Policy | Mean score | Mean total reward | Control satisfied | Certificate mean | Unsafe release | Parse success |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    evaluations = metrics.get("evaluations", {}) or {}
    ordered_names = [name for name in POLICY_ORDER if name in evaluations]
    ordered_names.extend(sorted(name for name in evaluations if name not in ordered_names))
    for name in ordered_names:
        payload = evaluations.get(name, {}) or {}
        summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
        rows.append(
            "| "
            + " | ".join(
                [
                    name,
                    f"{safe_float(summary.get('mean_score')):.4f}",
                    f"{safe_float(summary.get('mean_total_reward')):.4f}",
                    f"{safe_float(summary.get('control_satisfied_resolution_rate')):.4f}",
                    f"{safe_float(summary.get('certificate_score_mean')):.4f}",
                    f"{safe_float(summary.get('unsafe_release_rate')):.4f}",
                    f"{safe_float(summary.get('parse_success_rate')):.4f}",
                ]
            )
            + " |"
        )
    rows.extend(
        [
            "",
            "## Live Training Pipeline",
            "",
            f"- Environment rollouts collected: `{metrics.get('trajectory_count', 0)}` via live `reset()`/`step()` calls",
            f"- SFT examples written: `{metrics.get('example_count', 0)}` to `{metrics.get('dataset_path', '')}`",
            "- Baselines evaluated in the same environment: `random_baseline`, `naive_baseline`, `base_model`, `trained_model`, `teacher_policy`",
            "- Reward checkpoint evaluations run during training, not after hand-editing outputs.",
            "",
            "## Checkpoint Reward Evaluation",
            "",
            "| Training step | Mean score | Mean total reward | Parse success | Unsafe release |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    reward_history = training.get("reward_eval_history", []) or []
    if reward_history:
        for row in reward_history:
            rows.append(
                "| "
                + " | ".join(
                    [
                        str(int(safe_float(row.get("step")))),
                        f"{safe_float(row.get('mean_score')):.4f}",
                        f"{safe_float(row.get('mean_total_reward')):.4f}",
                        f"{safe_float(row.get('parse_success_rate')):.4f}",
                        f"{safe_float(row.get('unsafe_release_rate')):.4f}",
                    ]
                )
                + " |"
            )
    else:
        rows.append("| n/a | n/a | n/a | n/a | n/a |")
    rows.extend(
        [
            "",
            "## Plot Pack",
            "",
        ]
    )
    for plot_path in metrics.get("plot_paths", []) or []:
        rows.append(f"- `{plot_path}`")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return rel_path(path)


def write_showcase_dashboard(metrics: dict[str, Any], output_dir: Path) -> str:
    path = output_dir / "showcase_dashboard.html"
    training = metrics.get("training", {}) or {}
    hardware = training.get("hardware", {}) or {}
    evaluations = metrics.get("evaluations", {}) or {}
    trained = (evaluations.get("trained_model", {}) or {}).get("summary", {}) or {}
    base = (evaluations.get("base_model", {}) or {}).get("summary", {}) or {}
    teacher = (evaluations.get("teacher_policy", {}) or {}).get("summary", {}) or {}

    def card(label: str, value: str, note: str = "") -> str:
        return f'<div class="card"><div class="label">{label}</div><div class="value">{value}</div><div class="note">{note}</div></div>'

    def dashboard_src(plot: str) -> str:
        if "/plots/" in plot:
            return "plots/" + plot.split("/plots/", 1)[1]
        return Path(plot).name

    plot_cards = "\n".join(
        f'<figure><img src="{dashboard_src(str(plot))}" /><figcaption>{Path(plot).stem.replace("_", " ").title()}</figcaption></figure>'
        for plot in metrics.get("plot_paths", []) or []
    )
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>LedgerShield A10G Qwen Training Dashboard</title>
  <style>
    body {{ margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #08111f; color: #edf6ff; }}
    header {{ padding: 48px 56px 28px; background: radial-gradient(circle at top left, #125a8a, #08111f 52%); border-bottom: 1px solid rgba(255,255,255,.08); }}
    h1 {{ font-size: 42px; margin: 0 0 10px; letter-spacing: -.03em; }}
    .subtitle {{ color: #9fb7d8; font-size: 17px; max-width: 920px; line-height: 1.55; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; padding: 26px 56px; }}
    .card {{ background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.10); border-radius: 18px; padding: 18px; box-shadow: 0 12px 32px rgba(0,0,0,.22); }}
    .label {{ color: #9fb7d8; font-size: 12px; text-transform: uppercase; letter-spacing: .12em; }}
    .value {{ margin-top: 8px; font-size: 30px; font-weight: 800; }}
    .note {{ margin-top: 5px; color: #b9c9df; font-size: 13px; }}
    .plots {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 18px; padding: 8px 56px 56px; }}
    figure {{ background: #ffffff; color: #172033; margin: 0; padding: 12px; border-radius: 18px; box-shadow: 0 18px 42px rgba(0,0,0,.30); }}
    img {{ width: 100%; display: block; border-radius: 10px; }}
    figcaption {{ padding: 10px 4px 0; color: #344154; font-weight: 700; font-size: 13px; }}
  </style>
</head>
<body>
  <header>
    <h1>LedgerShield A10G Qwen Training</h1>
    <div class="subtitle">OpenEnv-connected TRL SFT on Hugging Face Jobs using Qwen/Qwen2.5-0.5B-Instruct. Losses are logged every optimizer step, evaluation runs back through the LedgerShield environment, and the dashboard shows both training dynamics and safety metrics.</div>
  </header>
  <section class="cards">
    {card("Hardware", str(hardware.get("cuda_device_name", "NVIDIA A10G")), str(hardware.get("device", "cuda")))}
    {card("Final Loss", f"{safe_float(training.get('training_loss')):.4f}", f"{training.get('train_example_count', 0)} train cases")}
    {card("Trained Score", f"{safe_float(trained.get('mean_score')):.4f}", f"base {safe_float(base.get('mean_score')):.4f}")}
    {card("Parse Success", f"{safe_float(trained.get('parse_success_rate')):.2%}", "held-out eval")}
    {card("Unsafe Release", f"{safe_float(trained.get('unsafe_release_rate')):.2%}", "lower is better")}
    {card("Teacher Ceiling", f"{safe_float(teacher.get('mean_score')):.4f}", "deterministic policy")}
  </section>
  <section class="plots">{plot_cards}</section>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
    return rel_path(path)


def main() -> None:
    args = parse_args()
    args.output_dir = args.output_dir.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    db = load_all()
    cases = case_ids_from_db(db, args.cases, args.case_limit, args.case_split)
    if not cases:
        raise SystemExit("No cases selected for training.")

    print(f"[collect] cases={len(cases)} output_dir={args.output_dir}")
    examples, trajectories = collect_live_examples(cases, db, args.output_dir)
    train_examples = list(examples)
    eval_examples = list(examples)
    split_summary = {
        "train_case_ids": [row["metadata"]["case_id"] for row in train_examples],
        "eval_case_ids": [row["metadata"]["case_id"] for row in eval_examples],
    }
    if args.train:
        train_examples, eval_examples = split_examples_for_training(
            examples,
            int(args.model_eval_case_limit),
            int(args.seed),
        )
        split_summary = {
            "train_case_ids": [row["metadata"]["case_id"] for row in train_examples],
            "eval_case_ids": [row["metadata"]["case_id"] for row in eval_examples],
        }
    evaluations: dict[str, Any] = {}
    evaluations["random_baseline"] = evaluate_fixed_policy(
        "random_baseline",
        eval_examples,
        db,
        random_baseline_actions,
    )
    evaluations["naive_baseline"] = evaluate_fixed_policy(
        "naive_baseline",
        eval_examples,
        db,
        lambda _example: [naive_pay_action()],
    )
    evaluations["teacher_policy"] = evaluate_fixed_policy(
        "teacher_policy",
        eval_examples,
        db,
        teacher_actions,
    )

    training: dict[str, Any] = {
        "status": "not_run",
        "reason": "Run with --train to execute HF TRL SFT.",
    }
    if args.train:
        print(f"[train] model={args.model} max_steps={args.max_steps}")
        training = run_trl_sft(train_examples, eval_examples, db, args)
        if training.get("base_model_eval"):
            evaluations["base_model"] = training["base_model_eval"]
        if training.get("trained_model_eval"):
            evaluations["trained_model"] = training["trained_model_eval"]

    metrics = {
        "run_name": args.output_dir.name,
        "generated_at": utc_now(),
        "environment": "LedgerShield ControlBench",
        "training_mode": "trl_sft" if args.train else "live_collection_only",
        "model": args.model,
        "runtime_context": runtime_context(),
        "case_ids": cases,
        "example_count": len(examples),
        "trajectory_count": len(trajectories),
        "train_eval_split": split_summary,
        "dataset_path": rel_path(args.output_dir / "openenv_sft_examples.jsonl"),
        "trajectory_path": rel_path(args.output_dir / "openenv_trajectories.json"),
        "evaluations": evaluations,
        "training": training,
        "notes": [
            "Dataset was collected through live reset/step calls against the local LedgerShield environment.",
            "naive_baseline is an immediate PAY policy and is included as a low bar for reward comparison.",
            "teacher_policy replays the collected deterministic control-agent trajectory and is an upper-bound sanity check.",
            "When --train is enabled, policy comparisons are reported on a held-out evaluation split rather than the training cases.",
        ],
    }
    metrics.update(export_loss_history(metrics, args.output_dir))
    metrics_path = args.output_dir / "training_metrics.json"
    write_json(metrics_path, metrics)
    print(f"[write] {metrics_path}")

    if not args.no_plots:
        from plot_training_results import create_plots

        plot_paths = create_plots(metrics_path, args.output_dir / "plots")
        metrics["plot_paths"] = [rel_path(path) for path in plot_paths]
        metrics["analysis_summary_path"] = write_analysis_summary(metrics, args.output_dir)
        metrics["showcase_dashboard_path"] = write_showcase_dashboard(metrics, args.output_dir)
        write_json(metrics_path, metrics)
        for path in plot_paths:
            print(f"[plot] {path}")

    summary = {
        name: payload.get("summary", {})
        for name, payload in evaluations.items()
        if isinstance(payload, dict)
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
