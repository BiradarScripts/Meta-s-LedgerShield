/** Browser-only persistence for the /agent LLM form (opt-in). */

const REMEMBER = "ledgershield:agent:remember";
const API_KEY = "ledgershield:agent:apiKey";
const API_URL = "ledgershield:agent:apiUrl";
const MODEL = "ledgershield:agent:model";

function rememberEnabled(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(REMEMBER) === "1";
  } catch {
    return false;
  }
}

export function loadAgentFormFromStorage(): {
  apiKey: string;
  apiUrl: string;
  model: string;
} | null {
  if (typeof window === "undefined" || !rememberEnabled()) return null;
  try {
    return {
      apiKey: window.localStorage.getItem(API_KEY) ?? "",
      apiUrl: window.localStorage.getItem(API_URL) ?? "",
      model: window.localStorage.getItem(MODEL) ?? "",
    };
  } catch {
    return null;
  }
}

export function saveAgentFormToStorage(payload: {
  apiKey: string;
  apiUrl: string;
  model: string;
}): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(REMEMBER, "1");
    window.localStorage.setItem(API_KEY, payload.apiKey);
    window.localStorage.setItem(API_URL, payload.apiUrl);
    window.localStorage.setItem(MODEL, payload.model);
  } catch {
    /* quota / private mode */
  }
}

export function clearAgentFormStorage(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(REMEMBER);
    window.localStorage.removeItem(API_KEY);
    window.localStorage.removeItem(API_URL);
    window.localStorage.removeItem(MODEL);
  } catch {
    /* ignore */
  }
}
