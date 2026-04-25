"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { 
  ShieldCheck, 
  Gear, 
  Key, 
  Globe, 
  Brain,
  Play,
  ArrowLeft,
  Robot,
  Cpu,
  Circle
} from "@phosphor-icons/react";
import AgentStream from "@/components/AgentStream";

interface AgentConfig {
  type: "custom" | "demo";
  model?: string;
  apiUrl?: string;
  apiKey?: string;
  baseUrl?: string;
}

const AVAILABLE_MODELS = [
  { id: "gpt-4o", name: "GPT-4o", provider: "OpenAI" },
  { id: "gpt-4o-mini", name: "GPT-4o Mini", provider: "OpenAI" },
  { id: "claude-sonnet", name: "Claude Sonnet", provider: "Anthropic" },
  { id: "claude-haiku", name: "Claude Haiku", provider: "Anthropic" },
  { id: "gemini-pro", name: "Gemini Pro", provider: "Google" },
];

const AVAILABLE_CASES = [
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
    type: "demo",
    model: "",
    apiUrl: "https://api.openai.com/v1",
    apiKey: "",
  });
  const [selectedCase, setSelectedCase] = useState("CASE-A-001");
  const [isRunning, setIsRunning] = useState(false);
  const [showSettings, setShowSettings] = useState(true);
  const [runKey, setRunKey] = useState(0);
  
  return (
    <div className="min-h-screen bg-black text-white">
      <header className="fixed top-0 left-0 right-0 z-50 glass-subtle">
        <div className="max-w-[1600px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => router.push("/")} className="p-2 hover:bg-white/5 rounded-lg transition-colors">
              <ArrowLeft size={20} />
            </button>
            <div className="w-10 h-10 rounded-xl bg-emerald-500 flex items-center justify-center">
              <Robot size={24} weight="bold" className="text-black" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight">Agent Test</h1>
              <p className="text-xs text-zinc-500">Run AI agent on LedgerShield</p>
            </div>
          </div>
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 rounded-lg hover:bg-white/5 transition-colors"
          >
            <Gear size={20} />
          </button>
        </div>
      </header>

      <main className="pt-24 px-6 pb-12 max-w-4xl mx-auto">
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
                  <label className="text-sm text-zinc-400 mb-3 block">Agent Type</label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      onClick={() => setConfig({ ...config, type: "custom" })}
                      className={`p-4 rounded-xl border text-left transition-all ${
                        config.type === "custom" 
                          ? "border-emerald-500 bg-emerald-500/10" 
                          : "border-white/10 hover:border-white/20"
                      }`}
                    >
                      <Key size={24} className={config.type === "custom" ? "text-emerald-400" : "text-zinc-500"} />
                      <div className="mt-2 font-medium">Custom Agent</div>
                      <div className="text-xs text-zinc-500">Use your own API key</div>
                    </button>
                    <button
                      onClick={() => setConfig({ ...config, type: "demo" })}
                      className={`p-4 rounded-xl border text-left transition-all ${
                        config.type === "demo" 
                          ? "border-emerald-500 bg-emerald-500/10" 
                          : "border-white/10 hover:border-white/20"
                      }`}
                    >
                      <Robot size={24} className={config.type === "demo" ? "text-emerald-400" : "text-zinc-500"} />
                      <div className="mt-2 font-medium">Demo Agent</div>
                      <div className="text-xs text-zinc-500">Hardcoded rules</div>
                    </button>
                  </div>
                </div>
                
                {config.type === "custom" && (
                  <>
                    <div>
                      <label className="text-sm text-zinc-400 mb-2 block">Model</label>
                      <select
                        value={config.model}
                        onChange={(e) => setConfig({ ...config, model: e.target.value })}
                        className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 focus:border-purple-500/50 outline-none transition-colors"
                      >
                        <option value="">Select model...</option>
                        {AVAILABLE_MODELS.map(m => (
                          <option key={m.id} value={m.id}>{m.name} ({m.provider})</option>
                        ))}
                      </select>
                    </div>
                    
                    <div>
                      <label className="text-sm text-zinc-400 mb-2 block">API URL</label>
                      <input
                        type="text"
                        value={config.apiUrl}
                        onChange={(e) => setConfig({ ...config, apiUrl: e.target.value })}
                        className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 focus:border-emerald-500/50 outline-none transition-colors"
                        placeholder="https://api.openai.com/v1"
                      />
                    </div>
                    
                    <div>
                      <label className="text-sm text-zinc-400 mb-2 block">API Key</label>
                      <input
                        type="password"
                        value={config.apiKey}
                        onChange={(e) => setConfig({ ...config, apiKey: e.target.value })}
                        className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 focus:border-emerald-500/50 outline-none transition-colors"
                        placeholder="sk-..."
                      />
                    </div>
                  </>
                )}
                
                <div>
                  <label className="text-sm text-zinc-400 mb-3 block">Select Case</label>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {AVAILABLE_CASES.map(c => (
                      <button
                        key={c.case_id}
                        onClick={() => setSelectedCase(c.case_id)}
                        className={`p-3 rounded-lg border text-left transition-all ${
                          selectedCase === c.case_id
                            ? "border-emerald-500 bg-emerald-500/10"
                            : "border-white/10 hover:border-white/20"
                        }`}
                      >
                        <span className="text-xs font-mono text-zinc-500">{c.case_id}</span>
                        <p className="text-sm mt-1">{c.instruction}</p>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        
        {!isRunning ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-12"
          >
            <button
              onClick={() => {
                if (config.type === "custom" && (!config.apiKey || !config.model)) {
                  setShowSettings(true);
                  return;
                }
                setShowSettings(false);
                setRunKey(k => k + 1);
                setIsRunning(true);
              }}
              className="px-8 py-4 rounded-xl bg-emerald-500 hover:bg-emerald-600 transition-all font-semibold text-black flex items-center gap-2 mx-auto"
            >
              <Play size={20} weight="fill" />
              Start Agent Run
            </button>
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="glass-subtle rounded-2xl p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-zinc-500">{selectedCase}</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400">
                  {config.type === "demo" ? "DEMO" : "CUSTOM"}
                </span>
              </div>
              <button
                onClick={() => setIsRunning(false)}
                className="text-sm text-zinc-400 hover:text-white transition-colors"
              >
                Stop
              </button>
            </div>
            
            <div className="bg-black/30 rounded-xl p-4 min-h-[400px] max-h-[600px] overflow-y-scroll">
              <AgentStream key={runKey} isDemo={config.type === "demo"} />
            </div>
            
            <div className="mt-4 pt-4 border-t border-white/10 flex items-center justify-between text-sm text-zinc-500">
              <div className="flex items-center gap-2">
                <Circle size={14} className="text-emerald-500" weight="fill" />
                <span>Connected to LedgerShield</span>
              </div>
              <span>Case: {selectedCase}</span>
            </div>
          </motion.div>
        )}
      </main>
    </div>
  );
}