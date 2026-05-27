"""EXP-005: variability study on the already-deployed memory_assistant.

Runs the same memory workflow K times (fresh user per run to isolate per-run
non-determinism from cross-run memory accumulation) and quantifies how much
usage swings run-to-run. Per-run usage_metadata is captured instantly; one
settle + Monitoring pull at the end gives aggregate runtime + memory_bank
totals over the whole span.

Usage: python scripts/exp005_variability.py --runs 4 --settle 300
"""

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import vertexai
from vertexai import agent_engines

from agent_cost_estimator import load_or_build, price_query, build_turn, write_transcript
from agent_cost_estimator.usage import (
    collect_runtime_usage, price_runtime, collect_memory_usage,
    price_memory_usage,
)

PROJECT, LOCATION = "jsb-genai-sa", "us-central1"
STAGING = "gs://jsb-genai-sa-staging"
DATA = Path(__file__).resolve().parents[1] / "data"

FACTS = [
    "Hi! My name is Alice and I'm a marine biologist in Lisbon.",
    "Please remember I always prefer metric units and I'm vegetarian.",
]
RECALL = ("Based on what you know about me, suggest what I should pack for a "
          "research trip, and note my dietary preference.")


def one_run(engine, pb, user, transcripts):
    """Run facts -> generate memories -> recall; return per-run usage metrics."""
    events_total = 0
    in_tok = out_tok = calls = 0
    recall_ok = False

    def turn(session_id, msg):
        nonlocal events_total, in_tok, out_tok, calls
        evs = list(engine.stream_query(user_id=user, session_id=session_id, message=msg))
        events_total += len(evs) + 1
        qc = price_query(evs, pb)
        in_tok += qc.usage.prompt_tokens + qc.usage.cached_tokens
        out_tok += qc.usage.output_tokens
        calls += qc.usage.model_calls
        rec = build_turn(msg, evs, session_id=session_id)
        rec["user"] = user
        transcripts.append(rec)
        return evs

    sa = engine.create_session(user_id=user)
    sa_id = sa.get("id") if isinstance(sa, dict) else sa.id
    for f in FACTS:
        turn(sa_id, f)
    try:
        sess = engine.get_session(user_id=user, session_id=sa_id)
        asyncio.run(engine.async_add_session_to_memory(session=sess))
    except Exception as ex:
        print("   memory add failed:", repr(ex))
    time.sleep(20)
    sb = engine.create_session(user_id=user)
    sb_id = sb.get("id") if isinstance(sb, dict) else sb.id
    rec = turn(sb_id, RECALL)
    for e in rec:
        for p in (e.get("content") or {}).get("parts") or []:
            if p.get("text") and "vegetarian" in p["text"].lower():
                recall_ok = True

    model_usd = (in_tok * (pb.input_token_usd or 0)
                 + out_tok * (pb.output_token_usd or 0))
    return {
        "user": user, "input_tokens": in_tok, "output_tokens": out_tok,
        "model_calls": calls, "session_events": events_total,
        "recall_ok": recall_ok, "model_usd": model_usd,
    }


def variability(rows, key):
    vals = [r[key] for r in rows]
    mean = statistics.mean(vals)
    sd = statistics.pstdev(vals)
    return {
        "mean": round(mean, 4), "min": min(vals), "max": max(vals),
        "stdev": round(sd, 4),
        "cv_pct": round(100 * sd / mean, 1) if mean else 0.0,
        "spread_pct": round(100 * (max(vals) - min(vals)) / mean, 1) if mean else 0.0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=4)
    ap.add_argument("--settle", type=int, default=300)
    args = ap.parse_args()

    vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=STAGING)
    dep = json.loads((DATA / "deployment_memory_assistant.json").read_text())
    name = dep["resource_name"]
    engine_id = name.rstrip("/").split("/")[-1]
    engine = agent_engines.get(name)
    pb = load_or_build("gemini-2.5-flash")

    stamp = int(time.time())
    win_start = datetime.now(timezone.utc) - timedelta(seconds=60)
    rows = []
    transcripts = []
    for i in range(args.runs):
        user = f"vary-{stamp}-{i}"
        print(f"Run {i+1}/{args.runs} (user={user})...")
        r = one_run(engine, pb, user, transcripts)
        rows.append(r)
        print(f"  in={r['input_tokens']:5} out={r['output_tokens']:5} calls={r['model_calls']} "
              f"events={r['session_events']} recall_ok={r['recall_ok']} model=${r['model_usd']:.6f}")

    var = {k: variability(rows, k) for k in
           ("input_tokens", "output_tokens", "model_calls", "session_events", "model_usd")}
    print("\n=== PER-RUN VARIABILITY (usage_metadata) ===")
    print(json.dumps(var, indent=2))
    recall_rate = sum(1 for r in rows if r["recall_ok"]) / len(rows)
    print(f"recall_ok rate: {recall_rate:.0%}")

    print(f"\nWaiting {args.settle}s for Monitoring ingestion...")
    time.sleep(args.settle)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    w0, w1 = win_start.strftime(fmt), datetime.now(timezone.utc).strftime(fmt)
    runtime = collect_runtime_usage(PROJECT, engine_id, w0, w1)
    memory = collect_memory_usage(PROJECT, engine_id, w0, w1)
    mem_priced = price_memory_usage(memory, pb)
    rt_priced = price_runtime(runtime, pb)
    print("\n=== AGGREGATE OVER ALL RUNS (Cloud Monitoring) ===")
    print(json.dumps({
        "window": [w0, w1], "runs": args.runs,
        "runtime": {"usage": runtime.to_dict(), "priced": rt_priced},
        "memory_bank": mem_priced,
        "per_run_avg_runtime_usd": rt_priced["runtime_total_usd"] / args.runs,
        "per_run_avg_memory_retrievals": memory.get("memory_retrieval_count", 0) / args.runs,
        "per_run_avg_memories_written": memory.get("memory_mutation_count", 0) / args.runs,
    }, indent=2))

    out = {"agent": "memory_assistant", "engine": name, "runs": rows,
           "variability": var, "recall_rate": recall_rate,
           "aggregate_window": [w0, w1],
           "runtime": rt_priced, "memory_bank": mem_priced}
    rpt = DATA / "cost_report_exp005_variability.json"
    rpt.write_text(json.dumps(out, indent=2))
    tpath = DATA / "transcript_exp005_variability.jsonl"
    write_transcript(tpath, transcripts)
    print("\nReport written to", rpt)
    print(f"Transcript ({len(transcripts)} turns) written to", tpath)


if __name__ == "__main__":
    main()
