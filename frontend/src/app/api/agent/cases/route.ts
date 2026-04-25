import { NextResponse } from "next/server";

import { envHealth, getBackendUrl } from "@/lib/agent/env-client";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const STATIC_CASES = [
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

export async function GET() {
  const ok = await envHealth();
  return NextResponse.json({
    backend: getBackendUrl(),
    backend_healthy: ok,
    cases: STATIC_CASES,
  });
}
