#!/usr/bin/env python3
"""Build the LedgerShield Exquisite Training HTML dashboard."""

from __future__ import annotations

import argparse
import html
from pathlib import Path
from typing import Any

try:  # pragma: no cover
    from .common import EXQUISITE_ROOT, maybe_float, read_csv, read_json, read_jsonl, rel_path, safe_float, utc_now, write_json
except ImportError:  # pragma: no cover
    from common import EXQUISITE_ROOT, maybe_float, read_csv, read_json, read_jsonl, rel_path, safe_float, utc_now, write_json  # type: ignore


EXECUTIVE_PLOTS = [
    "01_final_policy_ladder.png",
    "02_sft_vs_grpo_grouped_bar.png",
    "03_scaling_law_score_vs_model_size.png",
    "04_score_safety_frontier_all_policies.png",
    "05_teacher_gap_closure.png",
    "06_exquisite_pipeline_diagram.png",
]
TRAINING_DYNAMICS_PLOTS = [f"{index:02d}_" for index in range(7, 17)]
SELFPLAY_PLOTS = [f"{index:02d}_" for index in range(17, 27)]
PER_CASE_PLOTS = [f"{index:02d}_" for index in range(27, 37)]
SAFETY_PLOTS = [f"{index:02d}_" for index in range(37, 47)]
ABLATION_PLOTS = [f"{index:02d}_" for index in range(47, 57)]


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


def load_manifest(report_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = read_json(report_dir / "visualization_manifest.json", default={}) or {}
    plots = manifest.get("plots", []) if isinstance(manifest, dict) else []
    return manifest, plots if isinstance(plots, list) else []


def pick_plots(plots: list[dict[str, Any]], patterns: list[str]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for plot in plots:
        filename = str(plot.get("filename", ""))
        if filename in EXECUTIVE_PLOTS or any(filename.startswith(pattern) for pattern in patterns):
            selected.append(plot)
    if patterns and patterns[0] not in {"01_"}:
        selected = [plot for plot in selected if str(plot.get("filename", "")) not in EXECUTIVE_PLOTS]
    return selected


def launches_summary(report_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    launches = read_json(report_dir / "hf_exquisite_launches.json", default={}) or {}
    jobs = launches.get("jobs", []) if isinstance(launches, dict) else []
    live_jobs = [row for row in jobs if isinstance(row, dict) and not row.get("exclude_from_live_reports")]
    return launches if isinstance(launches, dict) else {}, live_jobs


def metric_cards(matrix: list[dict[str, Any]], summary: dict[str, Any], preferences: int, jobs: list[dict[str, Any]]) -> list[dict[str, str]]:
    best = best_row(matrix) or {}
    sft = next((row for row in matrix if row.get("policy_key") == "trained_model"), {})
    grpo = next((row for row in matrix if row.get("policy_key") == "grpo_0_5b"), {})
    sft_score = maybe_float(sft.get("mean_score"))
    grpo_score = maybe_float(grpo.get("mean_score"))
    improvement = "PENDING" if sft_score is None or grpo_score is None else f"{grpo_score - sft_score:+.4f}"
    planned_gpu_hours = sum(safe_float(row.get("timeout_hours")) * safe_float(row.get("gpu_count"), 1.0) for row in jobs)
    planned_cost = sum(safe_float(row.get("max_cost_usd")) for row in jobs)
    return [
        {"label": "Best policy score", "value": str(best.get("mean_score", "PENDING")), "note": policy_label(best) if best else "pending"},
        {"label": "Best GRPO improvement", "value": improvement, "note": "over SFT 0.5B"},
        {"label": "Unsafe release", "value": str(best.get("unsafe_release", "PENDING")), "note": "best numeric policy"},
        {"label": "Parse success", "value": str(best.get("parse_success", "PENDING")), "note": "best numeric policy"},
        {"label": "Certificate score", "value": str(best.get("certificate_score", "PENDING")), "note": "best numeric policy"},
        {"label": "Control satisfaction", "value": str(best.get("control_satisfied", "PENDING")), "note": "best numeric policy"},
        {"label": "Self-play candidates", "value": str(summary.get("selfplay_candidate_count", 0)), "note": "generated candidates"},
        {"label": "Preference pairs", "value": str(preferences), "note": "best-vs-worst falsifier pairs"},
        {"label": "GPU hours", "value": f"{planned_gpu_hours:.1f}" if jobs else "PENDING", "note": f"planned cap, ${planned_cost:.2f} max" if jobs else "filled after HF jobs"},
    ]


def table_html(rows: list[dict[str, Any]], columns: list[str]) -> str:
    header = "".join(f"<th>{html.escape(column)}</th>" for column in columns)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{html.escape(str(row.get(column, '')))}</td>" for column in columns) + "</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def plot_cards(plots: list[dict[str, Any]], *, empty_message: str) -> str:
    if not plots:
        return f'<div class="empty">{html.escape(empty_message)}</div>'
    cards = []
    for plot in plots:
        filename = html.escape(str(plot.get("filename", "")))
        caption = html.escape(str(plot.get("caption", "")))
        cards.append(f'<figure><img src="../plots/{filename}" alt="{filename}" /><figcaption>{caption}</figcaption></figure>')
    return "".join(cards)


def artifact_list(report_dir: Path) -> str:
    inventory_path = report_dir / "artifact_inventory.md"
    if not inventory_path.exists():
        return '<div class="empty">Artifact inventory pending.</div>'
    items = []
    for line in inventory_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("- `") and line.endswith("`"):
            items.append(f"<li><code>{html.escape(line[3:-1])}</code></li>")
    return f"<ul>{''.join(items)}</ul>" if items else '<div class="empty">Artifact inventory pending.</div>'


def reproduction_commands() -> str:
    return """<pre><code>python training/exquisite/collect_selfplay_rollouts.py --mode smoke --case-limit 6 --eval-case-limit 2 --num-generations 4
python training/exquisite/evaluate_exquisite_policy.py
python training/exquisite/plot_exquisite_training_results.py
python training/exquisite/build_exquisite_dashboard.py
python training/exquisite/render_exquisite_report.py

export HF_TOKEN_PRIMARY="..."
export HF_TOKEN_SECONDARY="..."
python training/exquisite/launch_exquisite_jobs.py --monitor</code></pre>"""


def section_html(title: str, subtitle: str, content: str, *, panel_class: str = "plots") -> str:
    return f"""
    <section class="section">
      <div class="section-head">
        <h2>{html.escape(title)}</h2>
        <p>{html.escape(subtitle)}</p>
      </div>
      <div class="{panel_class}">{content}</div>
    </section>
    """


def build_html(cards: list[dict[str, str]], matrix: list[dict[str, Any]], manifest_plots: list[dict[str, Any]], jobs: list[dict[str, Any]], report_dir: Path) -> str:
    card_html = "".join(
        f'<div class="card"><div class="label">{html.escape(card["label"])}</div><div class="value">{html.escape(card["value"])}</div><div class="note">{html.escape(card["note"])}</div></div>'
        for card in cards
    )
    executive = [plot for plot in manifest_plots if str(plot.get("filename", "")) in EXECUTIVE_PLOTS]
    training = pick_plots(manifest_plots, TRAINING_DYNAMICS_PLOTS)
    selfplay = pick_plots(manifest_plots, SELFPLAY_PLOTS)
    per_case = pick_plots(manifest_plots, PER_CASE_PLOTS)
    safety = pick_plots(manifest_plots, SAFETY_PLOTS)
    ablations = pick_plots(manifest_plots, ABLATION_PLOTS)
    job_columns = ["name", "hardware", "last_status", "timeout", "hourly_cost_usd", "max_cost_usd", "url"]
    policy_columns = ["policy", "model", "method", "mean_score", "certificate_score", "control_satisfied", "unsafe_release", "parse_success", "status"]
    launch_panel = (
        f'<div class="table-wrap">{table_html(jobs, job_columns)}</div>'
        if jobs
        else '<div class="empty">No Hugging Face jobs launched yet.</div>'
    )
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LedgerShield Exquisite Training Dashboard</title>
  <style>
    :root {{
      --bg: #0a1324;
      --panel: rgba(255,255,255,.08);
      --panel-strong: rgba(255,255,255,.12);
      --line: rgba(255,255,255,.10);
      --text: #edf5ff;
      --muted: #a9bdd8;
      --accent: #7dd3fc;
      --accent-strong: #f59e0b;
      color-scheme: dark;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(56,189,248,.22), transparent 34%),
        radial-gradient(circle at top right, rgba(245,158,11,.16), transparent 26%),
        linear-gradient(180deg, #091121 0%, #0d1b31 48%, #091121 100%);
      color: var(--text);
    }}
    header {{
      padding: 58px 6vw 28px;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{
      margin: 0 0 14px;
      font-size: clamp(36px, 5vw, 66px);
      letter-spacing: -.05em;
      line-height: .92;
    }}
    h2 {{
      margin: 0;
      font-size: 24px;
      letter-spacing: -.03em;
    }}
    .section-head p, .subtitle {{
      color: var(--muted);
      line-height: 1.6;
      max-width: 1120px;
      margin: 10px 0 0;
      font-size: 16px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 14px;
      padding: 28px 6vw 8px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 18px;
      box-shadow: 0 20px 44px rgba(0,0,0,.22);
      backdrop-filter: blur(14px);
    }}
    .label {{
      color: #c2d7f1;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .13em;
    }}
    .value {{
      margin-top: 8px;
      font-size: 30px;
      font-weight: 760;
    }}
    .note {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 13px;
    }}
    .section {{
      padding: 26px 6vw 0;
    }}
    .table-wrap, .artifact-panel, .command-panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      overflow: hidden;
      box-shadow: 0 18px 40px rgba(0,0,0,.20);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      padding: 11px 12px;
      border-bottom: 1px solid rgba(255,255,255,.07);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      color: #dbeafe;
      background: rgba(14, 116, 144, .24);
    }}
    .plots {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 18px;
    }}
    figure {{
      background: #ffffff;
      color: #172033;
      margin: 0;
      padding: 12px;
      border-radius: 18px;
      box-shadow: 0 18px 42px rgba(0,0,0,.28);
    }}
    img {{
      width: 100%;
      display: block;
      border-radius: 10px;
    }}
    figcaption {{
      padding: 10px 4px 0;
      color: #344154;
      font-weight: 700;
      font-size: 13px;
      line-height: 1.42;
    }}
    .empty {{
      background: var(--panel);
      border: 1px dashed var(--line);
      border-radius: 20px;
      padding: 24px;
      color: var(--muted);
    }}
    ul {{
      margin: 0;
      padding: 18px 22px 18px 40px;
    }}
    li {{
      margin: 8px 0;
    }}
    pre {{
      margin: 0;
      padding: 18px 20px;
      overflow-x: auto;
      white-space: pre-wrap;
      color: #dbeafe;
      background: rgba(2,6,23,.42);
    }}
    code {{ font-family: "IBM Plex Mono", "SFMono-Regular", monospace; }}
    footer {{
      padding: 26px 6vw 54px;
      color: var(--muted);
      font-size: 13px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>LedgerShield Exquisite Training Layer</h1>
    <div class="subtitle">Environment-in-the-loop self-improvement for enterprise AP control agents: SFT warm start, self-play candidate generation, LedgerShield execution, deterministic falsifier reward, GRPO online RL, optional DPO distillation, and a 56-plot evidence pack.</div>
  </header>
  <section class="cards">{card_html}</section>
  {section_html("Policy Matrix", "Compares baseline, SFT, GRPO, DPO, and teacher policies on the same held-out evaluation slice. Budget-cut runs are excluded from this live view.", f'<div class="table-wrap">{table_html(matrix, policy_columns)}</div>', panel_class='')}
  {section_html("Launch Status", "Tracks the live Hugging Face job submissions, hardware, timeout cap, and monitor URL for the reduced-budget Exquisite run matrix.", launch_panel, panel_class='')}
  {section_html("Executive Plots", "Judge-facing summary plots for the main narrative: policy ladder, scaling law, safety frontier, teacher-gap closure, and pipeline structure.", plot_cards(executive, empty_message="Executive plots pending."))}
  {section_html("GRPO Training Dynamics", "Reward stability, completion behavior, parse robustness, unsafe-release suppression, and certificate/control trends over RL updates.", plot_cards(training, empty_message="GRPO dynamics plots pending HF history files."))}
  {section_html("Self-Play And Falsifier", "Evidence that candidate plans were actually generated, executed, ranked, and separated by the deterministic audit stack.", plot_cards(selfplay, empty_message="Self-play plots pending candidate collection."))}
  {section_html("Safety And Audit", "Institutional safety, auditability, calibration, review burden, and score-safety trade-off views across policies.", plot_cards(safety, empty_message="Safety plots pending policy metrics."))}
  {section_html("Per-Case Analysis", "Where GRPO helped, where it hurt, and which task families remain teacher-gap bottlenecks.", plot_cards(per_case, empty_message="Per-case plots pending evaluation files."))}
  {section_html("Ablations", "Reward, temperature, generation-count, warm-start, steps, and DPO-after-GRPO sensitivity views.", plot_cards(ablations, empty_message="Ablation plots pending dedicated HF runs."))}
  {section_html("Artifact Inventory", "Every report, matrix, and run directory currently tracked under artifacts/exquisite-training.", artifact_list(report_dir), panel_class="artifact-panel")}
  {section_html("Reproduction Commands", "Local smoke commands and the Hugging Face launch command used to reproduce the full Exquisite pipeline.", reproduction_commands(), panel_class="command-panel")}
  <footer>Generated at {html.escape(utc_now())}. Report artifact: <code>{html.escape(rel_path(report_dir / "exquisite_training_report.md"))}</code></footer>
</body>
</html>
"""


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    matrix = read_csv(args.report_dir / "final_policy_matrix.csv")
    summary = read_json(args.report_dir / "exquisite_training_summary.json", default={}) or {}
    _, manifest_plots = load_manifest(args.report_dir)
    _, jobs = launches_summary(args.report_dir)
    preferences = len(read_jsonl(args.artifact_root / "selfplay-0.5b" / "falsifier_preferences.jsonl"))
    cards = metric_cards(matrix, summary, preferences, jobs)
    dashboard_data = {
        "generated_at": utc_now(),
        "cards": cards,
        "matrix": matrix,
        "summary": summary,
        "jobs": jobs,
        "manifest": manifest_plots,
        "paths": {
            "dashboard": rel_path(args.output_dir / "index.html"),
            "data": rel_path(args.output_dir / "dashboard_data.json"),
        },
    }
    write_json(args.output_dir / "dashboard_data.json", dashboard_data)
    (args.output_dir / "index.html").write_text(build_html(cards, matrix, manifest_plots, jobs, args.report_dir), encoding="utf-8")
    print(args.output_dir / "index.html")


if __name__ == "__main__":
    main()
