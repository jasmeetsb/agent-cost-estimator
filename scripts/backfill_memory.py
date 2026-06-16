"""Backfill Memory Bank usage into a cost report after generation has settled.

WHY: Agent Engine Memory Bank generation (triggered by add_session_to_memory) is
asynchronous and its Cloud Monitoring metrics lag the run. Separately, exp_sample
had two bugs that zeroed memory regardless of timing: it read the wrong metric key
('generate_memories_tokens' vs the real 'generate_memories_token_count') and
hardcoded mutation_count to 0. This script re-queries the now-settled per-engine
memory_bank metrics and rewrites the report's memory_and_session + cumulative +
per_run_avg. Idempotent — safe to re-run as more generation settles.

Usage: python scripts/backfill_memory.py <pkg> [<pkg> ...]
Window: from the first batch start (or report window start) to now, scoped to the
engine_id in the report — so it captures exactly that engine's runs' generation.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent_cost_estimator import load_or_build
from agent_cost_estimator.usage import collect_memory_usage, price_memory_usage

PROJECT = "jsb-genai-sa"
DATA = Path(__file__).resolve().parents[1] / "data"


def backfill(pkg, pb):
    rpt = DATA / f"cost_report_{pkg}.json"
    if not rpt.exists():
        print(f"{pkg}: no cost report, skip"); return
    r = json.loads(rpt.read_text())
    engine_id = r["engine"].rstrip("/").split("/")[-1]
    cum = r.get("cumulative", {})
    cum_n = max(cum.get("interactions", len(r.get("runs", []))) or 1, 1)
    batches = r.get("batches", [])
    w0 = batches[0]["window"][0] if batches else r.get("window", [None])[0]
    w1 = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    m = collect_memory_usage(PROJECT, engine_id, w0, w1)
    gen = int(m.get("generate_memories_token_count", 0) or 0)
    mut = int(m.get("memory_mutation_count", 0) or 0)
    retr = int(m.get("memory_retrieval_count", 0) or 0)

    cum["generate_memories_tokens"] = gen
    cum["memory_mutations"] = mut
    cum["memory_retrieved"] = retr
    r["cumulative"] = cum

    mem_priced = price_memory_usage(
        {"generate_memories_token_count": gen, "memory_retrieval_count": retr,
         "memory_mutation_count": mut},
        pb, session_events=cum.get("session_events", 0))
    r["memory_and_session"] = mem_priced

    pa = r["per_run_avg"]
    pa["memory_session_usd"] = mem_priced["per_run_memory_usd"] / cum_n
    pa["total_usd"] = (pa.get("model_usd", 0) + pa.get("runtime_usd", 0)
                       + pa["memory_session_usd"] + pa.get("firestore_usd", 0))
    r["memory_backfilled"] = {"window": [w0, w1], "gen_tokens": gen,
                              "mutations": mut, "retrieved": retr, "interactions": cum_n}
    rpt.write_text(json.dumps(r, indent=2))
    print(f"{pkg:26} gen_tokens={gen:>8} ({gen/cum_n:>7.0f}/intxn) mutations={mut:>4} "
          f"retr={retr:>3} -> mem_session=${pa['memory_session_usd']:.5f}/intxn "
          f"base_total=${pa['total_usd']:.5f}")


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    pb = load_or_build("gemini-2.5-flash")
    for pkg in sys.argv[1:]:
        backfill(pkg, pb)


if __name__ == "__main__":
    main()
