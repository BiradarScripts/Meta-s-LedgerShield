#!/usr/bin/env python3
"""Build the LedgerShield Exquisite Training HTML dashboard."""

from __future__ import annotations

import argparse
import html
from pathlib import Path
from typing import Any

try:  # pragma: no cover
    from .common import EXQUISITE_ROOT, maybe_float, read_csv, read_json, read_jsonl, rel_path, utc_now, write_json
except ImportError:  # pragma: no cover
    from common import EXQUISITE_ROOT, maybe_float, read_csv, read_json, read_jsonl, rel_path, utc_now, write_json  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Exquisite dashboard.")
    parser.add_argument("--artifact-root", type=Path, default=EXQUISITE_ROOT)
    parser.add_argument("--report-dir", type=Path, default=EXQUISITE_ROOT / "reports")
    parser.add_argument("--plot-dir", type=Path, default=EXQUISITE_ROOT / "plots")
    parser.add_argument("--output-dir", type=Path, default=EXQUISITE_ROOT / "dashboard")
    return parser.parse_args()


def best_row(matrix: list[dict[str, Any]]) -> dict[str, Any] | None:
    numeric = [(maybe_float(row.get("mean_score")), row) for row in matrix]
    numeric = [(score, row) for score, row in numeric if score is not None]
    if not numeric:
        return None
    return max(numeric, key=lambda pair: pair[0])[1]


def policy_label(row: dict[str, Any]) -> str:
    model = str(row.get("model") or "")
    policy = str(row.get("policy") or "")
    if model and model != "-" and model not in policy:
        return f"{policy} {model}"
    return policy


def metric_cards(matrix: list[dict[str, Any]], summary: dict[str, Any], preferences: int) -> list[dict[str, str]]:
    best = best_row(matrix) or {}
    sft = next((row for row in matrix if row.get("policy_key") == "trained_model"), {})
    grpo = next((row for row in matrix if row.get("policy_key") == "grpo_0_5b"), {})
    sft_score = maybe_float(sft.get("mean_score"))
    grpo_score = maybe_float(grpo.get("mean_score"))
    improvement = "PENDING" if sft_score is None or grpo_score is None else f"{grpo_score - sft_score:+.4f}"
    return [
        {"label": "Best policy score", "value": str(best.get("mean_score", "PENDING")), "note": policy_label(best) if best else "pending"},
        {"label": "Best GRPO improvement", "value": improvement, "note": "over SFT 0.5B"},
        {"label": "Unsafe release", "value": str(best.get("unsafe_release", "PENDING")), "note": "best numeric policy"},
        {"label": "Parse success", "value": str(best.get("parse_success", "PENDING")), "note": "best numeric policy"},
        {"label": "Certificate score", "value": str(best.get("certificate_score", "PENDING")), "note": "best numeric policy"},
        {"label": "Control satisfaction", "value": str(best.get("control_satisfied", "PENDING")), "note": "best numeric policy"},
        {"label": "Self-play candidates", "value": str(summary.get("selfplay_candidate_count", 0)), "note": "generated candidates"},
        {"label": "Preference pairs", "value": str(preferences), "note": "best-vs-worst falsifier pairs"},
        {"label": "GPU hours", "value": "PENDING", "note": "filled after HF jobs"},
    ]


def table_html(matrix: list[dict[str, Any]]) -> str:
    columns = ["policy", "model", "method", "mean_score", "certificate_score", "control_satisfied", "unsafe_release", "parse_success", "status"]
    header = "".join(f"<th>{html.escape(column)}</th>" for column in columns)
    body = []
    for row in matrix:
        body.append("<tr>" + "".join(f"<td>{html.escape(str(row.get(column, '')))}</td>" for column in columns) + "</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def plot_cards(manifest: dict[str, Any], limit: int | None = None) -> str:
    plots = manifest.get("plots", []) if isinstance(manifest, dict) else []
    if limit:
        plots = plots[:limit]
    cards = []
    for plot in plots:
        filename = html.escape(str(plot.get("filename", "")))
        caption = html.escape(str(plot.get("caption", "")))
        cards.append(f'<figure><img src="../plots/{filename}" alt="{filename}" /><figcaption>{caption}</figcaption></figure>')
    return "".join(cards)


def build_html(cards: list[dict[str, str]], matrix: list[dict[str, Any]], manifest: dict[str, Any]) -> str:
    card_html = "".join(
        f'<div class="card"><div class="label">{html.escape(card["label"])}</div><div class="value">{html.escape(card["value"])}</div><div class="note">{html.escape(card["note"])}</div></div>'
        for card in cards
    )
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LedgerShield Exquisite Training Dashboard</title>
  <style>
    :root {{ color-scheme: dark; }}
    body {{ margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #08111f; color: #edf6ff; }}
    header {{ padding: 54px 6vw 32px; background: radial-gradient(circle at top left, #1d4ed8, #08111f 54%); border-bottom: 1px solid rgba(255,255,255,.10); }}
    h1 {{ margin: 0 0 12px; font-size: clamp(34px, 5vw, 62px); letter-spacing: -.05em; }}
    h2 {{ margin: 36px 6vw 14px; font-size: 24px; }}
    .subtitle {{ color: #b8c7dd; max-width: 1040px; line-height: 1.55; font-size: 17px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; padding: 26px 6vw; }}
    .card {{ background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.12); border-radius: 18px; padding: 18px; box-shadow: 0 14px 36px rgba(0,0,0,.25); }}
    .label {{ color: #9fb7d8; font-size: 12px; text-transform: uppercase; letter-spacing: .12em; }}
    .value {{ margin-top: 8px; font-size: 30px; font-weight: 850; }}
    .note {{ margin-top: 5px; color: #b9c9df; font-size: 13px; }}
    .panel {{ margin: 0 6vw 24px; background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.10); border-radius: 20px; overflow: hidden; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,.08); text-align: left; }}
    th {{ color: #bfdbfe; background: rgba(37,99,235,.22); }}
    .plots {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 18px; padding: 0 6vw 54px; }}
    figure {{ background: #ffffff; color: #172033; margin: 0; padding: 12px; border-radius: 18px; box-shadow: 0 18px 42px rgba(0,0,0,.30); }}
    img {{ width: 100%; display: block; border-radius: 10px; }}
    figcaption {{ padding: 10px 4px 0; color: #344154; font-weight: 700; font-size: 13px; line-height: 1.4; }}
    code {{ color: #bfdbfe; }}
  </style>
</head>
<body>
  <header>
    <h1>LedgerShield Exquisite Training Layer</h1>
    <div class="subtitle">Environment-in-the-loop self-improvement for enterprise AP control agents: SFT warm start, self-play candidate generation, LedgerShield execution, deterministic falsifier reward, GRPO online RL, optional DPO distillation, and a 40+ plot evidence pack.</div>
  </header>
  <section class="cards">{card_html}</section>
  <h2>Policy Matrix</h2>
  <section class="panel">{table_html(matrix)}</section>
  <h2>Executive Plots</h2>
  <section class="plots">{plot_cards(manifest, 6)}</section>
  <h2>Full Evidence Pack</h2>
  <section class="plots">{plot_cards(manifest)}</section>
</body>
</html>
"""


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    matrix = read_csv(args.report_dir / "final_policy_matrix.csv")
    summary = read_json(args.report_dir / "exquisite_training_summary.json", default={}) or {}
    manifest = read_json(args.report_dir / "visualization_manifest.json", default={}) or {}
    preferences = len(read_jsonl(args.artifact_root / "selfplay-0.5b" / "falsifier_preferences.jsonl"))
    cards = metric_cards(matrix, summary, preferences)
    dashboard_data = {
        "generated_at": utc_now(),
        "cards": cards,
        "matrix": matrix,
        "summary": summary,
        "manifest": manifest,
        "paths": {
            "dashboard": rel_path(args.output_dir / "index.html"),
            "data": rel_path(args.output_dir / "dashboard_data.json"),
        },
    }
    write_json(args.output_dir / "dashboard_data.json", dashboard_data)
    (args.output_dir / "index.html").write_text(build_html(cards, matrix, manifest), encoding="utf-8")
    print(args.output_dir / "index.html")


if __name__ == "__main__":
    main()
