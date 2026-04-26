"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Gear,
  Play,
  ArrowLeft,
  Cpu,
  Circle,
  Stop,
  Eye,
  EyeSlash,
  CheckCircle,
  XCircle,
  Spinner,
  Plug,
  BookOpen,
  ArrowSquareOut,
  TreeStructure,
} from "@phosphor-icons/react";

import AgentStream, { StreamEvent } from "@/components/AgentStream";
import { EnvironmentPanel } from "@/components/EnvironmentPanel";
import type { StepMath } from "@/lib/agent/diagnostics";
import { CertificateGraphModal } from "@/components/CertificateGraphModal";
import { LedgerShieldLogo } from "@/components/LedgerShieldLogo";
import {
  clearAgentFormStorage,
  loadAgentFormFromStorage,
  saveAgentFormToStorage,
} from "@/lib/agent/local-settings";

const DOCS_URL = "https://aryaman.mintlify.app/benchmark/benchmark-card";
const DEFAULT_API_URL = "https://api.openai.com/v1";

interface AgentConfig {
  model: string;
  apiUrl: string;
  apiKey: string;
}

interface AvailableCase {
  case_id: string;
  task_type: string;
  instruction: string;
}

type LlmHealthStatus = "idle" | "checking" | "ok" | "error";

interface LlmHealth {
  status: LlmHealthStatus;
  message?: string;
  latencyMs?: number;
  model?: string;
  sampleReply?: string;
}

/** Preset ids — your account may not expose every name; check the provider dashboard or /v1/models. */
const AVAILABLE_MODELS: { id: string; name: string; provider: string }[] = [
  { id: "gpt-5.5", name: "GPT-5.5", provider: "OpenAI · GPT-5 family" },
  { id: "gpt-5.4", name: "GPT-5.4", provider: "OpenAI · GPT-5 family" },
  { id: "gpt-5.4-mini", name: "GPT-5.4 mini", provider: "OpenAI · GPT-5 family" },
  { id: "gpt-5.4-nano", name: "GPT-5.4 nano", provider: "OpenAI · GPT-5 family" },
  { id: "gpt-5", name: "GPT-5", provider: "OpenAI · GPT-5 family" },
  { id: "gpt-4.1", name: "GPT-4.1", provider: "OpenAI · GPT-4.x" },
  { id: "gpt-4.1-mini", name: "GPT-4.1 mini", provider: "OpenAI · GPT-4.x" },
  { id: "gpt-4.1-nano", name: "GPT-4.1 nano", provider: "OpenAI · GPT-4.x" },
  { id: "gpt-4o", name: "GPT-4o", provider: "OpenAI · GPT-4.x" },
  { id: "gpt-4o-mini", name: "GPT-4o mini", provider: "OpenAI · GPT-4.x" },
  { id: "chatgpt-4o-latest", name: "ChatGPT-4o latest", provider: "OpenAI · GPT-4.x" },
  { id: "gpt-4-turbo", name: "GPT-4 Turbo", provider: "OpenAI · GPT-4.x" },
  { id: "gpt-3.5-turbo", name: "GPT-3.5 Turbo", provider: "OpenAI · GPT-4.x" },
  { id: "o4-mini", name: "o4-mini", provider: "OpenAI · reasoning" },
  { id: "o3", name: "o3", provider: "OpenAI · reasoning" },
  { id: "o3-mini", name: "o3-mini", provider: "OpenAI · reasoning" },
  { id: "o3-pro", name: "o3-pro", provider: "OpenAI · reasoning" },
  { id: "o1", name: "o1", provider: "OpenAI · reasoning" },
  { id: "o1-mini", name: "o1-mini", provider: "OpenAI · reasoning" },
  { id: "o1-preview", name: "o1-preview", provider: "OpenAI · reasoning" },
  {
    id: "claude-sonnet-4-20250514",
    name: "Claude Sonnet 4 (example id)",
    provider: "Other · via compatible proxy",
  },
  { id: "claude-3-5-sonnet-latest", name: "Claude 3.5 Sonnet", provider: "Other · via compatible proxy" },
  { id: "claude-3-5-haiku-latest", name: "Claude 3.5 Haiku", provider: "Other · via compatible proxy" },
  { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash (example)", provider: "Other · via compatible proxy" },
  { id: "gemini-1.5-pro", name: "Gemini 1.5 Pro", provider: "Other · via compatible proxy" },
];

const MODEL_PROVIDERS_ORDER = [
  "OpenAI · GPT-5 family",
  "OpenAI · GPT-4.x",
  "OpenAI · reasoning",
  "Other · via compatible proxy",
];

const CUSTOM_MODEL_SELECT = "__custom__";

const FALLBACK_CASES: AvailableCase[] = [
  { case_id: "CASE-A-001", task_type: "task_a", instruction: "Extract invoice fields from document" },
  { case_id: "CASE-A-002", task_type: "task_a", instruction: "Extract invoice fields from document" },
  { case_id: "CASE-A-003", task_type: "task_a", instruction: "Extract invoice fields from document" },
  { case_id: "CASE-A-004", task_type: "task_a", instruction: "Extract invoice fields from document" },
  { case_id: "CASE-B-001", task_type: "task_b", instruction: "Verify three-way match (Invoice, PO, Receipt)" },
  { case_id: "CASE-B-002", task_type: "task_b", instruction: "Verify three-way match (Invoice, PO, Receipt)" },
  { case_id: "CASE-B-003", task_type: "task_b", instruction: "Verify three-way match (Invoice, PO, Receipt)" },
  { case_id: "CASE-B-004", task_type: "task_b", instruction: "Verify three-way match (Invoice, PO, Receipt)" },
  { case_id: "CASE-B-005", task_type: "task_b", instruction: "Verify three-way match (Invoice, PO, Receipt)" },
  { case_id: "CASE-C-001", task_type: "task_c", instruction: "Detect duplicate invoice and verify bank account" },
  { case_id: "CASE-C-002", task_type: "task_c", instruction: "Detect duplicate invoice and verify bank account" },
  { case_id: "CASE-C-003", task_type: "task_c", instruction: "Detect duplicate invoice and verify bank account" },
  { case_id: "CASE-C-004", task_type: "task_c", instruction: "Detect duplicate invoice and verify bank account" },
  { case_id: "CASE-D-001", task_type: "task_d", instruction: "Full fraud investigation with email, vendor, bank, callback" },
  { case_id: "CASE-D-002", task_type: "task_d", instruction: "Full fraud investigation with email, vendor, bank, callback" },
  { case_id: "CASE-D-003", task_type: "task_d", instruction: "Full fraud investigation with email, vendor, bank, callback" },
  { case_id: "CASE-D-004", task_type: "task_d", instruction: "Full fraud investigation with email, vendor, bank, callback" },
  { case_id: "CASE-D-005", task_type: "task_d", instruction: "Full fraud investigation with email, vendor, bank, callback" },
  { case_id: "CASE-D-006", task_type: "task_d", instruction: "Full fraud investigation with email, vendor, bank, callback" },
  { case_id: "CASE-E-001", task_type: "task_e", instruction: "Campaign-level coordinated fraud detection" },
  { case_id: "CASE-E-002", task_type: "task_e", instruction: "Campaign-level coordinated fraud detection" },
];

export default function AgentTestPage() {
  const router = useRouter();

  const [config, setConfig] = useState<AgentConfig>({
    model: "gpt-4o-mini",
    apiUrl: DEFAULT_API_URL,
    apiKey: "",
  });
  const [rememberOnDevice, setRememberOnDevice] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [selectedCase, setSelectedCase] = useState("CASE-A-001");
  const [cases, setCases] = useState<AvailableCase[]>(FALLBACK_CASES);
  const [backendStatus, setBackendStatus] = useState<"unknown" | "ok" | "down">(
    "unknown",
  );

  const [showSettings, setShowSettings] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [finalScore, setFinalScore] = useState<number | null>(null);
  const [llmHealth, setLlmHealth] = useState<LlmHealth>({ status: "idle" });
  const [envObservation, setEnvObservation] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [cumulativeReward, setCumulativeReward] = useState(0);
  const [lastStepReward, setLastStepReward] = useState<number | null>(null);
  const [trustGraph, setTrustGraph] = useState<Record<string, unknown> | null>(
    null,
  );
  const [showCertificateModal, setShowCertificateModal] = useState(false);
  const [stepMath, setStepMath] = useState<StepMath | null>(null);
  const [activeRunCaseId, setActiveRunCaseId] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const healthAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const saved = loadAgentFormFromStorage();
    if (saved) {
      setRememberOnDevice(true);
      setConfig((prev) => ({
        ...prev,
        apiKey: saved.apiKey,
        apiUrl: saved.apiUrl || DEFAULT_API_URL,
        model: saved.model || prev.model,
      }));
    }
  }, []);

  useEffect(() => {
    if (!rememberOnDevice) return;
    saveAgentFormToStorage({
      apiKey: config.apiKey,
      apiUrl: config.apiUrl,
      model: config.model,
    });
  }, [rememberOnDevice, config.apiKey, config.apiUrl, config.model]);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/agent/cases")
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return;
        if (Array.isArray(data?.cases) && data.cases.length) {
          setCases(data.cases);
        }
        setBackendStatus(data?.backend_healthy ? "ok" : "down");
      })
      .catch(() => {
        if (!cancelled) setBackendStatus("down");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      healthAbortRef.current?.abort();
    };
  }, []);

  const updateConfig = (patch: Partial<AgentConfig>) => {
    setConfig((prev) => ({ ...prev, ...patch }));
    setLlmHealth((prev) =>
      prev.status === "idle" ? prev : { status: "idle" },
    );
  };

  const testLlmConnection = async () => {
    if (!config.apiKey.trim() || !config.model.trim()) {
      setLlmHealth({
        status: "error",
        message: "Provide API key and model first.",
      });
      return;
    }

    healthAbortRef.current?.abort();
    const controller = new AbortController();
    healthAbortRef.current = controller;
    setLlmHealth({ status: "checking" });

    try {
      const res = await fetch("/api/agent/health-check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          apiKey: config.apiKey,
          baseUrl: config.apiUrl,
          model: config.model,
        }),
        signal: controller.signal,
      });
      const data = (await res.json()) as {
        ok: boolean;
        backend?: { ok: boolean; url?: string };
        llm?: {
          ok: boolean;
          error?: string;
          latency_ms?: number;
          model?: string;
          sample_reply?: string;
        };
      };

      if (data?.backend?.ok !== undefined) {
        setBackendStatus(data.backend.ok ? "ok" : "down");
      }

      if (data?.llm?.ok) {
        setLlmHealth({
          status: "ok",
          latencyMs: data.llm.latency_ms,
          model: data.llm.model,
          sampleReply: data.llm.sample_reply,
        });
      } else {
        setLlmHealth({
          status: "error",
          message: data?.llm?.error || "Connection failed.",
        });
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setLlmHealth({
        status: "error",
        message: (err as Error).message || "Connection failed.",
      });
    }
  };

  const startRun = async () => {
    if (!config.apiKey.trim()) {
      setError("API key is required.");
      setShowSettings(true);
      return;
    }
    if (!config.model.trim()) {
      setError("Model is required.");
      setShowSettings(true);
      return;
    }
    setError(null);
    setEvents([]);
    setFinalScore(null);
    setEnvObservation(null);
    setCumulativeReward(0);
    setLastStepReward(null);
    setTrustGraph(null);
    setShowCertificateModal(false);
    setStepMath(null);
    setShowSettings(false);
    setIsRunning(true);

    const controller = new AbortController();
    abortRef.current?.abort();
    abortRef.current = controller;

    setActiveRunCaseId(selectedCase);

    try {
      const response = await fetch("/api/agent/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          caseId: selectedCase,
          model: config.model,
          baseUrl: config.apiUrl,
          apiKey: config.apiKey,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Request failed: ${response.status}`);
      }
      if (!response.body) {
        throw new Error("Response has no body.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let idx = buffer.indexOf("\n\n");
        while (idx !== -1) {
          const chunk = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          processChunk(chunk);
          idx = buffer.indexOf("\n\n");
        }
      }
      if (buffer.trim()) processChunk(buffer);
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        setEvents((prev) => [
          ...prev,
          { type: "status", content: "Run stopped by user." },
        ]);
      } else {
        const msg = (err as Error).message || "Agent run failed";
        setError(msg);
        setEvents((prev) => [
          ...prev,
          { type: "error", error: msg },
        ]);
      }
    } finally {
      setIsRunning(false);
    }
  };

  const processChunk = (chunk: string) => {
    const lines = chunk.split("\n");
    for (const line of lines) {
      if (!line.startsWith("data:")) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      try {
        const raw = JSON.parse(payload) as Record<string, unknown> & {
          type: string;
        };
        if (raw.type === "env_state") {
          if (raw.observation && typeof raw.observation === "object") {
            setEnvObservation(raw.observation as Record<string, unknown>);
          }
          setCumulativeReward(
            typeof raw.cumulative_reward === "number"
              ? raw.cumulative_reward
              : 0,
          );
          setLastStepReward(
            typeof raw.step_reward === "number" ? raw.step_reward : null,
          );
          if (raw.step_math && typeof raw.step_math === "object") {
            setStepMath(raw.step_math as StepMath);
          }
          continue;
        }
        if (
          raw.type === "result" &&
          raw.trust_graph &&
          typeof raw.trust_graph === "object"
        ) {
          setTrustGraph(raw.trust_graph as Record<string, unknown>);
        }
        setEvents((prev) => [...prev, raw as unknown as StreamEvent]);
      } catch {
        /* ignore malformed lines */
      }
    }
  };

  const stopRun = () => {
    abortRef.current?.abort();
  };

  const credsFilled =
    config.apiKey.trim().length > 0 && config.model.trim().length > 0;
  const ready = credsFilled && llmHealth.status === "ok";

  return (
    <div className="min-h-screen bg-black text-white">
      <header className="fixed top-0 left-0 right-0 z-50 glass-subtle">
        <div className="max-w-[1600px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/")}
              className="p-2 hover:bg-white/5 rounded-lg transition-colors"
            >
              <ArrowLeft size={20} />
            </button>
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-black/40 ring-1 ring-white/10">
              <LedgerShieldLogo size={34} />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight">Agent Test</h1>
              <p className="text-xs text-zinc-500">Run an LLM agent against LedgerShield</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <BackendBadge status={backendStatus} />
            <a
              href={DOCS_URL}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/10 hover:bg-white/5 transition-colors text-xs text-zinc-300"
              title="Open benchmark card docs"
            >
              <BookOpen size={14} />
              <span>Docs</span>
              <ArrowSquareOut size={11} className="opacity-70" />
            </a>
            <button
              onClick={() => setShowSettings((v) => !v)}
              className="p-2 rounded-lg hover:bg-white/5 transition-colors"
              aria-label="Toggle settings"
            >
              <Gear size={20} />
            </button>
          </div>
        </div>
      </header>

      <main className="pt-24 px-4 sm:px-6 pb-12 max-w-[1600px] mx-auto">
        <AnimatePresence mode="wait">
          {showSettings && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="glass-subtle rounded-2xl p-6 mb-6"
            >
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <Cpu size={20} />
                Agent Configuration
              </h2>

              <div className="space-y-6">
                    <div>
                      <label className="text-sm text-zinc-400 mb-2 block">Model</label>
                      <div className="space-y-2">
                        <select
                          value={
                            AVAILABLE_MODELS.some((m) => m.id === config.model)
                              ? config.model
                              : CUSTOM_MODEL_SELECT
                          }
                          onChange={(e) => {
                            const v = e.target.value;
                            if (v === CUSTOM_MODEL_SELECT) {
                              updateConfig({ model: "" });
                            } else {
                              updateConfig({ model: v });
                            }
                          }}
                          className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 focus:border-emerald-500/50 outline-none transition-colors font-mono text-sm"
                        >
                          {MODEL_PROVIDERS_ORDER.map((provider) => (
                            <optgroup label={provider} key={provider}>
                              {AVAILABLE_MODELS.filter((m) => m.provider === provider).map(
                                (m) => (
                                  <option key={m.id} value={m.id}>
                                    {m.name} ({m.id})
                                  </option>
                                ),
                              )}
                            </optgroup>
                          ))}
                          <option value={CUSTOM_MODEL_SELECT}>Custom model ID…</option>
                        </select>
                        {!AVAILABLE_MODELS.some((m) => m.id === config.model) && (
                          <input
                            type="text"
                            value={config.model}
                            onChange={(e) =>
                              updateConfig({ model: e.target.value })
                            }
                            className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 focus:border-emerald-500/50 outline-none transition-colors font-mono text-sm"
                            placeholder="Exact id from your provider (e.g. gpt-5.5)"
                            spellCheck={false}
                          />
                        )}
                      </div>
                      <p className="text-[10px] text-zinc-500 mt-1">
                        Presets follow common OpenAI-style ids (incl. GPT-5.x / o-series names from
                        provider docs). If a call fails, confirm the id with{" "}
                        <code className="font-mono">GET /v1/models</code> or your dashboard — names
                        change by rollout.
                      </p>
                    </div>

                    <div>
                      <label className="text-sm text-zinc-400 mb-2 block">
                        API Base URL
                      </label>
                      <input
                        type="text"
                        value={config.apiUrl}
                        onChange={(e) =>
                          updateConfig({ apiUrl: e.target.value })
                        }
                        className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 focus:border-emerald-500/50 outline-none transition-colors font-mono text-sm"
                        placeholder="https://api.openai.com/v1"
                      />
                      <p className="text-[10px] text-zinc-500 mt-1">
                        OpenAI-compatible endpoint. Use a proxy URL for Anthropic/Gemini if needed.
                      </p>
                    </div>

                    <div>
                      <label className="text-sm text-zinc-400 mb-2 block">API Key</label>
                      <div className="relative">
                        <input
                          type={showApiKey ? "text" : "password"}
                          value={config.apiKey}
                          onChange={(e) =>
                            updateConfig({ apiKey: e.target.value })
                          }
                          className="w-full px-4 py-3 pr-12 rounded-lg bg-white/5 border border-white/10 focus:border-emerald-500/50 outline-none transition-colors font-mono text-sm"
                          placeholder="sk-..."
                          autoComplete="off"
                          spellCheck={false}
                        />
                        <button
                          type="button"
                          onClick={() => setShowApiKey((v) => !v)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-200"
                        >
                          {showApiKey ? <EyeSlash size={16} /> : <Eye size={16} />}
                        </button>
                      </div>
                      <label className="mt-3 flex items-start gap-2 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          className="mt-1 rounded border-white/20 bg-white/5"
                          checked={rememberOnDevice}
                          onChange={(e) => {
                            const on = e.target.checked;
                            setRememberOnDevice(on);
                            if (!on) clearAgentFormStorage();
                            else {
                              saveAgentFormToStorage({
                                apiKey: config.apiKey,
                                apiUrl: config.apiUrl,
                                model: config.model,
                              });
                            }
                          }}
                        />
                        <span className="text-xs text-zinc-400 leading-snug">
                          Remember API key, base URL, and model in{" "}
                          <span className="text-zinc-300">this browser only</span> (localStorage).
                          Uncheck to clear saved values. Your key is only sent to this app’s server
                          when you run the agent — it is not uploaded elsewhere by LedgerShield.
                        </span>
                      </label>
                    </div>

                    <ConnectionCheck
                      health={llmHealth}
                      disabled={!credsFilled || llmHealth.status === "checking"}
                      onTest={testLlmConnection}
                    />

                <div>
                  <div className="flex items-center justify-between mb-3">
                    <label className="text-sm text-zinc-400">Select Case</label>
                    <a
                      href={`${DOCS_URL}#demo-cases`}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-[10px] font-mono uppercase tracking-[0.18em] text-zinc-500 hover:text-zinc-300 transition-colors"
                    >
                      What are these?
                      <ArrowSquareOut size={10} />
                    </a>
                  </div>
                  {llmHealth.status !== "ok" && (
                    <p className="text-[11px] text-amber-300/80 mb-2">
                      Test your LLM connection above before selecting a case.
                    </p>
                  )}
                  <div
                    className={`grid grid-cols-2 md:grid-cols-3 gap-2 max-h-[300px] overflow-y-auto pr-1 transition-opacity ${
                      llmHealth.status !== "ok"
                        ? "opacity-40 pointer-events-none"
                        : ""
                    }`}
                  >
                    {cases.map((c) => (
                      <button
                        key={c.case_id}
                        onClick={() => setSelectedCase(c.case_id)}
                        className={`p-3 rounded-lg border text-left transition-all ${
                          selectedCase === c.case_id
                            ? "border-emerald-500 bg-emerald-500/10"
                            : "border-white/10 hover:border-white/20"
                        }`}
                      >
                        <span className="text-xs font-mono text-zinc-500">
                          {c.case_id}
                        </span>
                        <p className="text-xs mt-1 text-zinc-300 leading-snug">
                          {c.instruction}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg border border-red-500/30 bg-red-500/10 text-sm text-red-300">
            {error}
          </div>
        )}

        {!isRunning && events.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-12"
          >
            <button
              onClick={startRun}
              disabled={!ready}
              className="px-8 py-4 rounded-xl bg-emerald-500 hover:bg-emerald-600 disabled:bg-zinc-700 disabled:cursor-not-allowed transition-all font-semibold text-black flex items-center gap-2 mx-auto"
            >
              <Play size={20} weight="fill" />
              Start Agent Run
            </button>
            {backendStatus === "down" && (
              <p className="text-xs text-amber-400 mt-3">
                LedgerShield backend looks unreachable. Start it with{" "}
                <code className="font-mono">python -m server.app</code>.
              </p>
            )}
            {credsFilled && llmHealth.status !== "ok" && (
              <p className="text-xs text-amber-400 mt-3">
                Test your LLM connection in settings before starting a run.
              </p>
            )}
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="glass-subtle rounded-2xl p-6"
          >
            <div className="grid lg:grid-cols-[1fr_minmax(280px,340px)] gap-6 items-start">
              <div className="min-w-0">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-mono text-zinc-500">
                  {String(
                    (envObservation?.case_id as string | undefined) ||
                      activeRunCaseId ||
                      selectedCase,
                  )}
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400">
                  LLM
                </span>
                <span className="text-[10px] font-mono text-zinc-500">
                  · {config.model}
                </span>
                {finalScore !== null && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 font-mono">
                    score {finalScore.toFixed(3)}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {isRunning ? (
                  <button
                    onClick={stopRun}
                    className="text-xs px-3 py-1.5 rounded-lg border border-red-500/30 text-red-300 hover:bg-red-500/10 transition-colors flex items-center gap-1"
                  >
                    <Stop size={14} weight="fill" /> Stop
                  </button>
                ) : (
                  <button
                    onClick={() => {
                      setEvents([]);
                      setFinalScore(null);
                      setError(null);
                      setEnvObservation(null);
                      setCumulativeReward(0);
                      setLastStepReward(null);
                      setTrustGraph(null);
                      setShowCertificateModal(false);
                      setStepMath(null);
                      setActiveRunCaseId(null);
                    }}
                    className="text-xs px-3 py-1.5 rounded-lg border border-white/10 hover:bg-white/5 transition-colors"
                  >
                    Reset
                  </button>
                )}
                <button
                  onClick={() => setShowSettings((v) => !v)}
                  className="text-xs px-3 py-1.5 rounded-lg border border-white/10 hover:bg-white/5 transition-colors"
                >
                  {showSettings ? "Hide" : "Show"} settings
                </button>
                {!isRunning && (
                  <button
                    onClick={startRun}
                    disabled={!ready}
                    className="text-xs px-3 py-1.5 rounded-lg bg-emerald-500 text-black hover:bg-emerald-400 disabled:bg-zinc-700 disabled:text-zinc-400 transition-colors flex items-center gap-1"
                  >
                    <Play size={14} weight="fill" /> Run again
                  </button>
                )}
              </div>
            </div>

            <div className="bg-black/30 rounded-xl p-4 min-h-[400px] max-h-[640px] overflow-y-auto">
              <AgentStream
                events={events}
                isStreaming={isRunning}
                onResultRevealed={(r) => setFinalScore(r.final_score)}
              />
            </div>

            <div className="mt-4 pt-4 border-t border-white/10 flex items-center justify-between text-xs text-zinc-500">
              <div className="flex items-center gap-2">
                <Circle
                  size={10}
                  weight="fill"
                  className={
                    isRunning
                      ? "text-emerald-400 animate-pulse"
                      : finalScore !== null
                        ? "text-amber-400"
                        : "text-zinc-500"
                  }
                />
                <span>
                  {isRunning
                    ? "Agent running..."
                    : finalScore !== null
                      ? "Episode complete"
                      : "Idle"}
                </span>
              </div>
              <span>{events.length} events</span>
            </div>
              </div>

              <aside className="space-y-3 lg:sticky lg:top-24 lg:self-start">
                <EnvironmentPanel
                  observation={envObservation}
                  cumulativeReward={cumulativeReward}
                  stepReward={lastStepReward}
                  stepMath={stepMath}
                  isRunning={isRunning}
                />
                <button
                  type="button"
                  onClick={() => setShowCertificateModal(true)}
                  disabled={!trustGraph}
                  className="w-full flex items-center justify-center gap-2 rounded-xl border border-violet-500/30 bg-violet-500/10 px-4 py-3 text-sm font-medium text-violet-200 hover:bg-violet-500/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-violet-500/10"
                >
                  <TreeStructure size={18} className="shrink-0" />
                  View certificate graph
                </button>
                {!trustGraph && finalScore !== null && (
                  <p className="text-[10px] text-zinc-600 text-center px-1">
                    Graph appears when the backend returns a trust/certificate
                    payload after grading.
                  </p>
                )}
              </aside>
            </div>
          </motion.div>
        )}
      </main>

      <CertificateGraphModal
        open={showCertificateModal}
        onClose={() => setShowCertificateModal(false)}
        graph={trustGraph}
      />
    </div>
  );
}

function ConnectionCheck({
  health,
  disabled,
  onTest,
}: {
  health: LlmHealth;
  disabled: boolean;
  onTest: () => void;
}) {
  const palette: Record<LlmHealthStatus, string> = {
    idle: "border-white/10 bg-white/5 text-zinc-400",
    checking: "border-blue-500/30 bg-blue-500/10 text-blue-300",
    ok: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    error: "border-red-500/30 bg-red-500/10 text-red-300",
  };

  const Icon =
    health.status === "ok"
      ? CheckCircle
      : health.status === "error"
        ? XCircle
        : health.status === "checking"
          ? Spinner
          : Plug;

  const headline =
    health.status === "ok"
      ? "Connection successful"
      : health.status === "error"
        ? "Connection failed"
        : health.status === "checking"
          ? "Testing connection…"
          : "Connection not tested";

  const detail =
    health.status === "ok"
      ? `${health.model || "model"} responded${
          typeof health.latencyMs === "number"
            ? ` in ${health.latencyMs} ms`
            : ""
        }${health.sampleReply ? ` · "${health.sampleReply}"` : ""}`
      : health.status === "error"
        ? health.message || "Unknown error"
        : health.status === "checking"
          ? "Sending a 1-token chat completion to verify the key, base URL and model."
          : "Run a connection test to verify your key, base URL and model before selecting a case.";

  return (
    <div
      className={`rounded-xl border px-4 py-3 flex items-start gap-3 ${palette[health.status]}`}
    >
      <Icon
        size={20}
        weight={health.status === "ok" ? "fill" : "regular"}
        className={`mt-0.5 shrink-0 ${
          health.status === "checking" ? "animate-spin" : ""
        }`}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <span className="text-sm font-medium">{headline}</span>
          <button
            type="button"
            onClick={onTest}
            disabled={disabled}
            className="text-xs px-3 py-1.5 rounded-lg border border-current/20 hover:bg-white/5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
          >
            {health.status === "checking" ? (
              <>
                <Spinner size={12} className="animate-spin" /> Testing
              </>
            ) : (
              <>
                <Plug size={12} /> Test connection
              </>
            )}
          </button>
        </div>
        <p className="text-[11px] mt-1 leading-snug break-words opacity-80">
          {detail}
        </p>
      </div>
    </div>
  );
}

function BackendBadge({
  status,
}: {
  status: "unknown" | "ok" | "down";
}) {
  const map: Record<typeof status, { label: string; color: string }> = {
    unknown: { label: "checking", color: "text-zinc-400 bg-zinc-500/10 border-zinc-500/30" },
    ok: { label: "backend live", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30" },
    down: { label: "backend down", color: "text-red-400 bg-red-500/10 border-red-500/30" },
  };
  const cfg = map[status];
  return (
    <span
      className={`text-[10px] font-mono px-2 py-1 rounded-full border ${cfg.color}`}
    >
      {cfg.label}
    </span>
  );
}
