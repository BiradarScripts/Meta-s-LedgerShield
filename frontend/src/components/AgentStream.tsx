"use client";

import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle,
  XCircle,
  Brain,
  Wrench,
  FileText,
  Warning,
  Gavel,
  Sparkle,
  CaretDown,
  CaretRight,
} from "@phosphor-icons/react";

export type StreamEvent =
  | { type: "status"; content: string }
  | { type: "observation"; observation: Record<string, unknown> }
  | { type: "thinking"; content: string }
  | { type: "text_delta"; content: string }
  | {
      type: "tool_use";
      id: string;
      name: string;
      input: Record<string, unknown>;
      confidence?: number;
    }
  | {
      type: "tool_result";
      id: string;
      name: string;
      output: Record<string, unknown>;
      reward?: number;
      done?: boolean;
    }
  | {
      type: "decision";
      decision: string;
      confidence: number;
      reason_codes: string[];
      policy_checks: Record<string, string>;
      notes?: string;
    }
  | {
      type: "result";
      final_score: number;
      reward: number;
      info: Record<string, unknown>;
      observation: Record<string, unknown>;
      trust_graph?: Record<string, unknown>;
    }
  | { type: "error"; error: string }
  | { type: "done" };

interface AgentStreamProps {
  events: StreamEvent[];
  isStreaming?: boolean;
  onResultRevealed?: (result: {
    final_score: number;
    reward: number;
    info: Record<string, unknown>;
  }) => void;
}

interface TimelineItem {
  id: string;
  kind:
    | "status"
    | "observation"
    | "thinking"
    | "tool_use"
    | "tool_result"
    | "text_delta"
    | "decision"
    | "result"
    | "error";
  title: string;
  status: "pending" | "done" | "error";
  toolName?: string;
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  text?: string;
  reward?: number;
  confidence?: number;
  decision?: {
    decision: string;
    confidence: number;
    reason_codes: string[];
    policy_checks: Record<string, string>;
    notes?: string;
  };
  result?: {
    final_score: number;
    reward: number;
    info: Record<string, unknown>;
  };
  error?: string;
  observation?: Record<string, unknown>;
}

function ShimmerText({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <motion.span
      className={`relative inline-block text-transparent bg-clip-text bg-gradient-to-r from-zinc-100 via-white to-zinc-100 ${className || ""}`}
      animate={{ backgroundPosition: ["200% center", "-200% center"] }}
      transition={{ duration: 2, ease: "linear", repeat: Infinity }}
      style={{ backgroundSize: "200% auto" }}
    >
      {children}
    </motion.span>
  );
}

function JsonBlock({ value, label }: { value: unknown; label?: string }) {
  const [open, setOpen] = useState(false);
  const text = JSON.stringify(value, null, 2);
  const preview = text.length > 100 ? text.slice(0, 100) + "…" : text;

  if (text === "{}" || text === "null") return null;

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 text-[10px] font-mono text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        {open ? <CaretDown size={10} /> : <CaretRight size={10} />}
        <span>{label || "data"}</span>
        {!open && <span className="ml-1 text-zinc-600">{preview}</span>}
      </button>
      {open && (
        <pre className="mt-1.5 text-[10px] font-mono text-zinc-300 bg-zinc-900/60 p-2 rounded border border-white/5 overflow-x-auto max-h-60">
          {text}
        </pre>
      )}
    </div>
  );
}

const decisionStyles: Record<string, string> = {
  PAY: "bg-emerald-500/15 border-emerald-500/30 text-emerald-300",
  HOLD: "bg-yellow-500/15 border-yellow-500/30 text-yellow-300",
  NEEDS_REVIEW: "bg-blue-500/15 border-blue-500/30 text-blue-300",
  ESCALATE_FRAUD: "bg-red-500/15 border-red-500/30 text-red-300",
};

function confidenceTone(value: number): string {
  if (value >= 0.85) return "text-emerald-300 bg-emerald-500/10 border-emerald-500/20";
  if (value >= 0.6) return "text-cyan-300 bg-cyan-500/10 border-cyan-500/20";
  if (value >= 0.4) return "text-amber-300 bg-amber-500/10 border-amber-500/20";
  return "text-red-300 bg-red-500/10 border-red-500/20";
}

function ConfidenceChip({ value }: { value: number }) {
  const safe = Math.min(1, Math.max(0, value));
  const tone = confidenceTone(safe);
  return (
    <span
      title={`Agent confidence in this tool call: ${(safe * 100).toFixed(0)}%`}
      className={`inline-flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 rounded border ${tone}`}
    >
      <span className="opacity-70">conf</span>
      <span>{safe.toFixed(2)}</span>
    </span>
  );
}

const REVEAL_DELAY_MS: Record<StreamEvent["type"], number> = {
  status: 380,
  observation: 720,
  thinking: 520,
  text_delta: 22,
  tool_use: 620,
  tool_result: 1100,
  decision: 900,
  result: 1100,
  error: 0,
  done: 0,
};

export function AgentStream({
  events,
  isStreaming = false,
  onResultRevealed,
}: AgentStreamProps) {
  const [lineTargetY, setLineTargetY] = useState(0);
  const [revealedCount, setRevealedCount] = useState(0);
  const itemRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollParentRef = useRef<HTMLElement | null>(null);
  const pinnedRef = useRef(true);
  const programmaticScrollRef = useRef(false);
  const resultFiredRef = useRef<string | null>(null);

  useEffect(() => {
    if (revealedCount > events.length) {
      const reset = setTimeout(() => setRevealedCount(events.length), 0);
      return () => clearTimeout(reset);
    }
    if (revealedCount >= events.length) return;

    const nextEvent = events[revealedCount];
    const delay = REVEAL_DELAY_MS[nextEvent.type] ?? 200;
    const t = setTimeout(() => {
      setRevealedCount((c) => Math.min(c + 1, events.length));
    }, delay);
    return () => clearTimeout(t);
  }, [events, revealedCount]);

  const visibleEvents = useMemo(
    () => events.slice(0, Math.min(revealedCount, events.length)),
    [events, revealedCount],
  );

  const { items, streamingText } = useMemo(() => {
    let nextItems: TimelineItem[] = [];
    let nextText = "";
    for (const event of visibleEvents) {
      nextItems = applyEvent(nextItems, event, (text) => {
        nextText += text;
      });
    }
    return { items: nextItems, streamingText: nextText };
  }, [visibleEvents]);

  const isCatchingUp = revealedCount < events.length;
  const showCursor = isStreaming || isCatchingUp;

  useEffect(() => {
    if (items.length > 0 && containerRef.current) {
      const lastItem = items[items.length - 1];
      const el = itemRefs.current.get(lastItem.id);
      if (el) {
        const containerRect = containerRef.current.getBoundingClientRect();
        const elRect = el.getBoundingClientRect();
        setLineTargetY(elRect.top - containerRect.top + elRect.height / 2);
      }
    }
  }, [items.length, items]);

  useEffect(() => {
    let node: HTMLElement | null = containerRef.current?.parentElement ?? null;
    while (node) {
      const style = getComputedStyle(node);
      if (/auto|scroll|overlay/.test(style.overflowY)) {
        scrollParentRef.current = node;
        break;
      }
      node = node.parentElement;
    }
    const scroller = scrollParentRef.current;
    if (!scroller) return;
    const onScroll = () => {
      if (programmaticScrollRef.current) {
        programmaticScrollRef.current = false;
        return;
      }
      const distance =
        scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight;
      pinnedRef.current = distance < 48;
    };
    scroller.addEventListener("scroll", onScroll, { passive: true });
    return () => scroller.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!pinnedRef.current) return;
    const scroller = scrollParentRef.current;
    if (!scroller) return;
    programmaticScrollRef.current = true;
    scroller.scrollTo({ top: scroller.scrollHeight, behavior: "smooth" });
  }, [items.length, streamingText]);

  useEffect(() => {
    const resultItem = items.find((it) => it.kind === "result");
    if (!resultItem) {
      resultFiredRef.current = null;
      return;
    }
    if (resultFiredRef.current === resultItem.id) return;
    resultFiredRef.current = resultItem.id;
    if (resultItem.result) {
      onResultRevealed?.(resultItem.result);
    }
  }, [items, onResultRevealed]);

  const setItemRef = useCallback(
    (id: string) => (el: HTMLDivElement | null) => {
      if (el) itemRefs.current.set(id, el);
    },
    [],
  );

  return (
    <div className="space-y-0" ref={containerRef}>
      <div className="relative">
        <motion.div
          className="absolute left-[11px] top-0 w-px border-l border-dashed border-zinc-600 origin-top"
          animate={{ height: lineTargetY, opacity: items.length > 0 ? 1 : 0 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        />

        <div className="space-y-0">
          {items.map((item) => (
            <motion.div
              key={item.id}
              ref={setItemRef(item.id)}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
              className="relative flex items-start gap-3 py-2"
            >
              <TimelineMarker item={item} />
              <div className="flex-1 min-w-0 pt-0.5">
                <TimelineBody item={item} />
              </div>
            </motion.div>
          ))}
        </div>

        <AnimatePresence>
          {streamingText && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="relative flex items-start gap-3 py-3"
            >
              <div className="relative z-10 flex-shrink-0 w-6 h-6 flex items-center justify-center">
                <FileText size={18} className="text-emerald-400" />
              </div>
              <div className="flex-1 pt-0.5">
                <pre className="text-sm text-zinc-100 font-sans whitespace-pre-wrap leading-relaxed">
                  {streamingText}
                  {showCursor && (
                    <motion.span
                      animate={{ opacity: [1, 0] }}
                      transition={{ duration: 0.8, repeat: Infinity }}
                      className="inline-block w-2 h-4 bg-emerald-400 ml-1 align-middle"
                    />
                  )}
                </pre>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {!showCursor && items.length === 0 && (
          <div className="text-center py-8 text-sm text-zinc-500">
            Waiting for agent to start...
          </div>
        )}
      </div>
    </div>
  );
}

function TimelineMarker({ item }: { item: TimelineItem }) {
  return (
    <div className="relative z-10 flex-shrink-0 w-6 h-6 flex items-center justify-center">
      <AnimatePresence mode="wait">
        {item.status === "pending" ? (
          <motion.div
            key="pending"
            initial={{ scale: 0 }}
            animate={{ scale: [0.6, 1, 0.6] }}
            transition={{ duration: 1.4, repeat: Infinity }}
            className="w-2 h-2 rounded-full bg-zinc-400"
          />
        ) : item.status === "error" ? (
          <motion.div
            key="error"
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ duration: 0.3, type: "spring" }}
          >
            <XCircle size={18} className="text-red-400" weight="fill" />
          </motion.div>
        ) : item.kind === "decision" ? (
          <motion.div
            key="decision"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.3, type: "spring" }}
          >
            <Gavel size={18} className="text-purple-400" weight="fill" />
          </motion.div>
        ) : item.kind === "result" ? (
          <motion.div
            key="result"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.3, type: "spring" }}
          >
            <Sparkle size={18} className="text-amber-300" weight="fill" />
          </motion.div>
        ) : (
          <motion.div
            key="done"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.25, type: "spring", stiffness: 500 }}
          >
            <CheckCircle
              size={18}
              className={
                item.kind === "tool_use" || item.kind === "tool_result"
                  ? "text-orange-400"
                  : "text-emerald-500"
              }
              weight="fill"
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function TimelineBody({ item }: { item: TimelineItem }) {
  const labelIcon = (() => {
    switch (item.kind) {
      case "tool_use":
      case "tool_result":
        return <Wrench size={12} className="text-orange-400" />;
      case "thinking":
        return <Brain size={12} className="text-zinc-400" />;
      case "error":
        return <Warning size={12} className="text-red-400" />;
      case "decision":
        return <Gavel size={12} className="text-purple-300" />;
      case "result":
        return <Sparkle size={12} className="text-amber-300" />;
      case "observation":
        return <FileText size={12} className="text-emerald-300" />;
      default:
        return <div className="w-1.5 h-1.5 rounded-full bg-zinc-500" />;
    }
  })();

  return (
    <div>
      <div className="flex items-center gap-2 flex-wrap">
        {labelIcon}
        {item.kind === "tool_use" || item.kind === "tool_result" ? (
          <ShimmerText className="text-sm text-zinc-100">
            {item.toolName || item.title}
          </ShimmerText>
        ) : (
          <span
            className={`text-sm ${
              item.kind === "error"
                ? "text-red-400"
                : item.kind === "decision"
                  ? "text-purple-200"
                  : item.kind === "result"
                    ? "text-amber-200"
                    : "text-zinc-200"
            }`}
          >
            {item.title}
          </span>
        )}
        {(item.kind === "tool_use" || item.kind === "tool_result") &&
          typeof item.confidence === "number" && (
            <ConfidenceChip value={item.confidence} />
          )}
        {typeof item.reward === "number" && item.reward !== 0 && (
          <span
            className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
              item.reward > 0
                ? "text-emerald-400 bg-emerald-500/10"
                : "text-red-400 bg-red-500/10"
            }`}
          >
            {item.reward > 0 ? "+" : ""}
            {item.reward.toFixed(2)}
          </span>
        )}
      </div>

      {item.kind === "tool_use" && item.input && (
        <JsonBlock label="input" value={item.input} />
      )}
      {item.kind === "tool_result" && item.output && (
        <JsonBlock label="output" value={item.output} />
      )}
      {item.kind === "observation" && item.observation && (
        <JsonBlock label="observation" value={summarizeObs(item.observation)} />
      )}

      {item.kind === "thinking" && item.text && (
        <p className="text-xs text-zinc-400 mt-1 italic leading-relaxed">{item.text}</p>
      )}

      {item.kind === "error" && item.error && (
        <p className="text-xs text-red-400 mt-1 leading-relaxed">{item.error}</p>
      )}

      {item.kind === "decision" && item.decision && (
        <div className="mt-2 space-y-2">
          <div
            className={`inline-flex items-center gap-2 px-3 py-1 rounded-md border text-xs font-semibold ${
              decisionStyles[item.decision.decision] ||
              "bg-zinc-500/15 border-zinc-500/30 text-zinc-300"
            }`}
          >
            {item.decision.decision}
            <span className="font-mono text-[10px] opacity-70">
              · conf {item.decision.confidence?.toFixed?.(2)}
            </span>
          </div>
          {item.decision.reason_codes?.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {item.decision.reason_codes.map((code) => (
                <span
                  key={code}
                  className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-zinc-300 border border-white/10"
                >
                  {code}
                </span>
              ))}
            </div>
          )}
          {item.decision.notes && (
            <p className="text-xs text-zinc-400 italic leading-relaxed">
              {item.decision.notes}
            </p>
          )}
          {item.decision.policy_checks &&
            Object.keys(item.decision.policy_checks).length > 0 && (
              <JsonBlock label="policy_checks" value={item.decision.policy_checks} />
            )}
        </div>
      )}

      {item.kind === "result" && item.result && (
        <div className="mt-2 space-y-1">
          <div className="text-xs text-zinc-400">
            Final score:{" "}
            <span className="font-mono text-amber-300">
              {item.result.final_score.toFixed(3)}
            </span>
            {" · "}
            Reward:{" "}
            <span className="font-mono">
              {item.result.reward.toFixed(3)}
            </span>
          </div>
          <JsonBlock label="info" value={item.result.info} />
        </div>
      )}
    </div>
  );
}

function summarizeObs(obs: Record<string, unknown>): Record<string, unknown> {
  const docs = Array.isArray(obs.visible_documents) ? obs.visible_documents : [];
  return {
    case_id: obs.case_id,
    task_type: obs.task_type,
    instruction: obs.instruction,
    visible_documents: docs.map((d) => {
      const doc = (d as Record<string, unknown>) || {};
      return { doc_id: doc.doc_id, doc_type: doc.doc_type };
    }),
    budget_remaining: obs.budget_remaining,
    budget_total: obs.budget_total,
    step_count: obs.step_count,
    max_steps: obs.max_steps,
    allowed_actions: obs.allowed_actions,
  };
}

function applyEvent(
  prev: TimelineItem[],
  event: StreamEvent,
  appendText: (text: string) => void,
): TimelineItem[] {
  const closePending = (items: TimelineItem[]): TimelineItem[] =>
    items.map((it) =>
      it.kind === "status" && it.status === "pending"
        ? { ...it, status: "done" as const }
        : it,
    );

  switch (event.type) {
    case "status": {
      const next = closePending(prev);
      return [
        ...next,
        {
          id: `status-${next.length}`,
          kind: "status",
          title: event.content,
          status: "pending",
        },
      ];
    }
    case "observation": {
      const next = closePending(prev);
      return [
        ...next,
        {
          id: `obs-${next.length}`,
          kind: "observation",
          title: `Observation · ${event.observation.case_id}`,
          status: "done",
          observation: event.observation,
        },
      ];
    }
    case "thinking": {
      const next = closePending(prev);
      return [
        ...next,
        {
          id: `think-${next.length}`,
          kind: "thinking",
          title: "Thinking",
          text: event.content,
          status: "done",
        },
      ];
    }
    case "text_delta": {
      appendText(event.content);
      return closePending(prev);
    }
    case "tool_use": {
      const next = closePending(prev);
      return [
        ...next,
        {
          id: event.id,
          kind: "tool_use",
          title: event.name,
          toolName: event.name,
          input: event.input,
          confidence: event.confidence,
          status: "pending",
        },
      ];
    }
    case "tool_result": {
      const idx = prev.findIndex((it) => it.id === event.id);
      if (idx === -1) {
        return [
          ...closePending(prev),
          {
            id: `${event.id}-result`,
            kind: "tool_result",
            title: event.name,
            toolName: event.name,
            output: event.output,
            reward: event.reward,
            status: "done",
          },
        ];
      }
      const next = [...prev];
      next[idx] = {
        ...next[idx],
        kind: "tool_result",
        output: event.output,
        reward: event.reward,
        status: "done",
      };
      return next;
    }
    case "decision": {
      const next = closePending(prev);
      return [
        ...next,
        {
          id: `decision-${next.length}`,
          kind: "decision",
          title: "Decision submitted",
          status: "done",
          decision: {
            decision: event.decision,
            confidence: event.confidence,
            reason_codes: event.reason_codes,
            policy_checks: event.policy_checks,
            notes: event.notes,
          },
        },
      ];
    }
    case "result": {
      const next = closePending(prev);
      return [
        ...next,
        {
          id: `result-${next.length}`,
          kind: "result",
          title: "Episode complete",
          status: "done",
          result: {
            final_score: event.final_score,
            reward: event.reward,
            info: event.info,
          },
        },
      ];
    }
    case "error": {
      const next = closePending(prev);
      return [
        ...next,
        {
          id: `error-${next.length}`,
          kind: "error",
          title: "Error",
          error: event.error,
          status: "error",
        },
      ];
    }
    case "done":
      return closePending(prev);
    default:
      return prev;
  }
}

export default AgentStream;
