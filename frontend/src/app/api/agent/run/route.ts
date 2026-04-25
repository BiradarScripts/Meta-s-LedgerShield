import { NextRequest } from "next/server";

import { runAgent, type AgentRunEvent } from "@/lib/agent/runner";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RunBody = {
  caseId?: string;
  apiKey?: string;
  baseUrl?: string;
  model?: string;
  mode?: "demo" | "custom";
  maxIterations?: number;
  temperature?: number;
};

const DEMO_TRUST_GRAPH: Record<string, unknown> = {
  certificate_version: "demo-trust-graph",
  nodes: [
    { id: "case:CASE-A-001", type: "Case", label: "CASE-A-001" },
    { id: "invoice:INV-A-001", type: "Invoice", label: "INV-A-001" },
    { id: "vendor:northwind", type: "Vendor", label: "Northwind" },
    { id: "decision:final", type: "Decision", label: "PAY" },
    { id: "certificate:decision", type: "Certificate", label: "valid" },
  ],
  edges: [
    { source: "case:CASE-A-001", target: "invoice:INV-A-001", type: "contains" },
    { source: "invoice:INV-A-001", target: "vendor:northwind", type: "invoice_issued_by_vendor" },
    { source: "certificate:decision", target: "decision:final", type: "decision_supported_by_certificate" },
    { source: "vendor:northwind", target: "decision:final", type: "supports" },
  ],
};

const DEMO_ENV_OBS: Record<string, unknown> = {
  case_id: "CASE-A-001",
  task_type: "task_a",
  instruction: "Extract invoice fields from document",
  step_count: 0,
  max_steps: 24,
  budget_remaining: 1.0,
  budget_total: 1.0,
  decision_readiness: 0.15,
  visible_documents: [{ doc_id: "INV-A-001", doc_type: "invoice" }],
  risk_snapshot: { observed_risk_signals: [] },
  investigation_status: { phase: "demo" },
  last_tool_result: {},
  case_metadata: { track_mode: "demo" },
  sprt_state: {
    posterior_probabilities: { fraud: 0.42, honest: 0.58 },
    recommended_decision: "NEEDS_REVIEW",
    optimal_stopping_reached: false,
  },
  reward_machine: { progress_fraction: 0.12, state_id: 1 },
};

const DEMO_MATH_AFTER_OCR = {
  reward_model: {
    value: 0.05,
    terminal: false,
    components: {
      voi_reward: 0.052,
      information_value: 0.118,
      cost_penalty: -0.066,
      potential_delta: 0.01,
    },
    metadata: {
      action_type: "ocr",
      observation_key: "ocr_tokens",
      novel_signal_count: 0,
      success: true,
    },
  },
  rl_plane: {
    reward: 0.05,
    terminal: false,
    truncated: false,
    state_dim: 37,
    preview: [0, 0.024, -0.011, 0.003, 0, 0, 0.02, 0.015],
    best_tool_voi: 0.0412,
    watchdog: 0.08,
    calibration: 0.72,
  },
};

const DEMO_MATH_AFTER_VENDOR = {
  reward_model: {
    value: 0.03,
    terminal: false,
    components: {
      voi_reward: 0.031,
      information_value: 0.095,
      cost_penalty: -0.065,
      potential_delta: 0.008,
    },
    metadata: {
      action_type: "lookup_vendor",
      observation_key: "vendor_profile",
      novel_signal_count: 0,
      success: true,
    },
  },
  rl_plane: {
    reward: 0.03,
    terminal: false,
    state_dim: 37,
    preview: [0, 0.031, -0.008, 0.01, 0.002, 0, 0.019, 0.022],
    best_tool_voi: 0.0388,
    watchdog: 0.11,
    calibration: 0.76,
  },
};

const DEMO_MATH_TERMINAL = {
  reward_model: {
    value: 0.87,
    terminal: true,
    components: {
      voi_reward: 0.12,
      information_value: 0.04,
      cost_penalty: -0.02,
      outcome_bonus: 0.63,
      potential_delta: 0,
    },
    metadata: {
      action_type: "submit_decision",
      observation_key: "decision",
      novel_signal_count: 0,
      success: true,
      terminal_reason: "decision_submitted",
    },
  },
  rl_plane: {
    reward: 0.87,
    terminal: true,
    truncated: false,
    state_dim: 37,
    preview: [0.92, 0.04, 0.01, 0, 0, 0.88, 0.02, 0.015],
    best_tool_voi: 0.12,
    watchdog: 0.02,
    calibration: 0.94,
  },
};

const DEMO_EVENTS: AgentRunEvent[] = [
  { type: "status", content: "Initializing demo agent..." },
  {
    type: "env_state",
    observation: { ...DEMO_ENV_OBS },
    cumulative_reward: 0,
    step_math: {
      reward_model: {
        value: 0,
        terminal: false,
        components: {},
        metadata: {},
      },
      rl_plane: {
        reward: 0,
        terminal: false,
        state_dim: 37,
        preview: [0, 0, 0, 0, 0, 0, 0, 0],
        best_tool_voi: 0.05,
        watchdog: 0.05,
        calibration: 0.7,
      },
    },
  },
  {
    type: "tool_use",
    id: "demo-1",
    name: "ocr",
    input: { doc_id: "INV-A-001", mode: "accurate" },
  },
  {
    type: "tool_result",
    id: "demo-1",
    name: "ocr",
    output: {
      doc_id: "INV-A-001",
      mode: "accurate",
      text_preview:
        "Northwind Industrial INV-2048-A 2026-01-15 Total: 2478.00 USD",
    },
    reward: 0.05,
  },
  {
    type: "env_state",
    observation: {
      ...DEMO_ENV_OBS,
      step_count: 1,
      decision_readiness: 0.35,
      last_tool_result: { tool_name: "ocr", success: true },
    },
    cumulative_reward: 0.05,
    step_reward: 0.05,
    step_math: { ...DEMO_MATH_AFTER_OCR },
  },
  {
    type: "thinking",
    content: "Vendor name 'Northwind Industrial' detected. Looking up master data...",
  },
  {
    type: "tool_use",
    id: "demo-2",
    name: "lookup_vendor",
    input: { vendor_key: "northwind-industrial" },
  },
  {
    type: "tool_result",
    id: "demo-2",
    name: "lookup_vendor",
    output: {
      vendor: {
        vendor_key: "northwind-industrial",
        bank_account: "IN55NW000111222",
        expected_domain: "northwind.example.com",
      },
    },
    reward: 0.03,
  },
  {
    type: "env_state",
    observation: {
      ...DEMO_ENV_OBS,
      step_count: 2,
      decision_readiness: 0.72,
      last_tool_result: { tool_name: "lookup_vendor", success: true },
      sprt_state: {
        posterior_probabilities: { fraud: 0.38, honest: 0.62 },
        recommended_decision: "NEEDS_REVIEW",
        optimal_stopping_reached: false,
      },
      reward_machine: { progress_fraction: 0.45, state_id: 2 },
    },
    cumulative_reward: 0.08,
    step_reward: 0.03,
    step_math: { ...DEMO_MATH_AFTER_VENDOR },
  },
  {
    type: "thinking",
    content: "Approved bank account matches invoice. No bank-change attempt detected.",
  },
  {
    type: "tool_use",
    id: "demo-3",
    name: "submit_decision",
    input: {
      decision: "PAY",
      confidence: 0.92,
      reason_codes: ["vendor_master_data_match", "no_bank_change_attempt"],
    },
  },
  {
    type: "decision",
    decision: "PAY",
    confidence: 0.92,
    reason_codes: ["vendor_master_data_match", "no_bank_change_attempt"],
    policy_checks: { three_way_match: "pass", bank_change_verification: "pass" },
  },
  {
    type: "env_state",
    observation: {
      ...DEMO_ENV_OBS,
      step_count: 3,
      decision_readiness: 1,
      last_tool_result: { tool_name: "submit_decision", success: true },
      sprt_state: {
        posterior_probabilities: { fraud: 0.08, honest: 0.92 },
        recommended_decision: "PAY",
        optimal_stopping_reached: true,
      },
      reward_machine: { progress_fraction: 1, state_id: 4 },
    },
    cumulative_reward: 0.95,
    step_reward: 0.87,
    step_math: { ...DEMO_MATH_TERMINAL },
  },
  {
    type: "result",
    final_score: 0.95,
    reward: 0.95,
    info: { final_score: 0.95 },
    observation: { case_id: "CASE-A-001" },
    trust_graph: DEMO_TRUST_GRAPH,
  },
  { type: "done" },
];

function eventToSse(event: AgentRunEvent): string {
  return `data: ${JSON.stringify(event)}\n\n`;
}

async function* streamDemo(): AsyncGenerator<AgentRunEvent, void, void> {
  for (const event of DEMO_EVENTS) {
    await new Promise((r) => setTimeout(r, 700));
    yield event;
  }
}

export async function POST(request: NextRequest) {
  let body: RunBody = {};
  try {
    body = (await request.json()) as RunBody;
  } catch {
    return new Response(JSON.stringify({ error: "Invalid JSON body" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const caseId = body.caseId || "";
  const mode = body.mode || "demo";

  if (!caseId) {
    return new Response(JSON.stringify({ error: "caseId is required" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (mode === "custom") {
    if (!body.apiKey) {
      return new Response(
        JSON.stringify({ error: "apiKey is required in custom mode" }),
        { status: 400, headers: { "Content-Type": "application/json" } },
      );
    }
    if (!body.model) {
      return new Response(
        JSON.stringify({ error: "model is required in custom mode" }),
        { status: 400, headers: { "Content-Type": "application/json" } },
      );
    }
  }

  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const send = (event: AgentRunEvent) => {
        try {
          controller.enqueue(encoder.encode(eventToSse(event)));
        } catch {
          /* controller may already be closed */
        }
      };

      const ping = setInterval(() => {
        try {
          controller.enqueue(encoder.encode(": ping\n\n"));
        } catch {
          /* ignore */
        }
      }, 15000);

      try {
        const generator =
          mode === "demo"
            ? streamDemo()
            : runAgent({
                caseId,
                apiKey: body.apiKey || "",
                baseUrl: body.baseUrl,
                model: body.model || "gpt-4o-mini",
                maxIterations: body.maxIterations,
                temperature: body.temperature,
              });

        for await (const event of generator) {
          send(event);
          if (event.type === "done") break;
        }
      } catch (err) {
        send({
          type: "error",
          error: (err as Error).message || "Unknown agent error",
        });
        send({ type: "done" });
      } finally {
        clearInterval(ping);
        try {
          controller.close();
        } catch {
          /* ignore */
        }
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
