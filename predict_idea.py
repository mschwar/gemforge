import sys
import json
from dotenv import load_dotenv
load_dotenv()

from core.prediction.oracle import oracle

def main():
    print(f"\n{'═'*80}")
    print(f" 🔮 GEMFORGE ORACLE — Consulting the patterns...")
    print(f"{'═'*80}\n")
    
    ideas = oracle.generate_predictions()
    
    if not ideas:
        print("The Oracle is silent. Try again later.")
        sys.exit(1)
        
    print("\n🔮 The Oracle has spoken:\n")
    for idea in ideas:
        print(f"🔹 {idea.get('type', 'Idea').upper()}: {idea.get('title')}")
        print(f"   {idea.get('one_liner')}")
        print(f"   Reason: {idea.get('why_it_fits')}")
        print(f"   Stack: {idea.get('tech_stack')}")
        print("-" * 40)
        
    print(f"\n✅ To forge one of these, copy the one-liner into:\n   python gemforge_cli.py new \"<idea>\"")
    print(f"{'═'*80}")

if __name__ == "__main__":
    main()
