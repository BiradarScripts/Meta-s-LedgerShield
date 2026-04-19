from __future__ import annotations

import argparse
import json
from pathlib import Path


HTML_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>LedgerShield v2 Before/After</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; }
    .grid { display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 16px; }
    .card { border: 1px solid #d0d7de; border-radius: 8px; padding: 16px; }
    .metric { font-size: 14px; color: #57606a; }
    .value { font-size: 28px; margin-top: 8px; }
  </style>
</head>
<body>
  <h1>LedgerShield v2 Before / After</h1>
  <div class="grid">
    {cards}
  </div>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a simple before/after metric card page")
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def metric_card(label: str, before: float, after: float) -> str:
    return (
        '<div class="card">'
        f'<div class="metric">{label}</div>'
        f'<div class="value">{before:.3f} → {after:.3f}</div>'
        "</div>"
    )


def main() -> None:
    args = parse_args()
    before = load(args.before)
    after = load(args.after)
    metrics = [
        (
            "Control-Satisfied Resolution",
            float(before["public_benchmark"]["control_satisfied_resolution_rate"]),
            float(after["public_benchmark"]["control_satisfied_resolution_rate"]),
        ),
        (
            "Institutional Utility",
            float(before["public_benchmark"]["institutional_utility_stats"]["mean"]),
            float(after["public_benchmark"]["institutional_utility_stats"]["mean"]),
        ),
        (
            "Unsafe Release Rate",
            float(before["public_benchmark"]["unsafe_release_rate"]),
            float(after["public_benchmark"]["unsafe_release_rate"]),
        ),
        (
            "Holdout Mean",
            float(before["holdout_challenge"]["score_stats"]["mean"]),
            float(after["holdout_challenge"]["score_stats"]["mean"]),
        ),
    ]
    html = HTML_TEMPLATE.format(cards="\n".join(metric_card(label, b, a) for label, b, a in metrics))
    Path(args.output).write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
