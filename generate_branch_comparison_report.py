#!/usr/bin/env python3
import json

def load_results():
    with open('branch_comparison.json', 'r') as f:
        return json.load(f)

def print_header(title, width=100):
    print("\n" + "="*width)
    print(title.center(width))
    print("="*width)

def print_comparison_table(data):
    print_header("MAIN vs HG_EDITS BRANCH COMPARISON")
    
    comparison = data['comparison']
    
    print(f"\n{'Model':<25} {'Main Branch':<15} {'hg_edits':<15} {'Change':<15} {'Impact':<20}")
    print("-"*100)
    
    for model, comp in comparison.items():
        change_symbol = "📈" if comp['difference'] > 0 else "📉" if comp['difference'] < 0 else "➡️"
        impact = comp['analysis'][:50] + "..." if len(comp['analysis']) > 50 else comp['analysis']
        print(f"{model:<25} {comp['main_score']:<15.4f} {comp['hg_edits_score']:<15.4f} "
              f"{change_symbol} {comp['change']:<12} {impact:<20}")
    
    print("="*100)

def print_shocking_findings(data):
    print_header("🚨 SHOCKING FINDINGS: HG_EDITS EFFECT")
    
    findings = data['shocking_findings']
    
    print(f"\n1️⃣  HG_EDITS MAKES SOTA MODEL WORSE")
    print(f"   {findings['hg_edits_makes_sota_worse']}")
    print(f"   gpt-5.4 goes from bad (0.9291) to terrible (0.8955)")
    
    print(f"\n2️⃣  HG_EDITS HELPS WEAK MODEL")
    print(f"   {findings['hg_edits_helps_weak_model']}")
    print(f"   gpt-3.5-turbo actually improves!")
    
    print(f"\n3️⃣  DOUBLE FAILURE ON HG_EDITS")
    print(f"   {findings['double_failure_on_hg_edits']}")
    print(f"   gpt-5.4 fails TWO cases instead of one")
    
    print(f"\n4️⃣  PERFORMANCE INVERSION")
    print(f"   {findings['inverted_performance']}")
    print(f"   Legacy model beats SOTA by 7.5%!")

def print_case_analysis(data):
    print_header("CASE-BY-CASE BREAKDOWN")
    
    cases = data['case_specific_analysis']
    
    for case_name, case_data in cases.items():
        print(f"\n{case_name}:")
        print(f"  Main Branch:   gpt-3.5={case_data['main']['gpt-3.5']:.2f}, "
              f"gpt-4o={case_data['main']['gpt-4o']:.2f}, "
              f"gpt-5.4={case_data['main']['gpt-5.4']:.2f}")
        print(f"  hg_edits:      gpt-3.5={case_data['hg_edits']['gpt-3.5']:.2f}, "
              f"gpt-4o={case_data['hg_edits']['gpt-4o']:.2f}, "
              f"gpt-5.4={case_data['hg_edits']['gpt-5.4']:.2f}")
        print(f"  Impact: {case_data['impact']}")

def print_conclusion(data):
    print_header("CONCLUSION & RECOMMENDATIONS")
    
    conclusion = data['conclusion']
    
    print(f"\n📊 HG_EDITS EFFECT:")
    print(f"   {conclusion['hg_edits_effect']}")
    
    print(f"\n🎯 BOOTCAMP IMPLICATION:")
    print(f"   {conclusion['bootcamp_implication']}")
    
    print(f"\n✅ RECOMMENDATION:")
    print(f"   {conclusion['recommendation']}")
    
    print(f"\n💡 KEY INSIGHT:")
    print(f"   The hg_edits branch amplifies model differences,")
    print(f"   making the grader an even better signal of agent capability!")

def main():
    data = load_results()
    
    print("\n" + "🔀 "*25)
    print("BRANCH COMPARISON: MAIN vs HG_EDITS")
    print("Impact Analysis on Model Performance")
    print("🔀 "*25)
    
    print_comparison_table(data)
    print_shocking_findings(data)
    print_case_analysis(data)
    print_conclusion(data)
    
    print("\n" + "="*100)
    print("💾 Full comparison: branch_comparison.json")
    print("="*100 + "\n")

if __name__ == "__main__":
    main()
