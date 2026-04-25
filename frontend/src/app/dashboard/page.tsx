"use client";

import { useState } from "react";
import { useLedgerApi } from "@/lib/api";
import { useAppStore } from "@/store";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShieldCheck,
  Gear,
  Play,
  ChartBar,
  BuildingOffice,
  Warning,
  CheckCircle,
  XCircle,
  MagnifyingGlass,
  Bank,
  Envelope,
  Phone,
  TrendUp,
  Robot,
  ArrowLeft,
} from "@phosphor-icons/react";
import { useRouter } from "next/navigation";

function ToolButton({
  tool,
  onClick,
  disabled,
  loading,
}: {
  tool: string;
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
}) {
  const toolLabels: Record<string, { label: string; icon: any }> = {
    ocr: { label: "OCR Document", icon: MagnifyingGlass },
    lookup_vendor: { label: "Lookup Vendor", icon: BuildingOffice },
    lookup_vendor_history: { label: "Vendor History", icon: BuildingOffice },
    inspect_email_thread: { label: "Inspect Email", icon: Envelope },
    compare_bank_account: { label: "Compare Bank", icon: Bank },
    search_ledger: { label: "Search Ledger", icon: TrendUp },
    lookup_policy: { label: "Lookup Policy", icon: ShieldCheck },
    lookup_po: { label: "Lookup PO", icon: ChartBar },
    lookup_receipt: { label: "Lookup Receipt", icon: ChartBar },
    request_callback_verification: { label: "Request Callback", icon: Phone },
    route_to_security: { label: "Route to Security", icon: Warning },
    create_human_handoff: { label: "Human Handoff", icon: BuildingOffice },
    route_to_procurement: { label: "Route to Procurement", icon: BuildingOffice },
  };

  const info = toolLabels[tool] || { label: tool, icon: Gear };
  const Icon = info.icon;

  return (
    <motion.button
      onClick={onClick}
      disabled={disabled || loading}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed text-sm font-medium"
    >
      <Icon size={18} />
      <span>{info.label}</span>
    </motion.button>
  );
}

function DecisionButton({
  decision,
  onClick,
  disabled,
}: {
  decision: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  const styles: Record<string, string> = {
    PAY: "bg-emerald-500/20 border-emerald-500/30 hover:bg-emerald-500/30 text-emerald-400",
    HOLD: "bg-yellow-500/20 border-yellow-500/30 hover:bg-yellow-500/30 text-yellow-400",
    NEEDS_REVIEW: "bg-blue-500/20 border-blue-500/30 hover:bg-blue-500/30 text-blue-400",
    ESCALATE_FRAUD: "bg-red-500/20 border-red-500/30 hover:bg-red-500/30 text-red-400",
  };

  return (
    <motion.button
      onClick={onClick}
      disabled={disabled}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`flex-1 px-4 py-3 rounded-lg border transition-all font-semibold text-sm disabled:opacity-40 disabled:cursor-not-allowed ${styles[decision] || styles.NEEDS_REVIEW}`}
    >
      {decision}
    </motion.button>
  );
}

function SPRTVisualization({ sprtState }: { sprtState: any }) {
  if (!sprtState?.posterior_probabilities) return null;

  const probs = sprtState.posterior_probabilities;
  const fraud = probs.fraud || 0.5;
  const honest = probs.honest || 0.5;

  return (
    <div className="space-y-3">
      <span className="text-xs text-zinc-400">SPRT Belief State</span>
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-red-400">Fraud</span>
          <span className="font-mono">{(fraud * 100).toFixed(1)}%</span>
        </div>
        <div className="h-2 rounded-full bg-white/5 overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${fraud * 100}%` }}
            className="h-full bg-red-500 rounded-full"
          />
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-emerald-400">Honest</span>
          <span className="font-mono">{(honest * 100).toFixed(1)}%</span>
        </div>
        <div className="h-2 rounded-full bg-white/5 overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${honest * 100}%` }}
            className="h-full bg-emerald-500 rounded-full"
          />
        </div>
      </div>
    </div>
  );
}

const AVAILABLE_CASES = [
  { case_id: "CASE-A-001", task_type: "task_a", instruction: "Extract invoice fields from document" },
  { case_id: "CASE-A-002", task_type: "task_a", instruction: "Extract invoice fields from document" },
  { case_id: "CASE-A-003", task_type: "task_a", instruction: "Extract invoice fields from document" },
  { case_id: "CASE-A-004", task_type: "task_a", instruction: "Extract invoice fields from document" },
  { case_id: "CASE-B-001", task_type: "task_b", instruction: "Verify three-way match (Invoice, PO, Receipt)" },
  { case_id: "CASE-B-002", task_type: "task_b", instruction: "Verify three-way match (Invoice, PO, Receipt)" },
  { case_id: "CASE-B-003", task_type: "task_b", instruction: "Verify three-way match" },
  { case_id: "CASE-B-004", task_type: "task_b", instruction: "Verify three-way match" },
  { case_id: "CASE-B-005", task_type: "task_b", instruction: "Verify three-way match" },
  { case_id: "CASE-C-001", task_type: "task_c", instruction: "Detect duplicate invoice and verify bank account" },
  { case_id: "CASE-C-002", task_type: "task_c", instruction: "Detect duplicate invoice and verify bank account" },
  { case_id: "CASE-C-003", task_type: "task_c", instruction: "Detect duplicate invoice" },
  { case_id: "CASE-C-004", task_type: "task_c", instruction: "Detect duplicate invoice" },
  { case_id: "CASE-D-001", task_type: "task_d", instruction: "Full fraud investigation" },
  { case_id: "CASE-D-002", task_type: "task_d", instruction: "Full fraud investigation" },
  { case_id: "CASE-D-003", task_type: "task_d", instruction: "Full fraud investigation" },
  { case_id: "CASE-D-004", task_type: "task_d", instruction: "Full fraud investigation" },
  { case_id: "CASE-D-005", task_type: "task_d", instruction: "Full fraud investigation" },
  { case_id: "CASE-D-006", task_type: "task_d", instruction: "Full fraud investigation" },
  { case_id: "CASE-E-001", task_type: "task_e", instruction: "Campaign-level fraud detection" },
  { case_id: "CASE-E-002", task_type: "task_e", instruction: "Campaign-level fraud detection" },
];

export default function Dashboard() {
  const {
    reset,
    step,
    submitDecision,
    currentCaseId,
    observation,
    stepHistory,
    isLoading,
    isSubmitting,
    error,
  } = useLedgerApi();

  const { setApiUrl, apiUrl } = useAppStore();
  const router = useRouter();
  const [showSettings, setShowSettings] = useState(false);

  const handleReset = async (caseId: string) => {
    await reset(caseId);
  };

  const handleTool = async (tool: string) => {
    const docs = observation?.visible_documents || [];
    const docId = docs[0]?.doc_id || "INV-A-001";
    
    const payload: Record<string, any> = {};
    
    switch (tool) {
      case "lookup_vendor":
      case "lookup_vendor_history":
        payload.vendor_key = "northwind-industrial";
        break;
      case "compare_bank_account":
        payload.vendor_key = "northwind-industrial";
        payload.proposed_bank_account = "IN99FAKE000999888";
        break;
      case "lookup_policy":
        payload.rule_id = "POL-001";
        break;
      case "lookup_po":
        payload.po_id = docId.replace("INV", "PO");
        break;
      case "lookup_receipt":
        payload.receipt_id = docId.replace("INV", "RCP");
        break;
      case "search_ledger":
        payload.vendor_key = "northwind-industrial";
        break;
      case "inspect_email_thread":
        payload.thread_id = `thread-${docId}`;
        break;
      case "ocr":
      case "get_doc_crop":
      case "zoom":
        payload.doc_id = docId;
        payload.mode = tool === "get_doc_crop" ? "text" : "standard";
        break;
      case "request_callback_verification":
        payload.vendor_key = "northwind-industrial";
        break;
    }
    
    await step({ action_type: tool, payload });
  };

  const handleSubmit = async (decision: string) => {
    const reasonCodes =
      decision === "ESCALATE_FRAUD"
        ? ["bank_override_attempt", "sender_domain_spoof"]
        : decision === "HOLD"
        ? ["suspicious_signals"]
        : [];

    const policyChecks =
      decision === "ESCALATE_FRAUD"
        ? {
            three_way_match: "pass",
            bank_change_verification: "fail",
            duplicate_check: "fail",
            approval_threshold_check: "pass",
          }
        : {
            three_way_match: "pass",
            bank_change_verification: "pass",
            duplicate_check: "pass",
            approval_threshold_check: "pass",
          };

    await submitDecision(decision, 0.9, reasonCodes, policyChecks, {});
  };

  const latestResult = stepHistory[stepHistory.length - 1];
  const currentObs = observation;
  const lastInfo = latestResult?.info;
  const finalScore = lastInfo?.final_score;

  return (
    <div className="min-h-screen bg-black text-white">
      <header className="fixed top-0 left-0 right-0 z-50 glass-subtle">
        <div className="max-w-[1600px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => router.push("/")} className="p-2 hover:bg-white/5 rounded-lg transition-colors">
              <ArrowLeft size={20} />
            </button>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="p-2 rounded-lg hover:bg-white/5 transition-colors"
            >
              <Gear size={20} />
            </button>
            <button
              onClick={() => router.push("/agent")}
              className="p-2 rounded-lg hover:bg-white/5 transition-colors"
              title="Test Agent"
            >
              <Robot size={20} />
            </button>
          </div>
        </div>
      </header>

      <main className="pt-24 px-6 pb-12 max-w-[1600px] mx-auto">
        {!currentCaseId ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-4xl mx-auto"
          >
            <div className="text-center mb-12">
              <h2 className="text-4xl font-semibold tracking-tight mb-4">
                Select a <span className="text-gradient">Case</span> to Begin
              </h2>
              <p className="text-zinc-400 max-w-lg mx-auto">
                Choose a fraud investigation case to start an episode. Each case presents unique
                challenges requiring document analysis, vendor verification, and evidence synthesis.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {AVAILABLE_CASES.map((caseItem) => (
                <motion.button
                  key={caseItem.case_id}
                  onClick={() => handleReset(caseItem.case_id)}
                  disabled={isLoading}
                  whileHover={{ scale: 1.02, y: -2 }}
                  whileTap={{ scale: 0.98 }}
                  className="text-left p-5 rounded-2xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all group"
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-mono text-zinc-500">{caseItem.case_id}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400">
                      {caseItem.task_type.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-sm font-medium text-zinc-200 line-clamp-2">
                    {caseItem.instruction}
                  </p>
                  <div className="mt-4 flex items-center gap-2 text-xs text-zinc-500 group-hover:text-zinc-400 transition-colors">
                    <Play size={14} />
                    <span>Start</span>
                  </div>
                </motion.button>
              ))}
            </div>
          </motion.div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-3 space-y-4">
              <div className="glass-subtle rounded-2xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-mono text-zinc-500">{currentCaseId}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400">
                    {currentObs?.task_type?.toUpperCase()}
                  </span>
                </div>
                <p className="text-sm text-zinc-300 leading-relaxed">
                  {currentObs?.instruction}
                </p>
              </div>

              <div className="glass-subtle rounded-2xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-400">Budget</span>
                  <span className="text-sm font-mono">
                    ${currentObs?.budget_remaining?.toFixed(1) || "0.0"} / ${currentObs?.budget_total?.toFixed(1) || "0.0"}
                  </span>
                </div>
                <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                  <motion.div
                    initial={{ width: "100%" }}
                    animate={{
                      width: `${((currentObs?.budget_remaining || 0) / (currentObs?.budget_total || 1)) * 100}%`,
                    }}
                    className="h-full bg-emerald-500 rounded-full"
                  />
                </div>
                <div className="flex items-center justify-between text-xs text-zinc-500">
                  <span>Step {currentObs?.step_count || 0}</span>
                  <span>Clock {currentObs?.case_clock || 0}</span>
                </div>
              </div>

              <div className="glass-subtle rounded-2xl p-5">
                <SPRTVisualization sprtState={currentObs?.sprt_state} />
              </div>

              {currentObs?.risk_snapshot?.observed_risk_signals?.length ? (
                <div className="glass-subtle rounded-2xl p-5">
                  <span className="text-xs text-zinc-400 mb-3 block">Discovered Signals</span>
                  <div className="flex flex-wrap gap-2">
                    {currentObs.risk_snapshot.observed_risk_signals.map((signal: string) => (
                      <span
                        key={signal}
                        className="text-[10px] px-2 py-1 rounded-full bg-red-500/20 text-red-400 border border-red-500/30"
                      >
                        {signal}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>

            <div className="lg:col-span-6 space-y-4">
              <div className="glass-subtle rounded-2xl p-5 min-h-[300px]">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm font-medium">Investigation Panel</span>
                  <span className="text-xs text-zinc-500">
                    {currentObs?.tool_rankings?.should_stop
                      ? "Consider submitting"
                      : "Keep investigating"}
                  </span>
                </div>

                {!finalScore ? (
                  <div className="space-y-6">
                    <div className="grid grid-cols-2 gap-3">
                      {(currentObs?.allowed_actions || [])
                        .filter((a: string) => a !== "submit_decision")
                        .map((tool: string) => (
                          <ToolButton
                            key={tool}
                            tool={tool}
                            onClick={() => handleTool(tool)}
                            disabled={isLoading || isSubmitting}
                            loading={isLoading}
                          />
                        ))}
                    </div>

                    <div className="border-t border-white/10 pt-4">
                      <span className="text-xs text-zinc-400 mb-3 block">Submit Decision</span>
                      <div className="grid grid-cols-2 gap-3">
                        {(currentObs?.allowed_actions || []).includes("submit_decision") && (
                          <>
                            <DecisionButton
                              decision="PAY"
                              onClick={() => handleSubmit("PAY")}
                              disabled={isLoading || isSubmitting}
                            />
                            <DecisionButton
                              decision="HOLD"
                              onClick={() => handleSubmit("HOLD")}
                              disabled={isLoading || isSubmitting}
                            />
                            <DecisionButton
                              decision="NEEDS_REVIEW"
                              onClick={() => handleSubmit("NEEDS_REVIEW")}
                              disabled={isLoading || isSubmitting}
                            />
                            <DecisionButton
                              decision="ESCALATE_FRAUD"
                              onClick={() => handleSubmit("ESCALATE_FRAUD")}
                              disabled={isLoading || isSubmitting}
                            />
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-500/20 flex items-center justify-center">
                      <CheckCircle size={32} className="text-emerald-400" />
                    </div>
                    <h3 className="text-xl font-semibold mb-2">Case Complete</h3>
                    <p className="text-sm text-zinc-400">
                      Final Score: <span className="text-emerald-400 font-mono">{finalScore?.toFixed(3)}</span>
                    </p>
                    <button
                      onClick={() => handleReset(currentCaseId)}
                      className="mt-4 px-4 py-2 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-all text-sm"
                    >
                      Restart Case
                    </button>
                  </div>
                )}
              </div>

              <div className="glass-subtle rounded-2xl p-5">
                <span className="text-xs text-zinc-400 mb-3 block">Step History</span>
                <div className="space-y-2 max-h-[200px] overflow-y-auto">
                  {stepHistory.map((step: any, i: number) => (
                    <div
                      key={i}
                      className="flex items-center justify-between text-sm py-2 px-3 rounded-lg bg-white/5"
                    >
                      <span className="text-zinc-400">{step.action_type}</span>
                      <span
                        className={`text-xs font-mono ${
                          step.reward > 0
                            ? "text-emerald-400"
                            : step.reward < 0
                            ? "text-red-400"
                            : "text-zinc-500"
                        }`}
                      >
                        {step.reward > 0 ? "+" : ""}
                        {step.reward?.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="lg:col-span-3 space-y-4">
              <div className="glass-subtle rounded-2xl p-5">
                <span className="text-xs text-zinc-400 mb-3 block">Documents</span>
                {currentObs?.visible_documents?.map((doc: any) => (
                  <div
                    key={doc.doc_id}
                    className="flex items-center gap-3 p-3 rounded-lg bg-white/5 mb-2"
                  >
                    <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center">
                      <span className="text-xs font-mono">{doc.doc_type}</span>
                    </div>
                    <div>
                      <p className="text-sm font-medium">{doc.doc_id}</p>
                      <p className="text-xs text-zinc-500">{doc.page_count} pages</p>
                    </div>
                  </div>
                )) || <p className="text-sm text-zinc-500">No documents visible</p>}
              </div>

              <div className="glass-subtle rounded-2xl p-5">
                <span className="text-xs text-zinc-400 mb-3 block">Status</span>
                <div className="space-y-2">
                  <p className="text-sm text-zinc-300">
                    {latestResult?.done ? "Episode complete" : "Investigating..."}
                  </p>
                  <p className="text-xs text-zinc-500">
                    Reward: {latestResult?.reward?.toFixed(2) || "0.00"}
                  </p>
                </div>
              </div>

              {error && (
                <div className="glass-subtle rounded-2xl p-5 border border-red-500/30">
                  <div className="flex items-center gap-2 text-red-400 mb-2">
                    <XCircle size={16} />
                    <span className="text-sm font-medium">Error</span>
                  </div>
                  <p className="text-sm text-zinc-400">{error}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      <AnimatePresence>
        {showSettings && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={() => setShowSettings(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="glass rounded-2xl p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="text-lg font-semibold mb-4">Settings</h2>
              <div className="space-y-4">
                <div>
                  <label className="text-sm text-zinc-400 mb-2 block">API URL</label>
                  <input
                    type="text"
                    value={apiUrl}
                    onChange={(e) => setApiUrl(e.target.value)}
                    className="w-full px-4 py-2 rounded-lg bg-white/5 border border-white/10 focus:border-emerald-500/50 outline-none transition-colors text-sm"
                    placeholder="http://localhost:8000"
                  />
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
