export type StepPayload = {
  action_type: string;
  payload?: Record<string, unknown>;
};

export type StepResponse = {
  observation: Record<string, unknown>;
  reward: number;
  done: boolean;
  truncated?: boolean;
  terminated?: boolean;
  info?: Record<string, unknown>;
};

const BACKEND_URL =
  process.env.LEDGERSHIELD_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

export async function envReset(caseId: string): Promise<StepResponse> {
  const response = await fetch(`${BACKEND_URL}/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ case_id: caseId }),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`reset failed (${response.status}): ${text}`);
  }
  return (await response.json()) as StepResponse;
}

export async function envStep(action: StepPayload): Promise<StepResponse> {
  const response = await fetch(`${BACKEND_URL}/step`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(action),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`step failed (${response.status}): ${text}`);
  }
  return (await response.json()) as StepResponse;
}

export async function envHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${BACKEND_URL}/health`, { cache: "no-store" });
    return response.ok;
  } catch {
    return false;
  }
}

export function getBackendUrl(): string {
  return BACKEND_URL;
}
