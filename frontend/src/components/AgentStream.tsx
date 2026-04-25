"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle, XCircle, Brain, Wrench, FileText, Warning } from "@phosphor-icons/react";

export type StreamEvent = {
  type: "tool_use" | "tool_result" | "text_delta" | "thinking" | "error" | "status";
  id?: string;
  name?: string;
  input?: Record<string, unknown>;
  content?: string;
  error?: string;
};

interface AgentStreamProps {
  events?: StreamEvent[];
  onEvent?: (event: StreamEvent) => void;
  isDemo?: boolean;
}

interface TimelineItem {
  id: string;
  type: StreamEvent["type"];
  title: string;
  subtitle?: string;
  input?: Record<string, unknown>;
  status: "pending" | "done" | "error";
  isCheckpoint?: boolean;
}

function ShimmerText({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <motion.span
      className={`relative inline-block text-transparent bg-clip-text bg-gradient-to-r from-zinc-100 via-white to-zinc-100 ${className}`}
      animate={{
        backgroundPosition: ["200% center", "-200% center"],
      }}
      transition={{
        duration: 2,
        ease: "linear",
        repeat: Infinity,
      }}
      style={{
        backgroundSize: "200% auto",
      }}
    >
      {children}
    </motion.span>
  );
}

export function AgentStream({ events = [], onEvent, isDemo = false }: AgentStreamProps) {
  const [items, setItems] = useState<TimelineItem[]>([]);
  const [streamingText, setStreamingText] = useState("");
  const [lineTargetY, setLineTargetY] = useState(0);
  const hasRunDemo = useRef(false);
  const itemRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isDemo && !hasRunDemo.current) {
      hasRunDemo.current = true;
      runDemo();
    }
  }, [isDemo]);

  useEffect(() => {
    for (const event of events) {
      handleEvent(event);
    }
  }, [events]);

  useEffect(() => {
    if (items.length > 0 && containerRef.current) {
      const lastItem = items[items.length - 1];
      const el = itemRefs.current.get(lastItem.id);
      if (el) {
        const containerRect = containerRef.current.getBoundingClientRect();
        const elRect = el.getBoundingClientRect();
        const relativeY = elRect.top - containerRect.top + elRect.height / 2;
        setLineTargetY(relativeY);
      }
    }
  }, [items.length]);

  const handleEvent = useCallback((event: StreamEvent) => {
    onEvent?.(event);

    switch (event.type) {
      case "tool_use":
        setItems(prev => {
          const updated = prev.map(item =>
            item.type === "status" && item.status === "pending"
              ? { ...item, status: "done" as const }
              : item
          );
          return [...updated, {
            id: event.id || String(Date.now()),
            type: "tool_use",
            title: event.name || "tool",
            subtitle: "Calling...",
            input: event.input,
            status: "pending",
          }];
        });
        break;

      case "tool_result":
        setItems(prev => prev.map(item => {
          if (item.id === event.id) {
            return { ...item, status: "done" as const, subtitle: "Done", isCheckpoint: true };
          }
          if (item.type === "status" && item.status === "pending") {
            return { ...item, status: "done" as const };
          }
          return item;
        }));
        break;

      case "text_delta":
        setItems(prev => prev.map(item =>
          item.type === "status" && item.status === "pending"
            ? { ...item, status: "done" as const }
            : item
        ));
        setStreamingText(prev => prev + (event.content || ""));
        break;

      case "thinking":
        setItems(prev => {
          const updated = prev.map(item =>
            item.type === "status" && item.status === "pending"
              ? { ...item, status: "done" as const }
              : item
          );
          return [...updated, {
            id: `think-${Date.now()}`,
            type: "thinking",
            title: "Thinking",
            subtitle: event.content,
            status: "done",
          }];
        });
        break;

      case "error":
        if (event.id) {
          setItems(prev => prev.map(item =>
            item.id === event.id
              ? { ...item, status: "error" as const, subtitle: event.error || "Failed" }
              : item
          ));
        }
        break;

      case "status":
        setItems(prev => {
          const updated = prev.map(item =>
            item.type === "status" && item.status === "pending"
              ? { ...item, status: "done" as const }
              : item
          );
          return [...updated, {
            id: `status-${Date.now()}`,
            type: "status",
            title: event.content || "...",
            status: "pending",
          }];
        });
        break;
    }
  }, [onEvent]);

  const runDemo = () => {
    const demoEvents: { delay: number; event: StreamEvent }[] = [
      { delay: 800, event: { type: "status", content: "Initializing agent..." } },
      { delay: 1500, event: { type: "tool_use", id: "1", name: "reset", input: { case_id: "CASE-A-001" } } },
      { delay: 1200, event: { type: "tool_result", id: "1", content: '{"case_id":"CASE-A-001","budget":10}' } },
      { delay: 800, event: { type: "thinking", content: "Analyzing case type and required verification steps..." } },
      { delay: 1000, event: { type: "tool_use", id: "2", name: "lookup_vendor", input: { vendor_key: "northwind-industrial" } } },
      { delay: 1200, event: { type: "tool_result", id: "2", content: '{"vendor_name":"Northwind Industrial","bank":"IN55NW000111222"}' } },
      { delay: 600, event: { type: "tool_use", id: "3", name: "ocr", input: { doc_id: "INV-A-001" } } },
      { delay: 1500, event: { type: "tool_result", id: "3", content: '{"amount":2478.00,"date":"2026-01-15"}' } },
      { delay: 800, event: { type: "status", content: "Evaluating fraud signals..." } },
      { delay: 1000, event: { type: "text_delta", content: "Decision: PAY\nConfidence: 0.95\nAll verification checks passed successfully." } },
    ];

    let accumulatedDelay = 0;
    demoEvents.forEach(({ delay, event }) => {
      accumulatedDelay += delay;
      setTimeout(() => handleEvent(event), accumulatedDelay);
    });
  };

  const setItemRef = (id: string) => (el: HTMLDivElement | null) => {
    if (el) itemRefs.current.set(id, el);
  };

  return (
    <div className="space-y-0" ref={containerRef}>
      <div className="relative">
        <motion.div
          className="absolute left-[11px] top-0 w-px border-l border-dashed border-zinc-600 origin-top"
          animate={{ 
            height: lineTargetY,
            opacity: items.length > 0 ? 1 : 0
          }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />

        <div className="space-y-0">
          {items.map((item, index) => (
            <motion.div
              key={item.id}
              ref={setItemRef(item.id)}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, ease: "easeOut", delay: 0.05 }}
              className="relative flex items-start gap-3 py-2"
            >
              <div className="relative z-10 flex-shrink-0 w-6 h-6 flex items-center justify-center">
                <AnimatePresence mode="wait">
                  {item.status === "pending" ? (
                    <motion.div
                      key="pending"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      exit={{ scale: 0 }}
                      transition={{ duration: 0.2 }}
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
                  ) : (
                    <motion.div
                      key="done"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ duration: 0.25, type: "spring", stiffness: 500 }}
                    >
                      <CheckCircle 
                        size={18} 
                        className={item.type === "tool_use" ? "text-orange-400" : "text-emerald-500"} 
                        weight="fill" 
                      />
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <div className="flex-1 min-w-0 pt-0.5">
                <div className="flex items-center gap-2">
                  {item.type === "tool_use" && <Wrench size={12} className="text-zinc-500" />}
                  {item.type === "thinking" && <Brain size={12} className="text-zinc-500" />}
                  {item.type === "error" && <Warning size={12} className="text-red-400" />}
                  {item.type === "status" && <div className="w-1.5 h-1.5 rounded-full bg-zinc-500" />}

                  {item.isCheckpoint && item.status === "done" ? (
                    <ShimmerText className="text-sm text-zinc-100">
                      {item.title}
                    </ShimmerText>
                  ) : (
                    <span className={`text-sm ${item.type === "error" ? "text-red-400" : "text-zinc-300"}`}>
                      {item.title}
                    </span>
                  )}

                  {item.status === "pending" && item.type !== "status" && (
                    <motion.span
                      animate={{ opacity: [0.3, 0.8, 0.3] }}
                      transition={{ duration: 2, repeat: Infinity }}
                      className="text-[10px] text-zinc-500"
                    >
                      {item.subtitle}
                    </motion.span>
                  )}
                </div>

                {item.subtitle && item.status !== "pending" && item.type !== "tool_use" && (
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.4, delay: 0.1 }}
                    className="text-xs text-zinc-500 mt-1 italic leading-relaxed"
                  >
                    {item.subtitle}
                  </motion.p>
                )}

                {item.input && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    transition={{ duration: 0.3, delay: 0.2 }}
                  >
                    <pre className="mt-1.5 text-[10px] font-mono text-zinc-600 bg-zinc-900/50 p-1.5 rounded overflow-x-auto">
                      {JSON.stringify(item.input, null, 1)}
                    </pre>
                  </motion.div>
                )}
              </div>
            </motion.div>
          ))}
        </div>

        <AnimatePresence>
          {streamingText && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="relative flex items-start gap-3 py-3"
            >
              <div className="relative z-10 flex-shrink-0 w-6 h-6 flex items-center justify-center">
                <FileText size={18} className="text-emerald-500" />
              </div>
              <div className="flex-1 pt-0.5">
                <pre className="text-sm text-zinc-100 font-mono whitespace-pre-wrap leading-relaxed">
                  {streamingText}
                  <motion.span
                    animate={{ opacity: [1, 0] }}
                    transition={{ duration: 0.8, repeat: Infinity }}
                    className="inline-block w-2 h-4 bg-emerald-500 ml-1 align-middle"
                  />
                </pre>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default AgentStream;