"use client";

import {
  Pulse,
  Gauge,
  Coins,
  WarningCircle,
  Calculator,
  ChartLine,
} from "@phosphor-icons/react";

import type { StepMath } from "@/lib/agent/diagnostics";

function asRecord(v: unknown): Record<string, unknown> | null {
  return v && typeof v === "object" && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : null;
}

function asString(v: unknown): string {
  return typeof v === "string" ? v : "";
}

function asNumber(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

const COMPONENT_PRIORITY = [
  "voi_reward",
  "information_value",
  "cost_penalty",
  "failure_penalty",
  "potential_delta",
  "milestone_bonus",
  "reward_machine_bonus",
];

function sortComponentEntries(entries: [string, number][]): [string, number][] {
  const rank = (k: string) => {
    const i = COMPONENT_PRIORITY.indexOf(k);
    return i === -1 ? 999 : i;
  };
  return [...entries].sort((a, b) => rank(a[0]) - rank(b[0]) || a[0].localeCompare(b[0]));
}

export function EnvironmentPanel({
  observation,
  cumulativeReward,
  stepReward,
  stepMath,
  isRunning,
}: {
  observation: Record<string, unknown> | null;
  cumulativeReward: number;
  stepReward: number | null;
  stepMath: StepMath | null;
  isRunning: boolean;
}) {
  if (!observation) {
    return (
      <div className="rounded-xl border border-white/10 bg-black/40 p-4 text-xs text-zinc-500">
        <p className="font-mono uppercase tracking-[0.2em] text-[10px] text-zinc-600 mb-2">
          Environment
        </p>
        <p>Start a run to stream live state from LedgerShield.</p>
      </div>
    );
  }

  const caseId = asString(observation.case_id);
  const taskType = asString(observation.task_type);
  const instruction = asString(observation.instruction);
  const step = asNumber(observation.step_count) ?? 0;
  const maxSteps = asNumber(observation.max_steps) ?? 0;
  const budgetRem = asNumber(observation.budget_remaining);
  const budgetTot = asNumber(observation.budget_total);
  const readiness = asNumber(observation.decision_readiness);
  const meta = asRecord(observation.case_metadata);
  const trackMode = meta ? asString(meta.track_mode) : "";
  const risk = asRecord(observation.risk_snapshot);
  const signals = Array.isArray(risk?.observed_risk_signals)
    ? (risk!.observed_risk_signals as unknown[])
    : [];
  const rankings = observation.tool_rankings;
  const inv = asRecord(observation.investigation_status);
  const docs = Array.isArray(observation.visible_documents)
    ? observation.visible_documents
    : [];
  const lastTool = asRecord(observation.last_tool_result);
  const lastToolName = lastTool ? asString(lastTool.tool_name) : "";
  const sprt = asRecord(observation.sprt_state);
  const posteriors = sprt?.posterior_probabilities;
  const posteriorEntries =
    posteriors && typeof posteriors === "object"
      ? Object.entries(posteriors as Record<string, unknown>).filter(
          ([, v]) => typeof v === "number",
        )
      : [];
  const sprtRecommend = sprt ? asString(sprt.recommended_decision) : "";
  const sprtStop = sprt ? Boolean(sprt.optimal_stopping_reached) : false;
  const rmState = asRecord(observation.reward_machine);
  const rmProgress = rmState ? asNumber(rmState.progress_fraction) : null;
  const rmStateId = rmState ? asNumber(rmState.state_id) : null;

  const rankingEntries =
    rankings && typeof rankings === "object" && !Array.isArray(rankings)
      ? Object.entries(rankings as Record<string, unknown>).filter(
          ([, v]) => typeof v === "number",
        )
      : [];

  return (
    <div className="rounded-xl border border-white/10 bg-black/40 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-white/[0.02]">
        <div className="flex items-center gap-2">
          <Pulse
            size={16}
            className={isRunning ? "text-emerald-400 animate-pulse" : "text-zinc-500"}
            weight="fill"
          />
          <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-zinc-400">
            Environment
          </span>
        </div>
        {trackMode && (
          <span className="text-[9px] font-mono px-2 py-0.5 rounded border border-white/10 text-zinc-500">
            {trackMode}
          </span>
        )}
      </div>

      <div className="p-4 space-y-4 max-h-[min(72vh,640px)] overflow-y-auto text-xs">
        <div>
          <p className="text-[10px] font-mono text-zinc-500 mb-1">Case</p>
          <p className="font-mono text-emerald-300/90">{caseId || "—"}</p>
          <p className="text-zinc-400 mt-0.5">{taskType}</p>
          {instruction && (
            <p className="text-zinc-500 mt-2 leading-snug line-clamp-3">{instruction}</p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-2.5">
            <div className="flex items-center gap-1 text-[10px] text-zinc-500 mb-1">
              <Gauge size={12} /> Step
            </div>
            <p className="font-mono text-zinc-200">
              {step} / {maxSteps}
            </p>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-2.5">
            <div className="flex items-center gap-1 text-[10px] text-zinc-500 mb-1">
              <Coins size={12} /> Budget
            </div>
            <p className="font-mono text-zinc-200">
              {budgetRem != null && budgetTot != null
                ? `${budgetRem.toFixed(2)} / ${budgetTot.toFixed(2)}`
                : "—"}
            </p>
          </div>
        </div>

        <div className="rounded-lg border border-white/10 bg-white/[0.03] p-2.5">
          <p className="text-[10px] text-zinc-500 mb-1">Live reward (env)</p>
          <div className="flex items-baseline gap-2 flex-wrap">
            <span className="font-mono text-amber-300 text-sm">
              Σ {cumulativeReward.toFixed(3)}
            </span>
            {stepReward != null && (
              <span className="text-[10px] font-mono text-zinc-500">
                last Δ {stepReward >= 0 ? "+" : ""}
                {stepReward.toFixed(3)}
              </span>
            )}
          </div>
        </div>

        {(stepMath?.reward_model || stepMath?.rl_plane) && (
          <div className="rounded-lg border border-cyan-500/20 bg-cyan-500/[0.06] p-2.5 space-y-2">
            <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-[0.15em] text-cyan-400/90">
              <Calculator size={14} />
              VoI &amp; step math
            </div>

            {stepMath.reward_model && (
              <>
                <div className="flex justify-between gap-2 text-[10px]">
                  <span className="text-zinc-500">Reward model value</span>
                  <span className="font-mono text-cyan-200">
                    {stepMath.reward_model.value.toFixed(4)}
                    {stepMath.reward_model.terminal ? (
                      <span className="text-zinc-500 ml-1">· terminal</span>
                    ) : null}
                  </span>
                </div>
                {sortComponentEntries(
                  Object.entries(stepMath.reward_model.components),
                ).length > 0 && (
                  <div className="space-y-1 max-h-36 overflow-y-auto">
                    {sortComponentEntries(
                      Object.entries(stepMath.reward_model.components),
                    ).map(([k, v]) => (
                      <div
                        key={k}
                        className="flex justify-between gap-2 text-[10px] font-mono border border-white/5 rounded px-2 py-1 bg-black/20"
                      >
                        <span
                          className={
                            k === "voi_reward" || k === "information_value"
                              ? "text-cyan-300 truncate"
                              : "text-zinc-400 truncate"
                          }
                        >
                          {k}
                        </span>
                        <span
                          className={
                            k === "voi_reward"
                              ? "text-emerald-300 shrink-0"
                              : "text-zinc-200 shrink-0"
                          }
                        >
                          {v.toFixed(4)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                {Object.keys(stepMath.reward_model.metadata).length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(stepMath.reward_model.metadata).map(
                      ([k, v]) => (
                        <span
                          key={k}
                          className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-zinc-900/80 border border-white/10 text-zinc-400 max-w-full truncate"
                          title={`${k}: ${String(v)}`}
                        >
                          {k}: {String(v)}
                        </span>
                      ),
                    )}
                  </div>
                )}
              </>
            )}

            {stepMath.rl_plane && stepMath.rl_plane.state_dim > 0 && (
              <div className="pt-1 border-t border-white/10 space-y-1.5">
                <div className="flex items-center gap-1 text-[10px] text-zinc-500">
                  <ChartLine size={12} /> RL state vector
                </div>
                <p className="text-[10px] font-mono text-zinc-400">
                  dim {stepMath.rl_plane.state_dim}
                  {stepMath.rl_plane.best_tool_voi != null && (
                    <span className="text-cyan-300 ml-2">
                      best_tool_voi (vec):{" "}
                      {stepMath.rl_plane.best_tool_voi.toFixed(4)}
                    </span>
                  )}
                </p>
                {(stepMath.rl_plane.watchdog != null ||
                  stepMath.rl_plane.calibration != null) && (
                  <div className="flex flex-wrap gap-2 text-[9px] font-mono text-zinc-500">
                    {stepMath.rl_plane.watchdog != null && (
                      <span>
                        watchdog:{" "}
                        <span className="text-zinc-300">
                          {stepMath.rl_plane.watchdog.toFixed(4)}
                        </span>
                      </span>
                    )}
                    {stepMath.rl_plane.calibration != null && (
                      <span>
                        calibration:{" "}
                        <span className="text-zinc-300">
                          {stepMath.rl_plane.calibration.toFixed(4)}
                        </span>
                      </span>
                    )}
                  </div>
                )}
                {stepMath.rl_plane.preview.length > 0 && (
                  <p className="text-[9px] font-mono text-zinc-600 break-all leading-relaxed">
                    head: [{stepMath.rl_plane.preview.map((x) => x.toFixed(3)).join(", ")}]
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {posteriorEntries.length > 0 && (
          <div className="rounded-lg border border-violet-500/20 bg-violet-500/[0.06] p-2.5">
            <p className="text-[10px] font-mono text-violet-300/90 mb-2 uppercase tracking-[0.15em]">
              SPRT posteriors
            </p>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {posteriorEntries.map(([k, v]) => (
                <div
                  key={k}
                  className="flex justify-between gap-2 text-[10px] font-mono"
                >
                  <span className="text-zinc-400 truncate">{k}</span>
                  <span className="text-violet-200 shrink-0">
                    {((v as number) * 100).toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
            {(sprtRecommend || sprtStop) && (
              <p className="text-[9px] text-zinc-500 mt-2 font-mono">
                {sprtRecommend && <>rec: {sprtRecommend} · </>}
                {sprtStop ? "stop reached" : "stop open"}
              </p>
            )}
          </div>
        )}

        {(rmProgress != null || rmStateId != null) && (
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/[0.06] p-2.5">
            <p className="text-[10px] font-mono text-amber-200/90 mb-1 uppercase tracking-[0.15em]">
              Reward machine
            </p>
            {rmProgress != null && (
              <div className="h-1.5 rounded-full bg-white/10 overflow-hidden mb-1">
                <div
                  className="h-full rounded-full bg-amber-500/70"
                  style={{
                    width: `${Math.min(100, rmProgress * 100)}%`,
                  }}
                />
              </div>
            )}
            <p className="text-[10px] font-mono text-zinc-400">
              progress {(rmProgress != null ? rmProgress * 100 : 0).toFixed(1)}%
              {rmStateId != null && (
                <span className="text-zinc-500"> · state {rmStateId}</span>
              )}
            </p>
          </div>
        )}

        {readiness != null && (
          <div>
            <p className="text-[10px] text-zinc-500 mb-1">Decision readiness</p>
            <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
              <div
                className="h-full rounded-full bg-cyan-500/80 transition-all duration-300"
                style={{ width: `${Math.min(100, readiness * 100)}%` }}
              />
            </div>
            <p className="text-[10px] font-mono text-zinc-500 mt-1">
              {(readiness * 100).toFixed(1)}%
            </p>
          </div>
        )}

        <div>
          <p className="text-[10px] text-zinc-500 mb-1 flex items-center gap-1">
            <WarningCircle size={12} /> Risk signals ({signals.length})
          </p>
          {signals.length === 0 ? (
            <p className="text-zinc-600 italic">None observed yet</p>
          ) : (
            <ul className="space-y-1 max-h-24 overflow-y-auto">
              {signals.slice(0, 12).map((s, i) => (
                <li
                  key={i}
                  className="text-[10px] font-mono text-amber-200/80 bg-amber-500/10 border border-amber-500/20 rounded px-2 py-1"
                >
                  {String(s)}
                </li>
              ))}
            </ul>
          )}
        </div>

        {rankingEntries.length > 0 ? (
          <div>
            <p className="text-[10px] text-zinc-500 mb-1">Tool rankings (instrumented)</p>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {rankingEntries
                .sort((a, b) => Number(b[1]) - Number(a[1]))
                .slice(0, 8)
                .map(([k, v]) => (
                  <div
                    key={k}
                    className="flex justify-between gap-2 text-[10px] font-mono border border-white/5 rounded px-2 py-1"
                  >
                    <span className="text-zinc-400 truncate">{k}</span>
                    <span className="text-cyan-300 shrink-0">
                      {Number(v).toFixed(3)}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        ) : (
          trackMode === "blind" && (
            <p className="text-[10px] text-zinc-600 italic">
              Tool rankings / SPRT are hidden in blind benchmark mode.
            </p>
          )
        )}

        {inv && Object.keys(inv).length > 0 && (
          <div>
            <p className="text-[10px] text-zinc-500 mb-1">Investigation</p>
            <pre className="text-[9px] font-mono text-zinc-500 bg-zinc-950/80 rounded p-2 max-h-28 overflow-auto border border-white/5">
              {JSON.stringify(inv, null, 2)}
            </pre>
          </div>
        )}

        <div>
          <p className="text-[10px] text-zinc-500 mb-1">
            Visible documents ({docs.length})
          </p>
          <ul className="space-y-1 max-h-28 overflow-y-auto">
            {docs.slice(0, 8).map((d, i) => {
              const doc = asRecord(d) || {};
              return (
                <li
                  key={i}
                  className="text-[10px] font-mono text-zinc-400 truncate border border-white/5 rounded px-2 py-0.5"
                >
                  {asString(doc.doc_id)}{" "}
                  <span className="text-zinc-600">
                    ({asString(doc.doc_type)})
                  </span>
                </li>
              );
            })}
          </ul>
        </div>

        {lastToolName && (
          <div className="text-[10px] text-zinc-500 border-t border-white/10 pt-3">
            Last tool:{" "}
            <span className="font-mono text-zinc-300">{lastToolName}</span>
          </div>
        )}
      </div>
    </div>
  );
}
