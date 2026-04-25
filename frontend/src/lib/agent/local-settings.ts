/** Browser-only persistence for the /agent LLM form (opt-in). */

export type StoredAgentMode = "demo" | "custom";

const REMEMBER = "ledgershield:agent:remember";
const API_KEY = "ledgershield:agent:apiKey";
const API_URL = "ledgershield:agent:apiUrl";
const MODEL = "ledgershield:agent:model";
const MODE = "ledgershield:agent:mode";

function rememberEnabled(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(REMEMBER) === "1";
  } catch {
    return false;
  }
}

export function loadAgentFormFromStorage(): {
  mode: StoredAgentMode;
  apiKey: string;
  apiUrl: string;
  model: string;
} | null {
  if (typeof window === "undefined" || !rememberEnabled()) return null;
  try {
    const mode = window.localStorage.getItem(MODE) as StoredAgentMode | null;
    return {
      mode: mode === "demo" || mode === "custom" ? mode : "custom",
      apiKey: window.localStorage.getItem(API_KEY) ?? "",
      apiUrl: window.localStorage.getItem(API_URL) ?? "",
      model: window.localStorage.getItem(MODEL) ?? "",
    };
  } catch {
    return null;
  }
}

export function saveAgentFormToStorage(payload: {
  mode: StoredAgentMode;
  apiKey: string;
  apiUrl: string;
  model: string;
}): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(REMEMBER, "1");
    window.localStorage.setItem(MODE, payload.mode);
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
    window.localStorage.removeItem(MODE);
  } catch {
    /* ignore */
  }
}
