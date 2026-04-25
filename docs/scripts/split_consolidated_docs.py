"""Split docs/DOCUMENTATION.md into individual Mintlify pages.

Each top-level ``## <Section>`` in the consolidated documentation becomes a
standalone Markdown page under the appropriate group folder, with proper
Mintlify YAML frontmatter. Headings inside each section are demoted by one
level so the section H2 becomes the page H1 implicitly via the title.

Run from the repo root:

    python docs/scripts/split_consolidated_docs.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "docs" / "DOCUMENTATION.md"
DOCS_DIR = REPO_ROOT / "docs"


@dataclass(frozen=True)
class SectionSpec:
    heading: str
    output: str
    title: str
    description: str
    icon: str
    sidebar: str | None = None


SECTIONS: list[SectionSpec] = [
    SectionSpec(
        heading="Documentation Hub",
        output="overview/documentation-hub.md",
        title="Documentation Hub",
        description="Reading paths, code landmarks, and how the docs map to the LedgerShield ControlBench codebase.",
        icon="book-open",
        sidebar="Hub",
    ),
    SectionSpec(
        heading="Documentation Index",
        output="overview/documentation-index.md",
        title="Documentation Index",
        description="Quick navigation to every documentation page, organized by category.",
        icon="list",
        sidebar="Index",
    ),
    SectionSpec(
        heading="Benchmark Card",
        output="benchmark/benchmark-card.md",
        title="Benchmark Card",
        description="One-page benchmark identity, official tracks, headline metrics, and result classes.",
        icon="id-card",
        sidebar="Benchmark Card",
    ),
    SectionSpec(
        heading="Tasks",
        output="benchmark/tasks.md",
        title="Tasks & Scoring",
        description="Task families A–E, the 21 curated cases, output contracts, and per-dimension scoring weights.",
        icon="list-checks",
        sidebar="Tasks",
    ),
    # NOTE: API Reference is split into multiple curated pages under
    # ``docs/api-reference/`` and ``docs/api-reference.md``. It is intentionally
    # not regenerated from ``DOCUMENTATION.md`` so the sidebar grouping stays
    # intact. Update those files by hand if the consolidated source changes.
    SectionSpec(
        heading="Architecture",
        output="architecture/overview.md",
        title="Architecture",
        description="System layers, hidden world state, episode lifecycle, reward design, institutional memory, certificates, and TrustGraph.",
        icon="layers",
        sidebar="Overview",
    ),
    SectionSpec(
        heading="ASHTG Theory",
        output="architecture/ashtg-theory.md",
        title="ASHTG Theory",
        description="Adversarial Sequential Hypothesis Testing Game — the theoretical framework grounding LedgerShield's rewards, stopping rules, and grading.",
        icon="brain-circuit",
        sidebar="ASHTG Theory",
    ),
    SectionSpec(
        heading="Development",
        output="guides/development.md",
        title="Development",
        description="Local setup, the test suite, CI expectations, repo/file map, and extension guidance for contributors.",
        icon="code",
        sidebar="Development",
    ),
    SectionSpec(
        heading="Deployment",
        output="guides/deployment.md",
        title="Deployment",
        description="Local, Docker, and Hugging Face Space deployment. Environment variables, deployment profiles, and troubleshooting.",
        icon="rocket",
        sidebar="Deployment",
    ),
    SectionSpec(
        heading="Demo Script",
        output="guides/demo-script.md",
        title="Demo Script",
        description="Frozen 5-step demo walkthrough for CASE-D-001, optimized for judges and live demos.",
        icon="play",
        sidebar="Demo Script",
    ),
    SectionSpec(
        heading="Mini-Blog",
        output="blog/mini-blog.md",
        title="Mini-Blog",
        description="Short-form story explaining what LedgerShield does, why it matters, and how it differs from one-shot benchmarks.",
        icon="newspaper",
        sidebar="Mini-Blog",
    ),
    SectionSpec(
        heading="HF Mini-Blog Final",
        output="blog/hf-mini-blog.md",
        title="HF Mini-Blog (Final)",
        description="The final Hugging Face mini-blog package shipped with the Round 2 submission.",
        icon="megaphone",
        sidebar="HF Mini-Blog",
    ),
    SectionSpec(
        heading="Submission Contract",
        output="contracts/submission-contract.md",
        title="Submission Contract",
        description="The locked Round 2 submission contract — what is in scope, what is frozen, and how it is evaluated.",
        icon="file-signature",
        sidebar="Submission Contract",
    ),
    SectionSpec(
        heading="Plan A Final Deliverables",
        output="reports/plan-a-deliverables.md",
        title="Plan A Final Deliverables",
        description="The full Plan A handoff: deliverables, status, and acceptance criteria.",
        icon="package-check",
        sidebar="Plan A Deliverables",
    ),
    SectionSpec(
        heading="A3 Case Audit Report",
        output="reports/a3-case-audit.md",
        title="A3 — Case Audit Report",
        description="Per-case audit of the 21-case curated catalog, including labels, evidence quality, and difficulty calibration.",
        icon="clipboard-check",
        sidebar="A3 Case Audit",
    ),
    SectionSpec(
        heading="A4 Portfolio Track Report",
        output="reports/a4-portfolio-track.md",
        title="A4 — Portfolio Track Report",
        description="Portfolio track design, AP-week capacity model, and institutional-utility scoring.",
        icon="briefcase",
        sidebar="A4 Portfolio Track",
    ),
    SectionSpec(
        heading="A7 Demo Asset Package",
        output="reports/a7-demo-assets.md",
        title="A7 — Demo Asset Package",
        description="Frozen demo asset bundle: scripts, traces, screenshots, and judge-facing materials.",
        icon="image",
        sidebar="A7 Demo Assets",
    ),
    SectionSpec(
        heading="A8 Publishing Guide",
        output="reports/a8-publishing-guide.md",
        title="A8 — Publishing Guide",
        description="Publishing checklist for the Hugging Face Space, leaderboard artifacts, and submission package.",
        icon="upload",
        sidebar="A8 Publishing Guide",
    ),
    SectionSpec(
        heading="P0-0 Verification Report",
        output="verification/p0-0.md",
        title="P0-0 — Submission Contract Locked",
        description="Verification that the Round 2 submission contract is locked and matches the implementation.",
        icon="check-square",
        sidebar="P0-0",
    ),
    SectionSpec(
        heading="P0-1 Verification Report",
        output="verification/p0-1.md",
        title="P0-1 — Runtime Validation",
        description="Verification report for the 9-endpoint runtime validation pass.",
        icon="check-square",
        sidebar="P0-1",
    ),
    SectionSpec(
        heading="P0-2 Verification Report",
        output="verification/p0-2.md",
        title="P0-2 — Benchmark Artifacts Frozen",
        description="Verification that the benchmark report, leaderboard, and case database are frozen for Round 2.",
        icon="check-square",
        sidebar="P0-2",
    ),
    SectionSpec(
        heading="P0-3 Verification Report",
        output="verification/p0-3.md",
        title="P0-3 — Case Audit Complete",
        description="Verification that the 21-case curated catalog has been audited and accepted.",
        icon="check-square",
        sidebar="P0-3",
    ),
    SectionSpec(
        heading="P0-4 Verification Report",
        output="verification/p0-4.md",
        title="P0-4 — Portfolio Track Strengthened",
        description="Verification that the portfolio track passes its strengthened acceptance criteria.",
        icon="check-square",
        sidebar="P0-4",
    ),
    SectionSpec(
        heading="P0-5 Verification Report",
        output="verification/p0-5.md",
        title="P0-5 — Evaluator Hardened",
        description="Verification that the evaluator handles malformed submissions, degenerate evidence, and edge cases.",
        icon="check-square",
        sidebar="P0-5",
    ),
    SectionSpec(
        heading="P0-6 Verification Report",
        output="verification/p0-6.md",
        title="P0-6 — README Cleanup",
        description="Verification that the README has been cleaned up and matches the locked submission contract.",
        icon="check-square",
        sidebar="P0-6",
    ),
    SectionSpec(
        heading="P0-7 Verification Report",
        output="verification/p0-7.md",
        title="P0-7 — Demo Assets Frozen",
        description="Verification that the demo assets have been frozen for the Round 2 walkthrough.",
        icon="check-square",
        sidebar="P0-7",
    ),
    SectionSpec(
        heading="P0-8 Verification Report",
        output="verification/p0-8.md",
        title="P0-8 — Mini-Blog Verified",
        description="Verification that the mini-blog package is final and consistent with the README and benchmark card.",
        icon="check-square",
        sidebar="P0-8",
    ),
    SectionSpec(
        heading="Implementation Deep-Dive",
        output="implementation/deep-dive.md",
        title="Implementation Deep-Dive",
        description="File-level walkthrough of every server module, including environment, grading, world state, certificates, and tooling.",
        icon="microscope",
        sidebar="Deep-Dive",
    ),
]


def yaml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def demote_headings(body: str) -> str:
    """Demote every heading by one level so the section H2 becomes a doc H1.

    The page title is rendered from frontmatter, so we strip the first
    occurrence of the original ``## ...`` heading and shift the rest down.
    """
    lines = body.splitlines()
    out: list[str] = []
    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if match:
            hashes, text = match.groups()
            if len(hashes) == 1:
                out.append(line)
            else:
                out.append(f"{'#' * (len(hashes) - 1)} {text}")
        else:
            out.append(line)
    return "\n".join(out).strip() + "\n"


def fix_internal_links(body: str, section_to_path: dict[str, str]) -> str:
    """Rewrite ``](#section-anchor)`` links to point at the new MDX pages."""

    def repl(match: re.Match[str]) -> str:
        anchor = match.group(1)
        target = section_to_path.get(anchor)
        if not target:
            return match.group(0)
        return f"](/{target})"

    pattern = re.compile(r"\]\(#([a-z0-9-]+)\)")
    return pattern.sub(repl, body)


# MDX cannot parse HTML comments outside code fences. Strip the
# ``<!-- sync:foo:start --> ... <!-- sync:foo:end -->`` markers used by
# ``sync_benchmark_metadata.py`` in the source documentation.
_SYNC_COMMENT_RE = re.compile(r"^[ \t]*<!--\s*sync:[^>]*-->[ \t]*\r?\n?", re.MULTILINE)


def strip_sync_markers(body: str) -> str:
    return _SYNC_COMMENT_RE.sub("", body)


def slug_for(heading: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")


def main() -> None:
    raw = SOURCE.read_text(encoding="utf-8")
    section_pattern = re.compile(r"^## (.+?)$", re.MULTILINE)
    matches = list(section_pattern.finditer(raw))

    section_bodies: dict[str, str] = {}
    for idx, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw)
        body = raw[start:end].strip("\n")
        body = body.lstrip("\n").rstrip() + "\n"
        section_bodies[heading] = body

    section_to_path = {
        slug_for(spec.heading): spec.output.removesuffix(".md") for spec in SECTIONS
    }

    for spec in SECTIONS:
        body = section_bodies.get(spec.heading)
        if body is None:
            print(f"warn: missing section '{spec.heading}'")
            continue

        body = demote_headings(body)
        body = fix_internal_links(body, section_to_path)
        body = strip_sync_markers(body)
        body = body.replace("](../", "](https://github.com/BiradarScripts/Meta-s-LedgerShield/blob/main/")

        front = [
            "---",
            f'title: "{yaml_escape(spec.title)}"',
            f'description: "{yaml_escape(spec.description)}"',
            f'icon: "{spec.icon}"',
        ]
        if spec.sidebar:
            front.append(f'sidebarTitle: "{yaml_escape(spec.sidebar)}"')
        front.append("---\n")

        out_path = DOCS_DIR / spec.output
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(front) + "\n" + body, encoding="utf-8")
        print(f"wrote {out_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
