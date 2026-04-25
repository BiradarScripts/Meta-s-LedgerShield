"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { ArrowRight } from "@phosphor-icons/react";
import LanyardWithControls from "@/components/lanyard-with-controls";

const NOVELTY_CARDS = [
  {
    eyebrow: "01 / Memory",
    title: "Persistent Institutional Memory",
    copy: "Tracks vendor trust, fraud losses, authority pressure, and institutional outcomes across episodes.",
    className: "md:col-span-5 md:row-span-2",
    accent: "from-blue-500/14 to-white/[0.03]",
  },
  {
    eyebrow: "02 / Authority",
    title: "Calibration-Gated Authority",
    copy: "Agents earn or lose operational authority based on calibration quality and catastrophic mistakes.",
    className: "md:col-span-7",
    accent: "from-cyan-500/12 to-white/[0.03]",
  },
  {
    eyebrow: "03 / Long Con",
    title: "Sleeper-Vendor Vigilance",
    copy: "Tests whether agents catch vendors that behave normally first, then activate fraud later.",
    className: "md:col-span-3",
    accent: "from-zinc-400/10 to-white/[0.02]",
  },
  {
    eyebrow: "04 / Proof",
    title: "Decision Certificates",
    copy: "Every decision can carry auditable evidence, policy, intervention, and counterfactual nodes.",
    className: "md:col-span-4",
    accent: "from-blue-500/10 to-white/[0.02]",
  },
  {
    eyebrow: "05 / Audit",
    title: "Falsifier + TrustGraph",
    copy: "After decisions, a deterministic adversary attacks unsupported claims and unsafe PAY actions.",
    className: "md:col-span-7",
    accent: "from-white/[0.08] to-white/[0.02]",
  },
  {
    eyebrow: "06 / Generation",
    title: "FraudGen Ecosystems",
    copy: "Generates novel fraud worlds with solvability manifests, tool paths, artifacts, and validation metadata.",
    className: "md:col-span-5",
    accent: "from-cyan-500/10 to-white/[0.02]",
  },
];

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen overflow-hidden bg-transparent text-white">
      <header className="border-b border-white/10 bg-black/20 backdrop-blur-sm">
        <div className="mx-auto flex h-16 w-full max-w-[1600px] items-center justify-between px-6">
          <p className="font-mono text-lg tracking-tight text-zinc-100">LedgerShield.</p>
        </div>
      </header>
      <main className="relative">
        <section className="relative min-h-[calc(100vh-4rem)] px-6 pt-20 lg:pt-24">
          <div className="relative mx-auto grid w-full max-w-[1600px] items-start gap-8 lg:grid-cols-2">
            <div className="max-w-2xl space-y-7 pt-8">
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
              </motion.div>
            </div>

            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              transition={{ delay: 0.12, duration: 0.45 }}
              className="relative mx-auto w-full max-w-2xl pt-4 lg:pt-0"
            >
              <LanyardWithControls
                position={[0, 0, 16]}
                containerClassName="lg:absolute lg:top-0 lg:right-0 lg:w-full relative w-full h-[76vh] lg:h-[80vh] bg-radial from-transparent to-transparent select-none"
              />
            </motion.div>
          </div>
        </section>

        <section className="relative px-6 pb-24 pt-10">
          <div className="mx-auto w-full max-w-[1600px]">
            <div className="mb-8 max-w-3xl">
              <p className="mb-3 font-mono text-xs uppercase tracking-[0.24em] text-zinc-500">
                Why LedgerShield is different
              </p>
              <h2 className="text-balance text-4xl font-semibold tracking-tight text-white md:text-6xl">
                Built to test trust, not just task accuracy.
              </h2>
            </div>

            <div className="grid auto-rows-[210px] grid-cols-1 gap-4 md:grid-cols-12">
              {NOVELTY_CARDS.map((card, index) => (
                <motion.article
                  key={card.title}
                  initial={{ opacity: 0, y: 18 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-80px" }}
                  transition={{ delay: index * 0.05, duration: 0.35 }}
                  className={`group relative overflow-hidden rounded-[2rem] border border-white/10 bg-gradient-to-br ${card.accent} ${card.className} p-7 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-sm`}
                >
                  <div className="absolute right-5 top-5 h-20 w-20 rounded-full border border-white/10 bg-white/[0.03] transition-transform duration-500 group-hover:scale-125" />
                  <div className="absolute -bottom-14 -right-14 h-40 w-40 rounded-full bg-white/[0.04]" />
                  <div className="relative flex h-full flex-col justify-between">
                    <p className="font-mono text-xs uppercase tracking-[0.22em] text-zinc-500">
                      {card.eyebrow}
                    </p>
                    <div>
                      <h3 className="max-w-xl text-3xl font-semibold tracking-tight text-white">
                        {card.title}
                      </h3>
                      <p className="mt-3 max-w-xl text-base leading-relaxed text-zinc-400">
                        {card.copy}
                      </p>
                    </div>
                  </div>
                </motion.article>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}