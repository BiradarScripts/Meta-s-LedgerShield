"use client";

import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, X } from "@phosphor-icons/react";

export type PreviewDoc = {
  doc_id?: string;
  doc_type?: string;
  page_count?: number;
  [key: string]: unknown;
};

/** Map CASE-A-001 → INV-A-001 for sample previews before reset. */
export function sampleDocIdForCase(caseId: string): string {
  const m = caseId.match(/^CASE-([A-E])-(\d{3})$/i);
  if (m) return `INV-${m[1].toUpperCase()}-${m[2]}`;
  return "INV-A-001";
}

function normType(t: string): string {
  return t.trim().toLowerCase();
}

function extractOcrPreview(
  lastToolResult: Record<string, unknown> | null | undefined,
): string | undefined {
  if (!lastToolResult) return undefined;
  const name = typeof lastToolResult.tool_name === "string" ? lastToolResult.tool_name : "";
  if (name !== "ocr") return undefined;
  const top = lastToolResult.text_preview;
  if (typeof top === "string" && top.trim()) return top.trim();
  const out = lastToolResult.output;
  if (out && typeof out === "object" && "text_preview" in out) {
    const tp = (out as Record<string, unknown>).text_preview;
    return typeof tp === "string" && tp.trim() ? tp.trim() : undefined;
  }
  return undefined;
}

function InvoiceStub({ docId }: { docId: string }) {
  return (
    <div className="space-y-6 text-sm text-zinc-300 leading-relaxed">
      <div className="border-b border-white/10 pb-4">
        <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-emerald-400/90 mb-1">
          Commercial invoice
        </p>
        <h3 className="text-lg font-semibold text-white">{docId}</h3>
        <p className="text-xs text-zinc-500 mt-1">Issued 2026-01-15 · Due NET 30</p>
      </div>
      <div className="grid grid-cols-2 gap-4 text-xs">
        <div>
          <p className="text-zinc-500 mb-1">Bill to</p>
          <p className="font-medium text-zinc-200">Contoso AP Operations</p>
          <p className="text-zinc-500">200 Commerce Way</p>
        </div>
        <div>
          <p className="text-zinc-500 mb-1">Vendor</p>
          <p className="font-medium text-zinc-200">Northwind Industrial Ltd.</p>
          <p className="text-zinc-500">vendor_key: northwind-industrial</p>
        </div>
      </div>
      <div className="rounded-lg border border-white/10 overflow-hidden text-xs font-mono">
        <div className="grid grid-cols-[1fr_4rem_6rem] gap-2 px-3 py-2 bg-white/5 text-zinc-500">
          <span>Description</span>
          <span className="text-right">Qty</span>
          <span className="text-right">Amount</span>
        </div>
        <div className="grid grid-cols-[1fr_4rem_6rem] gap-2 px-3 py-2 border-t border-white/5">
          <span>Industrial fittings — batch 2048-A</span>
          <span className="text-right">1</span>
          <span className="text-right tabular-nums">2,478.00 USD</span>
        </div>
      </div>
      <p className="text-[11px] text-zinc-500">
        This is a benchmark fixture for LedgerShield. Use OCR tools in a run to replace this with
        extracted text from the environment.
      </p>
    </div>
  );
}

function EmailStub({ docId }: { docId: string }) {
  return (
    <div className="space-y-4 text-sm text-zinc-300">
      <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4 font-mono text-xs space-y-2">
        <p>
          <span className="text-zinc-500">From:</span> accounts@northwind.example.com
        </p>
        <p>
          <span className="text-zinc-500">To:</span> ap@contoso.example.com
        </p>
        <p>
          <span className="text-zinc-500">Subject:</span> Invoice {docId} — payment instructions
        </p>
      </div>
      <p className="text-zinc-400 leading-relaxed">
        Please process the attached invoice for Northwind Industrial. Remit to the account on file;
        contact procurement for any bank detail changes.
      </p>
    </div>
  );
}

export function DocumentPreviewModal({
  open,
  onClose,
  doc,
  caseId,
  instruction,
  lastToolResult,
}: {
  open: boolean;
  onClose: () => void;
  doc: PreviewDoc | null;
  caseId?: string;
  instruction?: string;
  lastToolResult?: Record<string, unknown> | null;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const docId = typeof doc?.doc_id === "string" ? doc.doc_id : "—";
  const docType = typeof doc?.doc_type === "string" ? doc.doc_type : "document";
  const pages =
    typeof doc?.page_count === "number" && Number.isFinite(doc.page_count)
      ? doc.page_count
      : undefined;
  const ocr = extractOcrPreview(lastToolResult ?? null);
  const t = normType(docType);

  return (
    <AnimatePresence>
      {open && doc && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.98 }}
            transition={{ duration: 0.2 }}
            className="relative w-full max-w-lg max-h-[85vh] overflow-hidden rounded-2xl border border-white/15 bg-zinc-950 shadow-2xl flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3 px-5 py-4 border-b border-white/10 bg-white/[0.03]">
              <div className="flex items-start gap-3 min-w-0">
                <div className="mt-0.5 rounded-lg bg-emerald-500/15 p-2 text-emerald-400">
                  <FileText size={22} weight="duotone" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-mono text-zinc-500 truncate">{docId}</p>
                  <p className="text-sm font-medium text-white capitalize">{docType}</p>
                  {pages != null && (
                    <p className="text-[11px] text-zinc-500 mt-0.5">{pages} pages</p>
                  )}
                  {caseId && (
                    <p className="text-[10px] text-zinc-600 mt-1 font-mono">Case {caseId}</p>
                  )}
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg p-2 text-zinc-400 hover:bg-white/10 hover:text-white transition-colors"
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </div>

            <div className="overflow-y-auto px-5 py-4 flex-1">
              {instruction ? (
                <p className="text-[11px] text-zinc-500 mb-4 border-l-2 border-emerald-500/40 pl-3">
                  Task: {instruction}
                </p>
              ) : null}

              {ocr ? (
                <div>
                  <p className="text-[10px] font-mono uppercase tracking-[0.15em] text-zinc-500 mb-2">
                    OCR excerpt (last run)
                  </p>
                  <pre className="text-xs text-zinc-300 whitespace-pre-wrap font-mono bg-black/50 border border-white/10 rounded-lg p-3 max-h-48 overflow-y-auto">
                    {ocr}
                  </pre>
                </div>
              ) : t === "invoice" || t === "inv" ? (
                <InvoiceStub docId={docId} />
              ) : t === "email" ? (
                <EmailStub docId={docId} />
              ) : (
                <div>
                  <p className="text-xs text-zinc-500 mb-2">Document metadata</p>
                  <pre className="text-[11px] font-mono text-zinc-400 bg-black/40 border border-white/10 rounded-lg p-3 overflow-x-auto">
                    {JSON.stringify(doc, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
