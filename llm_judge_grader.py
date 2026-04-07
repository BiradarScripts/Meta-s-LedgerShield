"""
LLM-as-Judge grading module for LedgerShield.

This module uses OpenAI models to evaluate agent reasoning quality,
create nuanced scores that separate strong from weak agents, and
provide detailed assessment of agent decision-making capabilities.

Key features:
- Reasoning quality assessment via LLM evaluation
- Agent capability comparison and ranking
- Grader calibration validation
- Detailed feedback on agent weaknesses
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from openai import OpenAI


API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "openai/gpt-4.1-mini"
HF_TOKEN = os.getenv("HF_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_KEY = HF_TOKEN or OPENAI_API_KEY or os.getenv("API_KEY")

JUDGE_TEMPERATURE = 0.0
MAX_TOKENS = 512


def get_openai_client() -> Optional[OpenAI]:
    """Initialize OpenAI client with appropriate credentials."""
    if not API_KEY:
        return None
    try:
        return OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    except Exception:
        return None


def compact_json(value: Any) -> str:
    """Create compact JSON representation."""
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True, sort_keys=True)


def normalize_text(value: Any) -> str:
    """Normalize text for comparison."""
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


class LLMGrader:
    """
    LLM-as-Judge grader that evaluates agent reasoning quality.
    
    This grader uses OpenAI models to assess:
    1. Reasoning coherence and logical flow
    2. Evidence utilization quality
    3. Decision justification strength
    4. Risk awareness and calibration
    5. Policy compliance understanding
    """
    
    def __init__(self, client: Optional[OpenAI] = None, model: str = MODEL_NAME):
        self.client = client or get_openai_client()
        self.model = model
        self.evaluation_history: list[dict[str, Any]] = []
    
    def _call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = MAX_TOKENS) -> dict[str, Any]:
        """Make LLM call and parse JSON response."""
        if not self.client:
            return {"error": "No OpenAI client available"}
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=JUDGE_TEMPERATURE,
                max_completion_tokens=max_tokens,
            )
            
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except json.JSONDecodeError:
            return {"error": "Failed to parse LLM response as JSON", "raw_response": content}
        except Exception as e:
            return {"error": f"LLM call failed: {str(e)}"}
    
    def evaluate_reasoning_quality(
        self,
        case_id: str,
        task_type: str,
        agent_trajectory: list[dict[str, Any]],
        final_decision: dict[str, Any],
        gold_standard: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Evaluate the quality of agent's reasoning process.
        
        Returns scores for:
        - logical_coherence: How well the reasoning flows
        - evidence_quality: How effectively evidence is used
        - risk_assessment: Quality of risk evaluation
        - decision_justification: Strength of decision rationale
        """
        system_prompt = """You are an expert evaluator of AI agent reasoning in financial audit tasks.
Evaluate the agent's reasoning process and provide scores in JSON format.

Scoring criteria (0.0 to 1.0):
- logical_coherence: Does the reasoning flow logically from evidence to conclusion?
- evidence_quality: Does the agent effectively identify and use relevant evidence?
- risk_assessment: Does the agent appropriately identify and weight risks?
- decision_justification: Is the final decision well-justified with evidence?

Also identify:
- key_strengths: List of what the agent did well
- key_weaknesses: List of what the agent missed or mishandled
- reasoning_gaps: Specific logical gaps in the agent's thinking

Return JSON format:
{
  "logical_coherence": float,
  "evidence_quality": float,
  "risk_assessment": float,
  "decision_justification": float,
  "overall_reasoning_score": float,
  "key_strengths": [str],
  "key_weaknesses": [str],
  "reasoning_gaps": [str]
}"""

        user_prompt = compact_json({
            "case_id": case_id,
            "task_type": task_type,
            "agent_trajectory": agent_trajectory,
            "final_decision": final_decision,
            "gold_standard": gold_standard,
        })
        
        result = self._call_llm(system_prompt, user_prompt)
        
        # Calculate overall reasoning score as weighted average
        if "overall_reasoning_score" not in result:
            result["overall_reasoning_score"] = (
                0.25 * result.get("logical_coherence", 0.5) +
                0.30 * result.get("evidence_quality", 0.5) +
                0.25 * result.get("risk_assessment", 0.5) +
                0.20 * result.get("decision_justification", 0.5)
            )
        
        self.evaluation_history.append({
            "case_id": case_id,
            "evaluation_type": "reasoning_quality",
            "result": result,
        })
        
        return result
    
    def evaluate_agent_capabilities(
        self,
        agent_results: list[dict[str, Any]],
        gold_standards: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Evaluate overall agent capabilities across multiple cases.
        
        This creates a capability profile that separates agents by:
        - Consistency across task types
        - Handling of edge cases
        - Learning from failures
        """
        system_prompt = """You are an expert evaluator comparing AI agent capabilities.
Analyze the agent's performance across multiple cases and provide a capability assessment.

Evaluate:
- task_mastery: How well agent handles each task type (A, B, C, D)
- consistency: Score variance across similar cases
- edge_case_handling: Performance on difficult/hard cases
- error_recovery: Does agent learn from mistakes?
- overall_capability: Aggregate capability score

Return JSON:
{
  "task_mastery": {"task_a": float, "task_b": float, "task_c": float, "task_d": float},
  "consistency_score": float,
  "edge_case_handling": float,
  "error_recovery": float,
  "overall_capability": float,
  "strengths": [str],
  "weaknesses": [str],
  "improvement_areas": [str]
}"""

        user_prompt = compact_json({
            "agent_results": agent_results,
            "gold_standards": gold_standards,
        })
        
        return self._call_llm(system_prompt, user_prompt, max_tokens=768)
    
    def compare_agents(
        self,
        agent_a_results: dict[str, Any],
        agent_b_results: dict[str, Any],
        gold_standards: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Compare two agents and determine which is stronger.
        
        Returns:
        - stronger_agent: "A", "B", or "tie"
        - confidence: Confidence in the assessment
        - key_differences: What separates the agents
        """
        system_prompt = """You are an expert evaluator comparing two AI agents.
Compare their performance and determine which is stronger.

Consider:
- Overall success rate and scores
- Consistency across task types
- Handling of difficult cases
- Quality of reasoning and decisions

Return JSON:
{
  "stronger_agent": "A" | "B" | "tie",
  "confidence": float (0.0-1.0),
  "score_difference": float,
  "key_differences": [str],
  "agent_a_strengths": [str],
  "agent_b_strengths": [str],
  "verdict": str (detailed explanation)
}"""

        user_prompt = compact_json({
            "agent_a": agent_a_results,
            "agent_b": agent_b_results,
            "gold_standards": gold_standards,
        })
        
        return self._call_llm(system_prompt, user_prompt, max_tokens=768)
    
    def validate_grader_signal(
        self,
        results_by_agent: dict[str, list[dict[str, Any]]],
        expected_ranking: list[str],
    ) -> dict[str, Any]:
        """
        Validate that the grader correctly separates agents by capability.
        
        This is crucial for the "bootcamp framing" - ensuring scores
        are valid signals of agent quality.
        """
        system_prompt = """You are validating an AI agent evaluation system.
Analyze whether the grading scores correctly separate agents by capability.

Evaluate:
- ranking_correlation: Do scores match expected agent ranking?
- score_separation: Is there meaningful difference between agent scores?
- consistency: Are scores consistent across similar cases?
- discriminative_power: Can the grader tell strong from weak agents?

Return JSON:
{
  "ranking_correct": bool,
  "ranking_correlation": float (Spearman-like correlation),
  "score_separation": float (avg difference between adjacent agents),
  "discriminative_power": float (0-1, how well it separates),
  "issues": [str],
  "recommendations": [str],
  "validation_passed": bool
}"""

        # Calculate basic stats
        agent_scores = {}
        for agent_id, results in results_by_agent.items():
            scores = [r.get("score", 0) for r in results]
            agent_scores[agent_id] = {
                "mean": sum(scores) / max(len(scores), 1),
                "std": self._calculate_std(scores),
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0,
            }
        
        user_prompt = compact_json({
            "agent_scores": agent_scores,
            "expected_ranking": expected_ranking,
            "raw_results": results_by_agent,
        })
        
        result = self._call_llm(system_prompt, user_prompt, max_tokens=768)
        
        # Add computed statistics
        result["computed_statistics"] = agent_scores
        
        return result
    
    def _calculate_std(self, values: list[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def generate_grading_report(
        self,
        agent_id: str,
        results: list[dict[str, Any]],
        gold_standards: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Generate a comprehensive grading report for an agent.
        
        Includes:
        - Overall performance summary
        - Per-task-type analysis
        - Reasoning quality assessment
        - Recommendations for improvement
        """
        # Get capability evaluation
        capabilities = self.evaluate_agent_capabilities(results, gold_standards)
        
        # Get reasoning quality for each case
        reasoning_scores = []
        for result in results:
            case_id = result.get("case_id", "")
            if case_id in gold_standards:
                reasoning = self.evaluate_reasoning_quality(
                    case_id=case_id,
                    task_type=result.get("task_type", ""),
                    agent_trajectory=result.get("trajectory", []),
                    final_decision=result.get("decision", {}),
                    gold_standard=gold_standards[case_id],
                )
                reasoning_scores.append(reasoning)
        
        # Aggregate reasoning scores
        if reasoning_scores:
            avg_reasoning = {
                "logical_coherence": sum(r.get("logical_coherence", 0) for r in reasoning_scores) / len(reasoning_scores),
                "evidence_quality": sum(r.get("evidence_quality", 0) for r in reasoning_scores) / len(reasoning_scores),
                "risk_assessment": sum(r.get("risk_assessment", 0) for r in reasoning_scores) / len(reasoning_scores),
                "decision_justification": sum(r.get("decision_justification", 0) for r in reasoning_scores) / len(reasoning_scores),
                "overall_reasoning": sum(r.get("overall_reasoning_score", 0) for r in reasoning_scores) / len(reasoning_scores),
            }
        else:
            avg_reasoning = {}
        
        # Calculate task-level breakdown
        task_scores: dict[str, list[float]] = {}
        for result in results:
            task_type = result.get("task_type", "unknown")
            score = result.get("score", 0)
            task_scores.setdefault(task_type, []).append(score)
        
        task_breakdown = {
            task: {
                "mean": sum(scores) / len(scores),
                "count": len(scores),
            }
            for task, scores in task_scores.items()
        }
        
        # Generate final score combining environment score and reasoning quality
        env_scores = [r.get("score", 0) for r in results]
        avg_env_score = sum(env_scores) / max(len(env_scores), 1)
        avg_reasoning_score = avg_reasoning.get("overall_reasoning", 0.5)
        
        # Combined score: 70% environment score, 30% reasoning quality
        combined_score = 0.7 * avg_env_score + 0.3 * avg_reasoning_score
        
        return {
            "agent_id": agent_id,
            "overall_score": round(combined_score, 4),
            "environment_score": round(avg_env_score, 4),
            "reasoning_score": round(avg_reasoning_score, 4),
            "task_breakdown": task_breakdown,
            "reasoning_quality": avg_reasoning,
            "capabilities": capabilities,
            "recommendations": capabilities.get("improvement_areas", []),
        }


def grade_with_llm_judge(
    case_id: str,
    task_type: str,
    agent_trajectory: list[dict[str, Any]],
    final_decision: dict[str, Any],
    gold_standard: dict[str, Any],
    client: Optional[OpenAI] = None,
) -> dict[str, Any]:
    """
    Convenience function to grade a single case with LLM judge.
    
    Returns detailed evaluation including reasoning quality scores.
    """
    grader = LLMGrader(client=client)
    
    reasoning_eval = grader.evaluate_reasoning_quality(
        case_id=case_id,
        task_type=task_type,
        agent_trajectory=agent_trajectory,
        final_decision=final_decision,
        gold_standard=gold_standard,
    )
    
    return {
        "case_id": case_id,
        "task_type": task_type,
        "reasoning_evaluation": reasoning_eval,
        "overall_quality_score": reasoning_eval.get("overall_reasoning_score", 0.5),
    }


def compare_agent_strengths(
    agent_results: dict[str, list[dict[str, Any]]],
    gold_standards: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    Compare multiple agents and rank them by capability.
    
    This is the key function for validating that the grading system
    can separate strong from weak agents.
    """
    grader = LLMGrader()
    
    # Generate reports for each agent
    agent_reports = {}
    for agent_id, results in agent_results.items():
        report = grader.generate_grading_report(agent_id, results, gold_standards)
        agent_reports[agent_id] = report
    
    # Rank agents by combined score
    ranked_agents = sorted(
        agent_reports.items(),
        key=lambda x: x[1]["overall_score"],
        reverse=True,
    )
    
    # Calculate score separation
    scores = [report["overall_score"] for _, report in ranked_agents]
    if len(scores) >= 2:
        separations = [scores[i] - scores[i+1] for i in range(len(scores)-1)]
        avg_separation = sum(separations) / len(separations)
    else:
        avg_separation = 0
    
    return {
        "ranked_agents": [
            {
                "rank": i + 1,
                "agent_id": agent_id,
                "overall_score": report["overall_score"],
                "environment_score": report["environment_score"],
                "reasoning_score": report["reasoning_score"],
            }
            for i, (agent_id, report) in enumerate(ranked_agents)
        ],
        "score_separation": round(avg_separation, 4),
        "agent_reports": agent_reports,
    }


if __name__ == "__main__":
    # Example usage and self-test
    print("LLM Judge Grader Module")
    print("=" * 60)
    
    # Check if OpenAI client can be initialized
    client = get_openai_client()
    if client:
        print("✓ OpenAI client initialized successfully")
        print(f"  Model: {MODEL_NAME}")
        print(f"  API Base: {API_BASE_URL}")
    else:
        print("✗ OpenAI client initialization failed")
        print("  Set HF_TOKEN or OPENAI_API_KEY environment variable")
        
    print("\nExample grading functions available:")
    print("  - LLMGrader.evaluate_reasoning_quality()")
    print("  - LLMGrader.evaluate_agent_capabilities()")
    print("  - LLMGrader.compare_agents()")
    print("  - LLMGrader.validate_grader_signal()")
    print("  - compare_agent_strengths()")
