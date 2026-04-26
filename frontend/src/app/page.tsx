"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  ArrowsClockwise,
  ArrowSquareOut,
  BookOpen,
  Brain,
  ClockCounterClockwise,
  Key,
  SealCheck,
  SquaresFour,
  TreeStructure,
} from "@phosphor-icons/react";
import LanyardWithControls from "@/components/lanyard-with-controls";

const DOCS_URL = "https://aryaman.mintlify.app/benchmark/benchmark-card";

type FeatureFigure =
  | "memory"
  | "authority"
  | "replay"
  | "longcon"
  | "proof"
  | "audit"
  | "generation";

function FeatureCardBackdrop() {
  return (
    <div
      className="pointer-events-none absolute inset-0 z-0 overflow-hidden rounded-2xl"
      aria-hidden
    >
      <div
        className="landing-wind-dots absolute inset-0 opacity-[0.45]"
        style={{
          backgroundImage:
            "radial-gradient(circle at center, rgba(255,255,255,0.11) 0.55px, transparent 0.6px)",
          backgroundSize: "11px 11px",
        }}
      />
      <div className="absolute bottom-3 left-3 grid grid-cols-2 gap-1 opacity-[0.35]">
        {Array.from({ length: 8 }, (_, i) => (
          <span key={i} className="size-1 bg-white" />
        ))}
      </div>
    </div>
  );
}

const NOVELTY_CARDS: {
  eyebrow: string;
  title: string;
  copy: string;
  className: string;
  tags: string[];
  figure: FeatureFigure;
  icon: typeof Brain;
}[] = [
  {
    eyebrow: "01 / Memory",
    title: "Persistent Institutional Memory",
    copy: "Tracks vendor trust, fraud losses, authority pressure, and institutional outcomes across episodes.",
    className: "md:col-span-5",
    tags: ["vendor_trust", "loss_ledger", "authority_pressure"],
    figure: "memory",
    icon: Brain,
  },
  {
    eyebrow: "02 / Authority",
    title: "Calibration-Gated Authority",
    copy: "Agents earn or lose operational authority based on calibration quality and catastrophic mistakes.",
    className: "md:col-span-7",
    tags: ["calibration", "clearance_band", "catastrophic_events"],
    figure: "authority",
    icon: Key,
  },
  {
    eyebrow: "03 / Replay",
    title: "Audit-Grade Reproducibility",
    copy: "Re-run episodes with frozen seeds and stable artifact hashes so scores and evidence traces line up every time.",
    className: "md:col-span-5",
    tags: ["frozen_seed", "artifact_hash", "trace_parity"],
    figure: "replay",
    icon: ArrowsClockwise,
  },
  {
    eyebrow: "04 / Long Con",
    title: "Sleeper-Vendor Vigilance",
    copy: "Tests whether agents catch vendors that behave normally first, then activate fraud later.",
    className: "md:col-span-3",
    tags: ["quiet_phase", "switch_event"],
    figure: "longcon",
    icon: ClockCounterClockwise,
  },
  {
    eyebrow: "05 / Proof",
    title: "Decision Certificates",
    copy: "Every decision can carry auditable evidence, policy, intervention, and counterfactual nodes.",
    className: "md:col-span-4",
    tags: ["evidence", "policy", "counterfactuals"],
    figure: "proof",
    icon: SealCheck,
  },
  {
    eyebrow: "06 / Audit",
    title: "Falsifier + TrustGraph",
    copy: "After decisions, a deterministic adversary attacks unsupported claims and unsafe PAY actions.",
    className: "md:col-span-7",
    tags: ["claim_graph", "unsafe_pay_probe"],
    figure: "audit",
    icon: TreeStructure,
  },
  {
    eyebrow: "07 / Generation",
    title: "FraudGen Ecosystems",
    copy: "Generates novel fraud worlds with solvability manifests, tool paths, artifacts, and validation metadata.",
    className: "md:col-span-5",
    tags: ["manifest", "tool_path", "validation_meta"],
    figure: "generation",
    icon: SquaresFour,
  },
];

function FeatureCardFigure({ variant }: { variant: FeatureFigure }) {
  switch (variant) {
    case "memory":
      return (
        <div className="mt-5 border-t border-white/10 pt-4">
          <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-500">
            Cross-episode state
          </p>
          <div className="flex gap-2">
            {["T−2", "T−1", "T"].map((label, i) => (
              <div key={label} className="flex min-w-0 flex-1 flex-col gap-2">
                <span className="font-mono text-[10px] text-zinc-500">{label}</span>
                <div
                  className={`rounded border p-2 ${i === 2 ? "border-white/30 bg-zinc-950" : "border-white/15 bg-black"}`}
                >
                  <div className="space-y-1.5">
                    <div className="h-px w-full bg-white/25" />
                    <div className="h-px w-4/5 bg-white/40" />
                    <div className="h-px w-3/5 bg-white/15" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    case "authority":
      return (
        <div className="mt-5 border-t border-white/10 pt-4">
          <div className="flex items-center justify-between font-mono text-[10px] text-zinc-500">
            <span>Calibration signal</span>
            <span>Authority band</span>
          </div>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-white/10">
            <div className="h-full w-[68%] rounded-full bg-white" />
          </div>
          <div className="mt-2 flex justify-between font-mono text-[10px] text-zinc-400">
            <span>↓ after mistakes</span>
            <span>↑ when stable</span>
          </div>
        </div>
      );
    case "replay":
      return (
        <div className="mt-5 border-t border-white/10 pt-4">
          <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-500">
            Same inputs → same trace
          </p>
          <div className="flex items-stretch gap-2 font-mono text-[10px]">
            <div className="flex min-w-0 flex-1 flex-col gap-1.5 rounded border border-white/15 bg-zinc-950 p-2">
              <span className="text-zinc-500">run_a.digest</span>
              <span className="truncate text-zinc-300">sha256···c41e</span>
            </div>
            <div className="flex shrink-0 items-center text-zinc-600">≡</div>
            <div className="flex min-w-0 flex-1 flex-col gap-1.5 rounded border border-white/15 bg-zinc-950 p-2">
              <span className="text-zinc-500">run_b.digest</span>
              <span className="truncate text-zinc-300">sha256···c41e</span>
            </div>
          </div>
          <p className="mt-2 text-[10px] text-zinc-500">episode_seed locked · tool RNG pinned</p>
        </div>
      );
    case "longcon":
      return (
        <div className="mt-5 border-t border-white/10 pt-4">
          <div className="flex items-stretch gap-1 sm:gap-2">
            <div className="min-w-0 flex-1 rounded-lg border border-white/20 p-2.5">
              <p className="font-mono text-[10px] uppercase tracking-wider text-zinc-500">Phase A</p>
              <p className="mt-1 text-xs leading-snug text-zinc-400">Benign vendor surface</p>
            </div>
            <div className="flex shrink-0 items-center font-mono text-zinc-600">→</div>
            <div className="min-w-0 flex-1 rounded-lg border border-dashed border-white/35 p-2.5">
              <p className="font-mono text-[10px] uppercase tracking-wider text-white">Phase B</p>
              <p className="mt-1 text-xs leading-snug text-zinc-400">Fraud activates</p>
            </div>
          </div>
        </div>
      );
    case "proof":
      return (
        <div className="mt-5 border-t border-white/10 pt-4">
          <div className="rounded-lg border border-white/25 bg-zinc-950 p-3 font-mono text-[10px] leading-relaxed">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="space-y-1 text-zinc-400">
                <div className="text-white">DECISION_CERT</div>
                <div>evidence_nodes · 14</div>
                <div>policy_refs · 3</div>
              </div>
              <div className="shrink-0 rounded border border-white/20 px-2 py-1 text-zinc-500">sha256···a3f9</div>
            </div>
          </div>
        </div>
      );
    case "audit":
      return (
        <div className="mt-5 border-t border-white/10 pt-4">
          <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-500">
            Deterministic challenge
          </p>
          <div className="flex flex-wrap items-center justify-center gap-2 py-1">
            <span className="rounded border border-white/25 px-2 py-1 font-mono text-[10px]">claim</span>
            <span className="text-zinc-600">—</span>
            <span className="rounded border border-dashed border-white/35 px-2 py-1 font-mono text-[10px] text-zinc-400">
              falsifier
            </span>
            <span className="text-zinc-600">—</span>
            <span className="rounded border border-white/25 px-2 py-1 font-mono text-[10px]">PAY gate</span>
          </div>
        </div>
      );
    case "generation":
      return (
        <div className="mt-5 border-t border-white/10 pt-4">
          <div className="space-y-2 font-mono text-[10px]">
            <div className="flex justify-between gap-2 border-b border-white/10 pb-2 text-zinc-500">
              <span>manifest.solvable</span>
              <span className="text-zinc-300">true</span>
            </div>
            <div className="flex justify-between gap-2 border-b border-white/10 pb-2 text-zinc-500">
              <span>tool_path.len</span>
              <span className="text-white">7</span>
            </div>
            <div className="flex justify-between gap-2 text-zinc-500">
              <span>world_id</span>
              <span className="truncate text-zinc-400">fg-eco-192.ax</span>
            </div>
          </div>
        </div>
      );
    default:
      return null;
  }
}

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen overflow-hidden bg-transparent text-white">
      <header className="border-b border-white/10 bg-black/20 backdrop-blur-sm">
        <div className="mx-auto flex h-16 w-full max-w-[1600px] items-center justify-between px-6">
          <p className="font-mono text-lg tracking-tight text-zinc-100">LedgerShield.</p>
          <a
            href={DOCS_URL}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-md border border-white/15 bg-white/5 px-3 py-1.5 font-mono text-xs uppercase tracking-[0.2em] text-zinc-300 transition hover:bg-white/10"
          >
            <BookOpen size={14} />
            Benchmark card
            <ArrowSquareOut size={12} className="opacity-70" />
          </a>
        </div>
      </header>
      <main className="relative">
        <section className="relative min-h-[calc(100vh-4rem)] px-6 pt-20 lg:pt-24">
          <div className="relative mx-auto grid w-full max-w-[1600px] items-start gap-8 lg:grid-cols-2">
            <div className="landing-wind-hero max-w-2xl space-y-7 pt-8">
              <motion.p
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="inline-flex rounded-md border border-white/20 bg-black/35 px-3 py-1 font-mono text-xs uppercase tracking-[0.22em] text-zinc-300"
              >
                Meta Scalar Hackathon
              </motion.p>
              <motion.h1
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.08 }}
                className="text-balance text-6xl font-semibold leading-[0.95] md:text-8xl"
              >
                AI Agents That Catch Fraud
              </motion.h1>
              <motion.p
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.16 }}
                className="max-w-xl text-pretty rounded-md bg-black/20 p-1.5 text-2xl text-zinc-300"
              >
                LedgerShield is the benchmark for evaluating AI agents on enterprise accounts payable fraud
                detection. Test your agent against realistic invoice, vendor, and payment fraud scenarios.
              </motion.p>
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.24 }}
                className="flex flex-wrap items-center gap-3"
              >
                <button
                  onClick={() => router.push("/dashboard")}
                  className="inline-flex items-center gap-2 rounded-2xl bg-white px-6 py-3 text-base font-semibold text-black transition hover:bg-zinc-200"
                >
                  Enter Dashboard
                  <ArrowRight size={16} weight="bold" />
                </button>
                <button
                  onClick={() => router.push("/agent")}
                  className="rounded-2xl border border-white/20 bg-white/5 px-6 py-3 text-base font-medium transition hover:bg-white/10"
                >
                  Test Agent
                </button>
                <a
                  href={DOCS_URL}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 rounded-2xl border border-white/15 bg-transparent px-6 py-3 text-base font-medium text-zinc-200 transition hover:border-white/30 hover:bg-white/5"
                >
                  Read the docs
                  <ArrowSquareOut size={14} className="opacity-70" />
                </a>
              </motion.div>
            </div>

            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              transition={{ delay: 0.12, duration: 0.45 }}
              className="relative mx-auto w-full max-w-2xl pt-4 lg:pt-0"
            >
              <div className="landing-wind-lanyard h-full w-full">
                <LanyardWithControls
                  position={[0, 0, 16]}
                  containerClassName="lg:absolute lg:top-0 lg:right-0 lg:w-full relative w-full h-[76vh] lg:h-[80vh] bg-radial from-transparent to-transparent select-none"
                />
              </div>
            </motion.div>
          </div>
        </section>

        <section className="relative border-t border-white/15 px-6 pb-24 pt-16">
          <div className="mx-auto w-full max-w-[1600px]">
            <div className="landing-wind-hero mb-10 max-w-3xl">
              <p className="mb-3 font-mono text-xs uppercase tracking-[0.24em] text-zinc-400">
                Why LedgerShield is different
              </p>
              <h2 className="text-balance text-4xl font-semibold tracking-tight text-white md:text-6xl">
                Built to test trust, not just task accuracy.
              </h2>
            </div>

            <div className="grid auto-rows-[minmax(220px,auto)] grid-cols-1 gap-3 md:grid-cols-12 md:gap-4">
              {NOVELTY_CARDS.map((card, index) => {
                const Icon = card.icon;
                return (
                  <motion.article
                    key={card.title}
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    viewport={{ once: true, margin: "-80px" }}
                    transition={{ delay: index * 0.05, duration: 0.35 }}
                    className={`group relative flex overflow-hidden rounded-2xl border border-white/20 bg-black p-7 text-left transition-colors hover:border-white/40 ${card.className}`}
                  >
                    <FeatureCardBackdrop />
                    <div
                      className={`relative z-[1] flex min-h-0 w-full min-w-0 flex-1 flex-col ${
                        index % 2 === 0 ? "landing-wind-card" : "landing-wind-card-alt"
                      }`}
                      style={{ animationDelay: `${index * 0.32}s` }}
                    >
                      <Icon
                        className="pointer-events-none absolute right-5 top-14 z-[1] text-white/[0.09] transition-colors group-hover:text-white/[0.14]"
                        size={72}
                        weight="thin"
                        aria-hidden
                      />
                      <div className="relative z-[1] flex w-full min-w-0 flex-col">
                        <p className="font-mono text-xs uppercase tracking-[0.22em] text-zinc-400">
                          {card.eyebrow}
                        </p>
                        <div className="mt-4 min-w-0 pr-16">
                          <h3 className="max-w-xl text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                            {card.title}
                          </h3>
                          <p className="mt-3 max-w-xl text-base leading-relaxed text-zinc-300">
                            {card.copy}
                          </p>
                          <ul className="mt-4 flex flex-wrap gap-1.5">
                            {card.tags.map((tag) => (
                              <li
                                key={tag}
                                className="rounded border border-white/15 bg-zinc-950 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-zinc-400"
                              >
                                {tag}
                              </li>
                            ))}
                          </ul>
                        </div>
                        <FeatureCardFigure variant={card.figure} />
                      </div>
                    </div>
                  </motion.article>
                );
              })}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}