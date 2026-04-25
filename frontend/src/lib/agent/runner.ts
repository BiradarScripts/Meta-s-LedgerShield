import OpenAI from "openai";
import type {
  ChatCompletionMessageParam,
  ChatCompletionMessageToolCall,
} from "openai/resources/chat/completions";

import { envReset, envStep, type StepResponse } from "./env-client";
import { extractStepMath, type StepMath } from "./diagnostics";
import { LEDGER_TOOLS, SYSTEM_PROMPT, TOOL_NAMES } from "./tools";
import { chatCompletionTemperatureFields } from "./openai-params";

export type AgentRunEvent =
  | { type: "status"; content: string }
  | { type: "observation"; observation: Record<string, unknown> }
  | {
      type: "env_state";
      observation: Record<string, unknown>;
      cumulative_reward: number;
      step_reward?: number;
      step_math?: StepMath;
    }
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

export type AgentRunConfig = {
  caseId: string;
  apiKey: string;
  baseUrl?: string;
  model: string;
  maxIterations?: number;
  temperature?: number;
};

const DEFAULT_BASE_URL = "https://api.openai.com/v1";

type Obs = Record<string, unknown>;

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function asString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function summarizeObservation(obs: Obs): string {
  const docs = asArray(obs.visible_documents)
    .map((d) => {
      const doc = (d as Record<string, unknown>) || {};
      return `${asString(doc.doc_id)} (${asString(doc.doc_type)})`;
    })
    .join(", ");
  const allowed = asArray(obs.allowed_actions).join(", ");
  const interventions = asArray(obs.available_interventions).join(", ");
  const risk = (obs.risk_snapshot as Obs | undefined) || {};
  const signals = asArray(risk.observed_risk_signals);
  const budgetRemaining = asNumber(obs.budget_remaining);
  const budgetTotal = asNumber(obs.budget_total);

  return [
    `case_id: ${asString(obs.case_id)}`,
    `task_type: ${asString(obs.task_type)}`,
    `instruction: ${asString(obs.instruction)}`,
    `step: ${asNumber(obs.step_count) ?? 0}/${asNumber(obs.max_steps) ?? 0}`,
    `budget: ${budgetRemaining?.toFixed(2) ?? "?"} / ${budgetTotal?.toFixed(2) ?? "?"}`,
    `visible_documents: ${docs || "(none)"}`,
    signals.length ? `observed_risk_signals: ${signals.join(", ")}` : null,
    `allowed_actions: ${allowed}`,
    interventions ? `available_interventions: ${interventions}` : null,
  ]
    .filter(Boolean)
    .join("\n");
}

function summarizeToolResult(payload: Record<string, unknown> | undefined): Record<string, unknown> {
  if (!payload) return {};
  const cleaned: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(payload)) {
    if (k === "tokens" && Array.isArray(v) && v.length > 12) {
      cleaned[k] = `[${v.length} tokens omitted]`;
      continue;
    }
    if (typeof v === "string" && v.length > 800) {
      cleaned[k] = v.slice(0, 800) + "...";
      continue;
    }
    cleaned[k] = v;
  }
  return cleaned;
}

function safeParseJson(text: string | null | undefined): Record<string, unknown> {
  if (!text) return {};
  try {
    const parsed = JSON.parse(text);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

export async function* runAgent(
  config: AgentRunConfig,
): AsyncGenerator<AgentRunEvent, void, void> {
  const baseURL = (config.baseUrl || DEFAULT_BASE_URL).replace(/\/+$/, "");
  const maxIterations = config.maxIterations ?? 16;

  yield { type: "status", content: `Resetting environment with ${config.caseId}` };

  let resetResult: StepResponse;
  try {
    resetResult = await envReset(config.caseId);
  } catch (err) {
    yield {
      type: "error",
      error: `Failed to reset environment: ${(err as Error).message}`,
    };
    yield { type: "done" };
    return;
  }

  yield { type: "observation", observation: resetResult.observation };
  yield {
    type: "status",
    content: `Loaded case ${resetResult.observation.case_id} (${resetResult.observation.task_type})`,
  };

  const client = new OpenAI({
    apiKey: config.apiKey,
    baseURL,
  });

  const messages: ChatCompletionMessageParam[] = [
    { role: "system", content: SYSTEM_PROMPT },
    {
      role: "user",
      content: `Initial observation:\n\n${summarizeObservation(resetResult.observation)}\n\nBegin investigation.`,
    },
  ];

  let lastObservation = resetResult.observation;
  let lastStepResponse: StepResponse | null = null;
  let submitted = false;
  let cumulativeReward = 0;

  yield {
    type: "env_state",
    observation: resetResult.observation as Record<string, unknown>,
    cumulative_reward: 0,
    step_math: extractStepMath(
      resetResult.info as Record<string, unknown> | undefined,
    ),
  };

  for (let iter = 0; iter < maxIterations && !submitted; iter++) {
    yield { type: "status", content: `LLM thinking (iteration ${iter + 1})...` };

    let completion;
    try {
      completion = await client.chat.completions.create({
        model: config.model,
        ...chatCompletionTemperatureFields(config.model, config.temperature),
        messages,
        tools: LEDGER_TOOLS,
        tool_choice: "auto",
      });
    } catch (err) {
      yield {
        type: "error",
        error: `LLM call failed: ${(err as Error).message}`,
      };
      yield { type: "done" };
      return;
    }

    const choice = completion.choices?.[0];
    const message = choice?.message;
    if (!message) {
      yield { type: "error", error: "LLM returned no message." };
      yield { type: "done" };
      return;
    }

    if (message.content && message.content.trim()) {
      yield { type: "thinking", content: message.content.trim() };
    }

    const toolCalls: ChatCompletionMessageToolCall[] = (message.tool_calls ||
      []) as ChatCompletionMessageToolCall[];

    if (!toolCalls.length) {
      messages.push({
        role: "assistant",
        content: message.content || "",
      });
      messages.push({
        role: "user",
        content:
          "You must continue by calling a tool. Pick the next best tool to advance the investigation, or call submit_decision if you have enough evidence. Remember to write a 1-2 sentence plan before the call and to include a 'thought' inside the tool arguments.",
      });
      continue;
    }

    messages.push({
      role: "assistant",
      content: message.content || "",
      tool_calls: toolCalls,
    });

    for (const call of toolCalls) {
      if (call.type !== "function") continue;
      const name = call.function.name;
      const rawArgs = safeParseJson(call.function.arguments);
      const thought =
        typeof rawArgs.thought === "string" ? rawArgs.thought.trim() : "";
      const confidenceRaw = rawArgs.confidence;
      const confidence =
        typeof confidenceRaw === "number" && Number.isFinite(confidenceRaw)
          ? Math.min(1, Math.max(0, confidenceRaw))
          : undefined;
      const args: Record<string, unknown> = { ...rawArgs };
      delete args.thought;
      delete args.confidence;

      if (!TOOL_NAMES.includes(name)) {
        yield {
          type: "tool_result",
          id: call.id,
          name,
          output: { error: `Unknown tool: ${name}` },
        };
        messages.push({
          role: "tool",
          tool_call_id: call.id,
          content: JSON.stringify({ error: `Unknown tool: ${name}` }),
        });
        continue;
      }

      if (thought) {
        yield { type: "thinking", content: thought };
      }

      yield {
        type: "tool_use",
        id: call.id,
        name,
        input: args,
        confidence,
      };

      let stepResponse: StepResponse;
      try {
        const action_type =
          name === "submit_decision" ? "submit_decision" : name;
        const payload =
          name === "submit_decision"
            ? buildSubmitPayload(args, lastObservation)
            : args;
        stepResponse = await envStep({ action_type, payload });
      } catch (err) {
        const errMsg = (err as Error).message;
        yield {
          type: "tool_result",
          id: call.id,
          name,
          output: { error: errMsg },
        };
        messages.push({
          role: "tool",
          tool_call_id: call.id,
          content: JSON.stringify({ error: errMsg }),
        });
        continue;
      }

      lastObservation = stepResponse.observation;
      lastStepResponse = stepResponse;
      const obsRecord = stepResponse.observation as Record<string, unknown>;
      const lastToolResult =
        (obsRecord?.last_tool_result as Record<string, unknown>) || {};
      const summarized = summarizeToolResult(lastToolResult);

      yield {
        type: "tool_result",
        id: call.id,
        name,
        output: summarized,
        reward: stepResponse.reward,
        done: stepResponse.done,
      };

      cumulativeReward += stepResponse.reward;
      yield {
        type: "env_state",
        observation: stepResponse.observation as Record<string, unknown>,
        cumulative_reward: cumulativeReward,
        step_reward: stepResponse.reward,
        step_math: extractStepMath(
          stepResponse.info as Record<string, unknown> | undefined,
        ),
      };

      messages.push({
        role: "tool",
        tool_call_id: call.id,
        content: JSON.stringify({
          tool_result: summarized,
          reward: stepResponse.reward,
          done: stepResponse.done,
          observation_summary: summarizeObservation(stepResponse.observation),
        }).slice(0, 6000),
      });

      if (name === "submit_decision") {
        submitted = true;
        yield {
          type: "decision",
          decision: String(args.decision || ""),
          confidence: Number(args.confidence ?? 0),
          reason_codes: Array.isArray(args.reason_codes)
            ? (args.reason_codes as string[])
            : [],
          policy_checks: (args.policy_checks as Record<string, string>) || {},
          notes: typeof args.notes === "string" ? args.notes : undefined,
        };
        break;
      }

      if (stepResponse.done) {
        submitted = true;
        break;
      }
    }
  }

  if (!submitted) {
    yield {
      type: "status",
      content: "Max iterations reached without a decision; submitting NEEDS_REVIEW.",
    };
    try {
      lastStepResponse = await envStep({
        action_type: "submit_decision",
        payload: buildSubmitPayload(
          {
            decision: "NEEDS_REVIEW",
            confidence: 0.4,
            reason_codes: ["max_iterations_reached"],
            policy_checks: {},
            notes: "Agent ran out of iterations.",
          },
          lastObservation,
        ),
      });
      lastObservation = lastStepResponse.observation;
      cumulativeReward += lastStepResponse.reward;
      yield {
        type: "env_state",
        observation: lastStepResponse.observation as Record<string, unknown>,
        cumulative_reward: cumulativeReward,
        step_reward: lastStepResponse.reward,
        step_math: extractStepMath(
          lastStepResponse.info as Record<string, unknown> | undefined,
        ),
      };
    } catch (err) {
      yield {
        type: "error",
        error: `Forced submit failed: ${(err as Error).message}`,
      };
      yield { type: "done" };
      return;
    }
  }

  const info = (lastStepResponse?.info || {}) as Record<string, unknown>;
  const finalScoreRaw = info.final_score;
  const finalScore =
    typeof finalScoreRaw === "number"
      ? finalScoreRaw
      : (lastStepResponse?.reward ?? 0);

  const lastObsRecord = lastObservation as Record<string, unknown>;
  const lastToolBlock =
    (lastObsRecord?.last_tool_result as Record<string, unknown>) || {};
  const trustGraphRaw = lastToolBlock.trust_graph;
  const trust_graph =
    trustGraphRaw && typeof trustGraphRaw === "object"
      ? (trustGraphRaw as Record<string, unknown>)
      : undefined;

  yield {
    type: "result",
    final_score: finalScore,
    reward: lastStepResponse?.reward || 0,
    info,
    observation: lastObservation,
    trust_graph,
  };
  yield { type: "done" };
}

function buildSubmitPayload(
  args: Record<string, unknown>,
  observation: Record<string, unknown>,
): Record<string, unknown> {
  const decision = String(args.decision || "NEEDS_REVIEW");
  const confidence = Number(args.confidence ?? 0.5);
  const reason_codes = Array.isArray(args.reason_codes)
    ? (args.reason_codes as string[])
    : [];
  const policy_checks = (args.policy_checks as Record<string, string>) || {};
  const notes = typeof args.notes === "string" ? (args.notes as string) : "";

  return {
    decision,
    confidence,
    reason_codes,
    policy_checks,
    evidence_map: {},
    notes,
    case_id: typeof observation?.case_id === "string" ? observation.case_id : "",
  };
}
