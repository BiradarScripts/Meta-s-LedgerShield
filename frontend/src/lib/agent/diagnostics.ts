export type StepMath = {
  reward_model?: {
    value: number;
    terminal: boolean;
    components: Record<string, number>;
    metadata: Record<string, unknown>;
  };
  rl_plane?: {
    reward: number;
    terminal: boolean;
    truncated?: boolean;
    state_dim: number;
    preview: number[];
    best_tool_voi: number | null;
    watchdog: number | null;
    calibration: number | null;
  };
};

const META_KEYS = [
  "action_type",
  "observation_key",
  "novel_signal_count",
  "success",
  "terminal_reason",
  "control_boundary_phase",
  "intervention",
  "watchdog_verdict",
] as const;

/** Aligns with server/rl_export.py export_state_vector layout (length typically 37). */
const STATE_VEC_IDX = {
  best_tool_voi: 25,
  watchdog: 35,
  calibration: 36,
} as const;

export function extractStepMath(
  info: Record<string, unknown> | undefined,
): StepMath | undefined {
  if (!info || typeof info !== "object") return undefined;

  const out: StepMath = {};

  const rm = info.reward_model;
  if (rm && typeof rm === "object") {
    const r = rm as Record<string, unknown>;
    const comp = r.components;
    const components: Record<string, number> = {};
    if (comp && typeof comp === "object") {
      for (const [k, v] of Object.entries(comp as Record<string, unknown>)) {
        if (typeof v === "number" && Number.isFinite(v)) components[k] = v;
      }
    }
    const meta = r.metadata;
    const metadata: Record<string, unknown> = {};
    if (meta && typeof meta === "object") {
      const mo = meta as Record<string, unknown>;
      for (const k of META_KEYS) {
        if (k in mo) metadata[k] = mo[k];
      }
    }
    out.reward_model = {
      value: typeof r.value === "number" ? r.value : 0,
      terminal: Boolean(r.terminal),
      components,
      metadata,
    };
  }

  const rlp = info.rl_data_plane;
  if (rlp && typeof rlp === "object") {
    const p = rlp as Record<string, unknown>;
    const sv = p.state_vector;
    const arr = Array.isArray(sv)
      ? (sv as unknown[]).filter((x): x is number => typeof x === "number")
      : [];
    const n = arr.length;
    out.rl_plane = {
      reward: typeof p.reward === "number" ? p.reward : 0,
      terminal: Boolean(p.terminal),
      truncated:
        typeof p.truncated === "boolean" ? p.truncated : undefined,
      state_dim: n,
      preview: arr.slice(0, 8),
      best_tool_voi:
        n > STATE_VEC_IDX.best_tool_voi
          ? arr[STATE_VEC_IDX.best_tool_voi]!
          : null,
      watchdog:
        n > STATE_VEC_IDX.watchdog ? arr[STATE_VEC_IDX.watchdog]! : null,
      calibration:
        n > STATE_VEC_IDX.calibration ? arr[STATE_VEC_IDX.calibration]! : null,
    };
  }

  return out.reward_model || out.rl_plane ? out : undefined;
}
