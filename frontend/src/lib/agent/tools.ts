import type OpenAI from "openai";

type ChatTool = OpenAI.Chat.Completions.ChatCompletionTool;

const THOUGHT_FIELD = {
  type: "string",
  description:
    "REQUIRED. One concise sentence (≤30 words) describing exactly what hypothesis or piece of evidence this call is meant to test, and why this specific tool + arguments are the right next step.",
};

const CONFIDENCE_FIELD = {
  type: "number",
  minimum: 0,
  maximum: 1,
  description:
    "REQUIRED. Float in [0,1] expressing how confident you are that THIS tool call (not the future result) is the correct next move given the evidence so far. Use <0.5 if you are guessing, ~0.7 for a sensible default move, ≥0.85 only when the next action is clearly mandated by the policy or by prior evidence.",
};

function withThought(tool: ChatTool): ChatTool {
  if (tool.type !== "function") return tool;
  const fn = tool.function;
  const params = (fn.parameters as Record<string, unknown> | undefined) || {
    type: "object",
    properties: {},
  };
  const properties = {
    ...((params.properties as Record<string, unknown>) || {}),
    thought: THOUGHT_FIELD,
    confidence: CONFIDENCE_FIELD,
  };
  const required = Array.from(
    new Set([
      ...((params.required as string[] | undefined) || []),
      "thought",
      "confidence",
    ]),
  );
  return {
    ...tool,
    function: {
      ...fn,
      parameters: { ...params, properties, required },
    },
  };
}

const RAW_TOOLS: ChatTool[] = [
  {
    type: "function",
    function: {
      name: "ocr",
      description:
        "Run OCR on a visible document. Use mode='accurate' for invoices and emails to extract all fields and line items. Returns tokens and a text preview.",
      parameters: {
        type: "object",
        properties: {
          doc_id: { type: "string", description: "Document ID from visible_documents." },
          mode: { type: "string", enum: ["fast", "accurate"], description: "Accurate is required for trustworthy field extraction." },
          page: { type: "integer", description: "Optional page number." },
        },
        required: ["doc_id", "mode"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "lookup_vendor",
      description: "Return master-data vendor profile (approved bank account, expected domain, contacts).",
      parameters: {
        type: "object",
        properties: {
          vendor_key: { type: "string", description: "Normalized vendor key e.g. 'northwind-industrial'." },
        },
        required: ["vendor_key"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "lookup_vendor_history",
      description: "Return historical events for a vendor (bank changes, fraud events, statuses).",
      parameters: {
        type: "object",
        properties: {
          vendor_key: { type: "string" },
        },
        required: ["vendor_key"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "lookup_policy",
      description: "Look up a specific AP policy rule, or all rules if rule_id is omitted.",
      parameters: {
        type: "object",
        properties: { rule_id: { type: "string", description: "Optional policy id." } },
      },
    },
  },
  {
    type: "function",
    function: {
      name: "lookup_po",
      description: "Fetch a Purchase Order by id (used for three-way match).",
      parameters: {
        type: "object",
        properties: { po_id: { type: "string" } },
        required: ["po_id"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "lookup_receipt",
      description: "Fetch a Goods Receipt by id (used for three-way match).",
      parameters: {
        type: "object",
        properties: { receipt_id: { type: "string" } },
        required: ["receipt_id"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "search_ledger",
      description: "Search the ledger for duplicate invoices by vendor / number / amount.",
      parameters: {
        type: "object",
        properties: {
          vendor_key: { type: "string" },
          invoice_number: { type: "string" },
          amount: { type: "number" },
        },
      },
    },
  },
  {
    type: "function",
    function: {
      name: "inspect_email_thread",
      description: "Inspect an email thread for a vendor for bank-change attempts, urgency, override language.",
      parameters: {
        type: "object",
        properties: { thread_id: { type: "string" } },
        required: ["thread_id"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "compare_bank_account",
      description: "Compare a proposed bank account against the vendor's approved master-data account.",
      parameters: {
        type: "object",
        properties: {
          vendor_key: { type: "string" },
          proposed_bank_account: { type: "string" },
        },
        required: ["vendor_key", "proposed_bank_account"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "request_callback_verification",
      description: "Trigger an out-of-band callback verification with the vendor.",
      parameters: {
        type: "object",
        properties: { vendor_key: { type: "string" } },
        required: ["vendor_key"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "request_bank_change_approval_chain",
      description: "Open the formal bank-change approval workflow for a vendor.",
      parameters: {
        type: "object",
        properties: { vendor_key: { type: "string" } },
        required: ["vendor_key"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "freeze_vendor_profile",
      description: "Freeze a vendor profile while suspected fraud is investigated.",
      parameters: {
        type: "object",
        properties: { vendor_key: { type: "string" } },
        required: ["vendor_key"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "route_to_security",
      description: "Route the case to the security team for fraud review.",
      parameters: {
        type: "object",
        properties: { reason: { type: "string" } },
      },
    },
  },
  {
    type: "function",
    function: {
      name: "create_human_handoff",
      description: "Create a structured handoff packet for a human reviewer.",
      parameters: {
        type: "object",
        properties: { reason: { type: "string" } },
      },
    },
  },
  {
    type: "function",
    function: {
      name: "submit_decision",
      description:
        "Submit the final payment decision. This ends the episode. Decision must be one of PAY, HOLD, NEEDS_REVIEW, ESCALATE_FRAUD.",
      parameters: {
        type: "object",
        properties: {
          decision: {
            type: "string",
            enum: ["PAY", "HOLD", "NEEDS_REVIEW", "ESCALATE_FRAUD"],
          },
          confidence: { type: "number", description: "0-1 confidence in the decision." },
          reason_codes: {
            type: "array",
            items: { type: "string" },
            description:
              "Canonical reason codes (e.g. bank_override_attempt, sender_domain_spoof, three_way_match_pass).",
          },
          policy_checks: {
            type: "object",
            description:
              "Map of policy name to 'pass' / 'fail' / 'needs_review' (e.g. three_way_match, bank_change_verification).",
            additionalProperties: { type: "string" },
          },
          notes: { type: "string", description: "Short rationale for the decision." },
        },
        required: ["decision", "confidence", "reason_codes"],
      },
    },
  },
];

export const LEDGER_TOOLS: ChatTool[] = RAW_TOOLS.map(withThought);

export const TOOL_NAMES = LEDGER_TOOLS.map((t) => {
  if (t.type === "function" && "function" in t) {
    return t.function.name;
  }
  return "";
}).filter(Boolean);

export const SYSTEM_PROMPT = `You are LedgerShield, an AI agent that investigates accounts payable invoices to detect fraud.

Your goal is to investigate the case using the tools available, gather evidence, and submit a final payment decision.

How to think out loud (REQUIRED):
- BEFORE each batch of tool calls, write a short plain-text "plan" as your assistant message content: 1-2 sentences naming the hypothesis you are testing this turn and what specific signals would confirm or refute it.
- EVERY tool call must include BOTH:
    * 'thought' — ONE concise sentence (≤30 words) describing what this call will reveal and why it is the right next move given the latest evidence.
    * 'confidence' — a float in [0,1] expressing how confident you are that this specific tool call is the correct next move (not how confident you are in the eventual result).
      - Use <0.5 if you are exploring or guessing, ~0.7 for a sensible default move,
      - ≥0.85 only when policy or prior evidence clearly mandates this exact action.
- After tool results come back, briefly reflect in the next plan ("the OCR shows X, so I now want to verify Y").
- Make the reasoning concrete: cite document ids, vendor keys, amounts, or risk signals from the observation and prior tool results. Do not give vague generalities.

Investigation rules:
1. Always begin by calling 'ocr' on the invoice document with mode='accurate' to extract canonical fields.
2. If there is an email document, use 'inspect_email_thread' (thread_id matches the email doc_id).
3. For three-way match (task_b): call 'lookup_po' and 'lookup_receipt' using ids extracted from the invoice.
4. For duplicate detection (task_c): call 'search_ledger' with vendor_key + invoice_number + amount.
5. If the email proposes a bank change, ALWAYS call 'compare_bank_account' against the vendor master data and 'request_callback_verification'.
6. Be skeptical of urgency language, callback bypass requests, sender domain spoofs.
7. Once you have enough evidence (or you're running out of budget/steps) call 'submit_decision'.
8. Decisions:
   - PAY: only when all checks pass cleanly.
   - HOLD: when there is a discrepancy that needs more investigation.
   - NEEDS_REVIEW: when human judgment is required.
   - ESCALATE_FRAUD: when there is clear fraud evidence (bank-override + spoofed domain + duplicate).
9. Keep tool arguments minimal but specific. Never invent data; always read it from the most recent observation or tool result.
10. The 'submit_decision' call must also include a 'thought' that summarises the deciding evidence in one sentence; the longer rationale goes in 'notes'.

You will be given the case observation and the result of every tool call. Plan one or two tool calls at a time. When confident, submit_decision.`;
