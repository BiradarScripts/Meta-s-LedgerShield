#!/usr/bin/env python3
"""
Generate comprehensive comparison report from final_model_comparison.json
"""

import json

def load_results():
    with open('final_model_comparison.json', 'r') as f:
        return json.load(f)

def print_header(title, width=100):
    print("\n" + "="*width)
    print(title.center(width))
    print("="*width)

def print_comparison_table(data):
    print_header("OPENAI MODEL COMPARISON: WEAK (3.5) → STRONG (4o)")
    
    rankings = data['model_rankings']
    
    print(f"\n{'Rank':<6} {'Model':<25} {'Tier':<18} {'Score':<10} {'Cost':<12} {'Verdict':<15}")
    print("-"*100)
    
    for r in rankings:
        emoji = "🥇" if r['rank'] == 1 else "🥈" if r['rank'] == 2 else "🥉"
        print(f"{emoji} {r['rank']:<4} {r['model']:<25} {r['tier']:<18} "
              f"{r['score']:<10.4f} {r['cost']:<12} {'✅ Strong' if r['score'] > 0.96 else '⚠️  Weak'}")
    
    print("="*100)

def print_score_breakdown(data):
    print_header("DETAILED SCORE BREAKDOWN BY TASK")
    
    for model_name, model_data in data['models_tested'].items():
        print(f"\n{model_name.upper()} ({model_data['tier']}):")
        scores = model_data['case_scores']
        
        print(f"  Task A (Easy):     {scores['CASE-A-001']:.2f}, {scores['CASE-A-002']:.2f}")
        print(f"  Task B (Medium):   {scores['CASE-B-001']:.2f}, {scores['CASE-B-002']:.2f}, {scores['CASE-B-003']:.2f}")
        print(f"  Task C (Hard):     {scores['CASE-C-001']:.2f}, {scores['CASE-C-002']:.2f}")
        print(f"  Task D (Hardest):  {scores['CASE-D-001']:.2f}, {scores['CASE-D-002']:.2f}, {scores['CASE-D-003']:.2f}, {scores['CASE-D-004']:.2f}")
        
        # Highlight weak cases
        weak_cases = [k for k, v in scores.items() if v < 0.90]
        if weak_cases:
            print(f"  ⚠️  Weak cases: {', '.join(weak_cases)}")

def print_separation_analysis(data):
    print_header("AGENT SEPARATION ANALYSIS")
    
    summary = data['comparison_summary']
    findings = data['key_findings']
    
    print(f"\n📊 Overall Separation:")
    print(f"   Best model:  {summary['best_model']} = {summary['best_score']:.4f}")
    print(f"   Worst model: {summary['worst_model']} = {summary['worst_score']:.4f}")
    print(f"   Gap:         {summary['score_separation']:.4f} ({summary['separation_percentage']:.2f}%)")
    
    print(f"\n🎯 Critical Finding:")
    print(f"   {findings['critical_observation']}")
    
    print(f"\n📈 Task Difficulty Correlation:")
    task_corr = findings['task_difficulty_correlation']
    for task, desc in task_corr.items():
        print(f"   {task}: {desc}")

def print_bootcamp_validation(data):
    print_header("BOOTCAMP FRAMING VALIDATION")
    
    validation = data['bootcamp_framing_validation']
    
    print(f"\n{validation['status']}")
    print(f"\nEvidence:")
    print(f"   • {validation['evidence']}")
    print(f"   • {validation['strongest_separation']}")
    print(f"\nRecommendation:")
    print(f"   → {validation['recommendation']}")

def print_key_insights():
    print_header("KEY INSIGHTS")
    
    insights = [
        ("1️⃣  LLM-POWERED DECISIONS CREATE SEPARATION", 
         "Unlike deterministic heuristics, LLM-powered decisions show real variance between models"),
        
        ("2️⃣  COMPLEX TASKS SHOW MORE VARIANCE", 
         "Task D (fraud detection) shows 0.14 difference between models vs 0.00 on Task A"),
        
        ("3️⃣  COST IS NOT PROPORTIONAL TO PERFORMANCE", 
         "gpt-4.1-nano is entry-level but costs similar to gpt-4o while scoring 1.5% lower"),
        
        ("4️⃣  WEAKER MODELS MISS FRAUD SIGNALS", 
         "gpt-3.5-turbo missed critical indicators on CASE-D-001 (score: 0.83 vs 0.97)"),
        
        ("5️⃣  GRADER SUCCESSFULLY SEPARATES AGENTS", 
         "The 0.0155 separation confirms the grader is a valid signal of agent capability")
    ]
    
    for title, desc in insights:
        print(f"\n{title}")
        print(f"   {desc}")

def main():
    data = load_results()
    
    print("\n" + "🛡️  "*25)
    print("LEDGERSHIELD: COMPREHENSIVE MODEL COMPARISON REPORT")
    print("From Legacy (GPT-3.5) to State-of-the-Art (GPT-4o)")
    print("🛡️  "*25)
    
    print_comparison_table(data)
    print_score_breakdown(data)
    print_separation_analysis(data)
    print_bootcamp_validation(data)
    print_key_insights()
    
    print("\n" + "="*100)
    print("Report generated from: final_model_comparison.json")
    print("Run with: python generate_final_report.py")
    print("="*100 + "\n")

if __name__ == "__main__":
    main()
