"use client";

import { useState } from "react";
import { useAppStore, Observation, StepResult, Case } from "@/store";

const AVAILABLE_CASES: Case[] = [
  { case_id: "CASE-A-001", task_type: "task_a", instruction: "Extract invoice fields from document" },
  { case_id: "CASE-A-002", task_type: "task_a", instruction: "Extract invoice fields from document" },
  { case_id: "CASE-A-003", task_type: "task_a", instruction: "Extract invoice fields from document" },
  { case_id: "CASE-A-004", task_type: "task_a", instruction: "Extract invoice fields from document" },
  { case_id: "CASE-B-001", task_type: "task_b", instruction: "Verify three-way match (Invoice, PO, Receipt)" },
  { case_id: "CASE-B-002", task_type: "task_b", instruction: "Verify three-way match (Invoice, PO, Receipt)" },
  { case_id: "CASE-B-003", task_type: "task_b", instruction: "Verify three-way match (Invoice, PO, Receipt)" },
  { case_id: "CASE-B-004", task_type: "task_b", instruction: "Verify three-way match (Invoice, PO, Receipt)" },
  { case_id: "CASE-B-005", task_type: "task_b", instruction: "Verify three-way match (Invoice, PO, Receipt)" },
  { case_id: "CASE-C-001", task_type: "task_c", instruction: "Detect duplicate invoice and verify bank account" },
  { case_id: "CASE-C-002", task_type: "task_c", instruction: "Detect duplicate invoice and verify bank account" },
  { case_id: "CASE-C-003", task_type: "task_c", instruction: "Detect duplicate invoice and verify bank account" },
  { case_id: "CASE-C-004", task_type: "task_c", instruction: "Detect duplicate invoice and verify bank account" },
  { case_id: "CASE-D-001", task_type: "task_d", instruction: "Full fraud investigation with email, vendor, bank, callback" },
  { case_id: "CASE-D-002", task_type: "task_d", instruction: "Full fraud investigation with email, vendor, bank, callback" },
  { case_id: "CASE-D-003", task_type: "task_d", instruction: "Full fraud investigation with email, vendor, bank, callback" },
  { case_id: "CASE-D-004", task_type: "task_d", instruction: "Full fraud investigation with email, vendor, bank, callback" },
  { case_id: "CASE-D-005", task_type: "task_d", instruction: "Full fraud investigation with email, vendor, bank, callback" },
  { case_id: "CASE-D-006", task_type: "task_d", instruction: "Full fraud investigation with email, vendor, bank, callback" },
  { case_id: "CASE-E-001", task_type: "task_e", instruction: "Campaign-level coordinated fraud detection" },
  { case_id: "CASE-E-002", task_type: "task_e", instruction: "Campaign-level coordinated fraud detection" },
];

const DEFAULT_CASES: Case[] = AVAILABLE_CASES;

export function useLedgerApi() {
  const { 
    apiUrl, 
    currentCaseId, 
    observation, 
    stepHistory,
    isLoading, 
    isSubmitting, 
    error,
    setCurrentCaseId,
    setObservation,
    addStepResult,
    clearHistory,
    setIsLoading,
    setIsSubmitting,
    setError,
  } = useAppStore();

  const reset = async (caseId: string) => {
    setIsLoading(true);
    setError(null);
    clearHistory();
    
    try {
      const response = await fetch(`${apiUrl}/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case_id: caseId }),
      });
      
      if (!response.ok) throw new Error(`Reset failed: ${response.status}`);
      
      const data = await response.json();
      const obs = data.observation as Observation;
      const result: StepResult = {
        observation: obs,
        reward: data.reward || 0,
        done: data.done || false,
        truncated: data.truncated || false,
        terminated: data.terminated || false,
        info: data.info || {},
      };
      
      setCurrentCaseId(caseId);
      setObservation(obs);
      addStepResult(result);
      
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const step = async (action: { action_type: string; payload?: Record<string, any> }) => {
    if (!currentCaseId) throw new Error("No active case. Call reset() first.");
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${apiUrl}/step`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(action),
      });
      
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`Step failed: ${response.status} - ${text}`);
      }
      
      const data = await response.json();
      const obs = data.observation as Observation;
      const result: StepResult = {
        observation: obs,
        reward: data.reward || 0,
        done: data.done || false,
        truncated: data.truncated || false,
        terminated: data.terminated || false,
        info: data.info || {},
      };
      
      setObservation(obs);
      addStepResult(result);
      
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const submitDecision = async (decision: string, confidence: number, reasonCodes: string[], policyChecks: Record<string, string>, evidenceMap: Record<string, any>) => {
    setIsSubmitting(true);
    setError(null);
    
    try {
      const response = await fetch(`${apiUrl}/step`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action_type: "submit_decision",
          payload: {
            decision,
            confidence,
            reason_codes: reasonCodes,
            policy_checks: policyChecks,
            evidence_map: evidenceMap,
          },
        }),
      });
      
      if (!response.ok) throw new Error(`Submit failed: ${response.status}`);
      
      const data = await response.json();
      const obs = data.observation as Observation;
      const result: StepResult = {
        observation: obs,
        reward: data.reward || 0,
        done: data.done || true,
        truncated: data.truncated || false,
        terminated: data.terminated || true,
        info: data.info || {},
      };
      
      setObservation(obs);
      addStepResult(result);
      
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(msg);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  };

  const fetchInstitutionalMemory = async () => {
    try {
      const response = await fetch(`${apiUrl}/institutional-memory`);
      if (!response.ok) return null;
      return await response.json();
    } catch {
      return null;
    }
  };

  return {
    reset,
    step,
    submitDecision,
    fetchInstitutionalMemory,
    currentCaseId,
    observation,
    stepHistory,
    isLoading,
    isSubmitting,
    error,
    availableCases: DEFAULT_CASES,
  };
}