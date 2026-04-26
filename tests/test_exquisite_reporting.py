from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXQUISITE_ROOT = REPO_ROOT / "artifacts" / "exquisite-training"


def run_command(*args: str) -> None:
    subprocess.run([sys.executable, *args], cwd=REPO_ROOT, check=True)


def test_exquisite_rebuild_marks_1_5b_as_fast_profile(tmp_path: Path):
    report_dir = tmp_path / "reports"
    plot_dir = tmp_path / "plots"
    dashboard_dir = tmp_path / "dashboard"
    report_dir.mkdir(parents=True, exist_ok=True)

    for filename in ["hf_exquisite_launches.json", "ablation_results.json"]:
        shutil.copy2(EXQUISITE_ROOT / "reports" / filename, report_dir / filename)

    run_command(
        "training/exquisite/evaluate_exquisite_policy.py",
        "--artifact-root",
        str(EXQUISITE_ROOT),
        "--output-dir",
        str(report_dir),
    )
    run_command(
        "training/exquisite/plot_exquisite_training_results.py",
        "--artifact-root",
        str(EXQUISITE_ROOT),
        "--report-dir",
        str(report_dir),
        "--output-dir",
        str(plot_dir),
    )
    run_command(
        "training/exquisite/build_exquisite_dashboard.py",
        "--artifact-root",
        str(EXQUISITE_ROOT),
        "--report-dir",
        str(report_dir),
        "--plot-dir",
        str(plot_dir),
        "--output-dir",
        str(dashboard_dir),
    )
    run_command(
        "training/exquisite/render_exquisite_report.py",
        "--artifact-root",
        str(EXQUISITE_ROOT),
        "--report-dir",
        str(report_dir),
        "--dashboard-dir",
        str(dashboard_dir),
    )

    matrix = json.loads((report_dir / "final_policy_matrix.json").read_text(encoding="utf-8"))
    sft_row = next(row for row in matrix if row.get("policy_key") == "sft_1_5b")
    assert sft_row["run_profile"] == "fast-profile scaling run"

    report_text = (report_dir / "exquisite_training_report.md").read_text(encoding="utf-8")
    assert "Fast-profile scaling note" in report_text
    assert "fast-profile scaling run included as supporting model-scaling evidence" in report_text

    dashboard_html = (dashboard_dir / "index.html").read_text(encoding="utf-8")
    assert "fast-profile scaling run" in dashboard_html

    manifest = json.loads((report_dir / "visualization_manifest.json").read_text(encoding="utf-8"))
    scaling_plot = next(plot for plot in manifest["plots"] if plot["filename"] == "03_scaling_law_score_vs_model_size.png")
    assert "fast-profile" in scaling_plot["caption"]
