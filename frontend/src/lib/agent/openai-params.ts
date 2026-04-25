/**
 * Newer OpenAI chat models reject `max_tokens` and require `max_completion_tokens`.
 * @see https://platform.openai.com/docs/api-reference/chat/create
 */
export function chatCompletionOutputTokenParam(
  model: string,
  tokens: number,
): { max_tokens: number } | { max_completion_tokens: number } {
  const m = model.trim().toLowerCase();
  if (
    m.startsWith("gpt-5") ||
    m.startsWith("o") ||
    m.startsWith("chatgpt-4o-latest")
  ) {
    return { max_completion_tokens: tokens };
  }
  return { max_tokens: tokens };
}

/** GPT-5 / o-series (and similar) only allow the API default temperature — omit the parameter. */
export function modelUsesDefaultTemperatureOnly(model: string): boolean {
  const m = model.trim().toLowerCase();
  return (
    m.startsWith("gpt-5") ||
    m.startsWith("o") ||
    m.startsWith("chatgpt-4o-latest")
  );
}

export function chatCompletionTemperatureFields(
  model: string,
  temperature: number | undefined,
): { temperature: number } | Record<string, never> {
  if (modelUsesDefaultTemperatureOnly(model)) {
    return {};
  }
  return { temperature: temperature ?? 0 };
}
