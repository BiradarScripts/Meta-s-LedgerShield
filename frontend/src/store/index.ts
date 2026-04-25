"use client";

import { create } from "zustand";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

export interface Case {
  case_id: string;
  task_type: string;
  instruction: string;
  task_label?: string;
  difficulty?: string;
  benchmark_split?: string;
}

export interface Observation {
  case_id: string;
  task_type: string;
  instruction: string;
  visible_documents: any[];
  revealed_artifacts: any[];
  pending_events: any[];
  budget_remaining: number;
  budget_total: number;
  step_count: number;
  case_clock: number;
  risk_snapshot: {
    observed_risk_signals: string[];
  };
  last_tool_result?: any;
  messages: string[];
  allowed_actions: string[];
  available_interventions: string[];
  case_metadata: {
    task_label?: string;
    benchmark_track?: string;
    benchmark_track_label?: string;
  };
  portfolio_context?: any;
  sprt_state?: {
    posterior_probabilities: Record<string, number>;
    recommended_decision: string;
    optimal_stopping_reached: boolean;
  };
  tool_rankings?: {
    recommended_tool: string;
    voi: number;
    cost: number;
    should_stop: boolean;
  };
  reward_machine?: any;
}

export interface StepResult {
  observation: Observation;
  reward: number;
  done: boolean;
  truncated: boolean;
  terminated: boolean;
  info: {
    reward_model?: {
      value: number;
      terminal: boolean;
      components?: Record<string, number>;
    };
    final_score?: number;
    score_breakdown?: any;
    outcome?: any;
  };
}

interface AppState {
  // Connection
  apiUrl: string;
  setApiUrl: (url: string) => void;
  
  // Current episode
  currentCaseId: string | null;
  setCurrentCaseId: (id: string | null) => void;
  
  // Observation state
  observation: Observation | null;
  setObservation: (obs: Observation | null) => void;
  
  // Step results history
  stepHistory: StepResult[];
  addStepResult: (result: StepResult) => void;
  clearHistory: () => void;
  
  // Loading states
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  isSubmitting: boolean;
  setIsSubmitting: (submitting: boolean) => void;
  
  // Error state
  error: string | null;
  setError: (error: string | null) => void;
  
  // Available cases
  availableCases: Case[];
  setAvailableCases: (cases: Case[]) => void;
  
  // Institutional memory
  institutionalMemory: any;
  setInstitutionalMemory: (memory: any) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Connection
  apiUrl: "http://localhost:8000",
  setApiUrl: (apiUrl) => set({ apiUrl }),
  
  // Current episode
  currentCaseId: null,
  setCurrentCaseId: (currentCaseId) => set({ currentCaseId }),
  
  // Observation state
  observation: null,
  setObservation: (observation) => set({ observation }),
  
  // Step results history
  stepHistory: [],
  addStepResult: (result) => set((state) => ({ 
    stepHistory: [...state.stepHistory, result] 
  })),
  clearHistory: () => set({ stepHistory: [] }),
  
  // Loading states
  isLoading: false,
  setIsLoading: (isLoading) => set({ isLoading }),
  isSubmitting: false,
  setIsSubmitting: (isSubmitting) => set({ isSubmitting }),
  
  // Error state
  error: null,
  setError: (error) => set({ error }),
  
  // Available cases
  availableCases: [],
  setAvailableCases: (availableCases) => set({ availableCases }),
  
  // Institutional memory
  institutionalMemory: null,
  setInstitutionalMemory: (institutionalMemory) => set({ institutionalMemory }),
}));