import { NextRequest, NextResponse } from "next/server";
import OpenAI from "openai";

import { envHealth, getBackendUrl } from "@/lib/agent/env-client";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type HealthBody = {
  apiKey?: string;
  baseUrl?: string;
  model?: string;
};

const DEFAULT_BASE_URL = "https://api.openai.com/v1";

export async function POST(request: NextRequest) {
  const backendUrl = getBackendUrl();
  const backendOk = await envHealth();

  let body: HealthBody = {};
  try {
    body = (await request.json()) as HealthBody;
  } catch {
    return NextResponse.json(
      {
        ok: false,
        backend: { url: backendUrl, ok: backendOk },
        llm: { ok: false, error: "Invalid JSON body" },
      },
      { status: 400 },
    );
  }

  const apiKey = (body.apiKey || "").trim();
  const baseUrl = (body.baseUrl || DEFAULT_BASE_URL).trim().replace(/\/+$/, "");
  const model = (body.model || "").trim();

  if (!apiKey || !model) {
    return NextResponse.json(
      {
        ok: false,
        backend: { url: backendUrl, ok: backendOk },
        llm: {
          ok: false,
          error: !apiKey ? "API key is required" : "Model is required",
        },
      },
      { status: 400 },
    );
  }

  const client = new OpenAI({ apiKey, baseURL: baseUrl });
  const start = Date.now();

  try {
    const response = await client.chat.completions.create({
      model,
      messages: [
        { role: "system", content: "Respond with the single word: ok" },
        { role: "user", content: "ping" },
      ],
      max_tokens: 4,
      temperature: 0,
    });

    const latencyMs = Date.now() - start;
    const reply = response.choices?.[0]?.message?.content?.trim() || "";

    return NextResponse.json({
      ok: true,
      backend: { url: backendUrl, ok: backendOk },
      llm: {
        ok: true,
        provider: baseUrl,
        model: response.model || model,
        latency_ms: latencyMs,
        sample_reply: reply.slice(0, 80),
      },
    });
  } catch (err) {
    const error = err as { status?: number; message?: string; code?: string };
    const status = error.status || 502;
    const message =
      error.message || error.code || "LLM connection check failed";
    return NextResponse.json(
      {
        ok: false,
        backend: { url: backendUrl, ok: backendOk },
        llm: {
          ok: false,
          status,
          error: message,
        },
      },
      { status: 200 },
    );
  }
}
