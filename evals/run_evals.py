"""Run the 30-question eval and score the agent.

  python evals/run_evals.py --provider groq --tag v1 --sleep 3
  python evals/run_evals.py --provider claude --tag v3

Each run is saved in evals/runs/ and one summary line is appended to evals/history.csv,
which is your v1 -> v2 -> v3 accuracy table for the README.
"""
import argparse
import csv
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agent import DailyLimitError, DataAgent, find_csvs, load_notes  # noqa: E402

REFUSAL = ["does not contain", "doesn't contain", "do not contain", "not available", "isn't available",
           "no column", "cannot", "can't", "unable", "not in the data", "no data", "don't have",
           "do not have", "not possible", "no information", "not included", "there is no", "there are no"]


def numbers(text):
    out = []
    for x in re.findall(r"-?\d[\d,]*\.?\d*", text):
        try:
            out.append(float(x.replace(",", "").rstrip(".")))
        except ValueError:
            pass
    return out


def norm(s):
    return re.sub(r"[_\-]+", " ", str(s).lower())


def contains_word(answer, value):
    v = re.escape(norm(value))
    return re.search(rf"(?<![a-z0-9]){v}(?![a-z0-9])", norm(answer)) is not None


def check(t, answer, con):
    """Returns (passed, gold_value)."""
    a = answer or ""
    if t["type"] == "refusal":
        return any(p in a.lower() for p in REFUSAL), "(should say the data can't answer this)"
    rows = con.execute(t["gold_sql"]).fetchall()
    if not rows:
        return False, "(gold query returned no rows)"
    if t["type"] == "number":
        g = float(rows[0][0])
        tol = 0.5 if g == int(g) else max(0.005 * abs(g), 0.011)
        return any(abs(n - g) <= tol for n in numbers(a)), g
    if t["type"] == "text":
        return contains_word(a, rows[0][0]), rows[0][0]
    if t["type"] == "list":
        vals = [r[0] for r in rows]
        return all(contains_word(a, v) for v in vals), vals
    raise ValueError(f"unknown type {t['type']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="groq", choices=["groq", "gemini", "claude"])
    ap.add_argument("--tag", default="v1", help="label for this run, e.g. v1, v2, v3")
    ap.add_argument("--limit", type=int, default=0, help="only run the first N questions")
    ap.add_argument("--sleep", type=float, default=0, help="seconds to wait between questions (free-tier limits)")
    args = ap.parse_args()

    paths = find_csvs(os.path.join(ROOT, "data"))
    if not paths:
        sys.exit("No CSV files in data/. Unzip the Kaggle Olist files there first.")
    agent = DataAgent(paths, provider=args.provider, notes=load_notes(os.path.join(ROOT, "data", "notes.txt")),
                      log_path=None)
    tests = json.load(open(os.path.join(ROOT, "evals", "eval_set.json")))
    if args.limit:
        tests = tests[:args.limit]

    rows, groups = [], {}
    for t in tests:
        try:
            ans = agent.ask(t["question"])
        except DailyLimitError as e:
            sys.exit(f"\nSTOPPED at question {t['id']}: {e}\nNothing was saved. Run again after the reset, "
                     "or use --provider gemini.")
        except Exception as e:  # noqa: BLE001
            ans = f"ERROR: {e}"
        ok, gold = check(t, ans, agent.con)
        rows.append({"id": t["id"], "group": t["group"], "ok": ok, "question": t["question"],
                     "gold": gold, "answer": ans, "sql": list(agent.queries), **agent.last_stats})
        g = groups.setdefault(t["group"], [0, 0])
        g[0] += ok
        g[1] += 1
        print(f"{'PASS' if ok else 'FAIL'} | {t['group']:6} | {t['question'][:80]}")
        if args.sleep:
            time.sleep(args.sleep)

    passed = sum(r["ok"] for r in rows)
    total = len(rows)
    acc = 100 * passed / total
    print(f"\nACCURACY: {passed}/{total} = {acc:.0f}%   ({args.provider} / {agent.model}, tag {args.tag})")
    for g, (p, n) in groups.items():
        print(f"  {g:7}: {p}/{n}")
    print(f"Tokens: {agent.tokens_in} in / {agent.tokens_out} out "
          f"(~{agent.tokens_in // max(total, 1)} in per question)")

    os.makedirs(os.path.join(ROOT, "evals", "runs"), exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    run_path = os.path.join(ROOT, "evals", "runs", f"{args.tag}_{args.provider}_{stamp}.json")
    json.dump(rows, open(run_path, "w"), indent=2, default=str)

    hist = os.path.join(ROOT, "evals", "history.csv")
    new = not os.path.exists(hist)
    with open(hist, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date", "tag", "provider", "model", "passed", "total", "accuracy_pct",
                        "tokens_in", "tokens_out"])
        w.writerow([time.strftime("%Y-%m-%d"), args.tag, args.provider, agent.model, passed, total,
                    round(acc, 1), agent.tokens_in, agent.tokens_out])
    print(f"Saved: {os.path.relpath(run_path, ROOT)} and evals/history.csv")
    print("Open the run file and read every FAIL to see why it failed.")


if __name__ == "__main__":
    main()
