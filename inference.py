"""
Inference Script - LedgerShield
===================================
OpenEnv Accounts Payable Audit Environment

MANDATORY:
- Before submitting, ensure the following variables are defined in your environment configuration:
    API_BASE_URL   The API endpoint for the LLM (e.g., https://router.huggingface.co/v1)
    MODEL_NAME     The model identifier to use for inference
    HF_TOKEN       Your Hugging Face / API key
    
- The inference script must be named `inference.py` and placed in the root directory of the project
- Participants must use OpenAI Client for all LLM calls using above variables

Environment: LedgerShield - A multimodal accounts payable audit environment
Tasks: task_a (field extraction), task_b (discrepancy detection), 
       task_c (duplicate/fraud detection), task_d (policy compliance)
"""

import os
import json
from typing import Optional

from openai import OpenAI

from envs.ledgershield_env import LedgerShieldEnv, LedgerShieldAction


API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN", os.getenv("API_KEY", ""))

MAX_STEPS = 20
TEMPERATURE = 0.2
MAX_TOKENS = 200

ALLOWED_TOOLS = [
    "zoom", "get_doc_crop", "ocr", "lookup_vendor", "lookup_vendor_history",
    "lookup_policy", "lookup_po", "lookup_receipt", "search_ledger",
    "inspect_email_thread", "compare_bank_account", "submit_decision"
]

DECISIONS = ["PAY", "HOLD", "NEEDS_REVIEW", "ESCALATE_FRAUD"]


def get_llm_response(
    client: OpenAI,
    instruction: str,
    visible_docs: list,
    messages_history: list,
    budget: float,
    step_count: int
) -> str:
    docs_summary = []
    for doc in visible_docs:
        docs_summary.append(f"- {doc['doc_id']} ({doc['doc_type']}): page_count={doc.get('page_count', 1)}")
    
    prompt = f"""You are auditing invoices in an accounts payable environment.

Current State:
- Step: {step_count}/{MAX_STEPS}
- Budget remaining: {budget:.2f}

Available documents:
{chr(10).join(docs_summary)}

Available tools: {', '.join(ALLOWED_TOOLS)}
When done, use submit_decision with one of: {', '.join(DECISIONS)}

{instruction}

Conversation history:
{chr(10).join(messages_history) if messages_history else "No previous actions."}

What would you like to do? Respond with a JSON object containing 'action_type' and 'payload'.
Example: {{"action_type": "lookup_vendor", "payload": {{"vendor_key": "acme-corp"}}}}
Example: {{"action_type": "submit_decision", "payload": {{"decision": "PAY"}}}}
"""
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a helpful accounts payable audit assistant. Always respond with valid JSON containing 'action_type' and 'payload' fields."},
            {"role": "user", "content": prompt}
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS
    )
    
    return response.choices[0].message.content


def parse_action(response: str) -> Optional[LedgerShieldAction]:
    try:
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        
        action_data = json.loads(response)
        action_type = action_data.get("action_type", "")
        payload = action_data.get("payload", {})
        
        if action_type == "submit_decision":
            return LedgerShieldAction(action_type="submit_decision", payload=payload)
        
        tool_aliases = {
            "lookup_vendor_info": "lookup_vendor",
            "get_document_crop": "get_doc_crop",
            "inspect_email": "inspect_email_thread",
            "compare_bank": "compare_bank_account",
        }
        action_type = tool_aliases.get(action_type, action_type)
        
        if action_type in ALLOWED_TOOLS:
            return LedgerShieldAction(action_type=action_type, payload=payload)
        
        return LedgerShieldAction(
            action_type="submit_decision", 
            payload={"decision": "NEEDS_REVIEW", "notes": f"Parse error: {response[:50]}"}
        )
        
    except (json.JSONDecodeError, KeyError):
        return LedgerShieldAction(
            action_type="submit_decision", 
            payload={"decision": "NEEDS_REVIEW", "notes": f"Parse error: {response[:50]}"}
        )


def run_episode(
    client: OpenAI,
    env: LedgerShieldEnv,
    case_id: Optional[str] = None,
    verbose: bool = True
) -> dict:
    reset_result = env.reset(case_id=case_id)
    task_type = reset_result.observation.task_type
    instruction = reset_result.observation.instruction
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Starting Episode: {reset_result.observation.case_id}")
        print(f"Task Type: {task_type}")
        print(f"Instruction: {instruction[:80]}...")
        print(f"{'='*60}")
    
    messages_history = []
    total_reward = 0.0
    steps = 0
    
    while steps < MAX_STEPS:
        try:
            response_text = get_llm_response(
                client=client,
                instruction=instruction,
                visible_docs=reset_result.observation.visible_documents,
                messages_history=messages_history[-5:],
                budget=reset_result.observation.budget_remaining,
                step_count=steps + 1
            )
        except Exception as e:
            print(f"LLM call failed: {e}")
            break
        
        action = parse_action(response_text)
        if action is None:
            break
        
        if verbose:
            print(f"  Step {steps + 1}: {action.action_type}")
        
        result = env.step(action)
        
        messages_history.append(f"Assistant: {action.action_type} with {json.dumps(action.payload)}")
        if result.observation.last_tool_result:
            tool_result = result.observation.last_tool_result
            result_summary = f"{tool_result.get('tool_name', 'unknown')}: "
            if tool_result.get('success'):
                result_summary += "success"
            else:
                result_summary += f"failed - {tool_result.get('message', 'error')}"
            messages_history.append(f"Environment: {result_summary}")
        
        total_reward += result.reward
        steps += 1
        
        if result.done:
            if verbose:
                final_score = result.observation.last_tool_result.get("score", 0.0) if result.observation.last_tool_result else 0.0
                print(f"  Episode completed! Final score: {final_score:.4f}")
            break
        
        reset_result = result
    
    return {
        "case_id": reset_result.observation.case_id,
        "task_type": task_type,
        "steps": steps,
        "total_reward": total_reward,
        "final_score": reset_result.observation.last_tool_result.get("score", 0.0) if reset_result.observation.last_tool_result else 0.0,
        "budget_used": 15.0 - reset_result.observation.budget_remaining
    }


def run_baseline_inference(
    api_base_url: str = API_BASE_URL,
    model_name: str = MODEL_NAME,
    hf_token: str = HF_TOKEN,
    test_cases: Optional[list] = None,
    verbose: bool = True
) -> dict:
    if not hf_token:
        raise ValueError("HF_TOKEN is required. Set it in your environment or pass it directly.")
    
    client = OpenAI(
        base_url=api_base_url,
        api_key=hf_token
    )
    
    if test_cases is None:
        test_cases = [
            "CASE-A-001",
            "CASE-A-002",
            "CASE-B-001",
            "CASE-C-001",
            "CASE-D-001",
        ]
    
    if verbose:
        print("="*60)
        print("LedgerShield Baseline Inference")
        print("="*60)
        print(f"API Base: {api_base_url}")
        print(f"Model: {model_name}")
        print(f"Test Cases: {test_cases}")
        print("="*60)
    
    env_url = os.getenv("ENV_URL", "http://localhost:8000")
    results = []
    
    with LedgerShieldEnv(base_url=env_url) as env:
        for case_id in test_cases:
            try:
                result = run_episode(client, env, case_id=case_id, verbose=verbose)
                results.append(result)
            except Exception as e:
                print(f"Error on case {case_id}: {e}")
                results.append({
                    "case_id": case_id,
                    "error": str(e),
                    "steps": 0,
                    "total_reward": 0.0,
                    "final_score": 0.0
                })
    
    successful = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]
    
    stats = {
        "total_cases": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "average_score": sum(r.get("final_score", 0.0) for r in successful) / max(len(successful), 1),
        "average_reward": sum(r.get("total_reward", 0.0) for r in successful) / max(len(successful), 1),
        "average_steps": sum(r.get("steps", 0) for r in successful) / max(len(successful), 1),
        "by_task_type": {}
    }
    
    # Group by task type
    for result in successful:
        task_type = result.get("task_type", "unknown")
        if task_type not in stats["by_task_type"]:
            stats["by_task_type"][task_type] = []
        stats["by_task_type"][task_type].append(result.get("final_score", 0.0))
    
    for task_type, scores in stats["by_task_type"].items():
        stats["by_task_type"][task_type] = {
            "count": len(scores),
            "avg_score": sum(scores) / max(len(scores), 1)
        }
    
    if verbose:
        print("\n" + "="*60)
        print("RESULTS SUMMARY")
        print("="*60)
        print(f"Total Cases: {stats['total_cases']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"Average Score: {stats['average_score']:.4f}")
        print(f"Average Reward: {stats['average_reward']:.4f}")
        print(f"Average Steps: {stats['average_steps']:.1f}")
        print("\nBy Task Type:")
        for task_type, data in stats["by_task_type"].items():
            print(f"  {task_type}: avg={data['avg_score']:.4f} (n={data['count']})")
        print("="*60)
    
    return {
        "results": results,
        "statistics": stats
    }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="LedgerShield Baseline Inference")
    parser.add_argument("--api-url", type=str, default=API_BASE_URL, help="API base URL")
    parser.add_argument("--model", type=str, default=MODEL_NAME, help="Model name")
    parser.add_argument("--token", type=str, default=HF_TOKEN, help="HF Token")
    parser.add_argument("--env-url", type=str, default=os.getenv("ENV_URL", "http://localhost:8000"), help="Environment URL")
    parser.add_argument("--cases", type=str, nargs="+", default=None, help="Specific case IDs to test")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    
    args = parser.parse_args()
    
    api_url = args.api_url if args.api_url else API_BASE_URL
    model = args.model if args.model else MODEL_NAME
    token = args.token if args.token else HF_TOKEN
    
    os.environ["API_BASE_URL"] = api_url
    os.environ["MODEL_NAME"] = model
    os.environ["HF_TOKEN"] = token
    if args.env_url:
        os.environ["ENV_URL"] = args.env_url
    
    run_baseline_inference(
        api_base_url=api_url,
        model_name=model,
        hf_token=token,
        test_cases=args.cases,
        verbose=not args.quiet
    )


if __name__ == "__main__":
    main()
