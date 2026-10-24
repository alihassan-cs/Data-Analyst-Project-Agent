"""Quick test from the terminal.

  python test.py                                  -> interactive chat (Groq)
  python test.py "How many orders are there?"     -> one question
  python test.py --provider gemini "..."          -> pick provider (groq | gemini | claude)
"""
import argparse
import sys

from agent import DataAgent, find_csvs, load_notes

ap = argparse.ArgumentParser()
ap.add_argument("question", nargs="*")
ap.add_argument("--provider", default="groq", choices=["groq", "gemini", "claude"])
args = ap.parse_args()

paths = find_csvs("data")
if not paths:
    sys.exit("No CSV files found in ./data. Unzip the Kaggle Olist files into the data/ folder.")

agent = DataAgent(paths, provider=args.provider, notes=load_notes())
print(f"Provider: {args.provider} | model: {agent.model}")
print("Tables loaded:", ", ".join(agent.tables), "\n")


def run(q):
    print(agent.ask(q))
    for sql in agent.queries:
        print("\n  SQL:", sql)
    s = agent.last_stats
    print(f"\n  [{s['tokens_in']} in / {s['tokens_out']} out tokens, {s['seconds']}s, {s['queries']} queries]\n")


if args.question:
    run(" ".join(args.question))
else:
    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q:
            run(q)
