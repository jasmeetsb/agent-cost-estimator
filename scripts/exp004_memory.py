"""EXP-004 driver: exercise Agent Engine Memory Bank + sub-agents, extract usage.

Flow:
  1. Session A (user gives durable facts about themselves).
  2. add_session_to_memory(A)  -> Memory Bank runs an LLM to extract memories
     (this is the generate_memories_token_count cost).
  3. Session B (a recall question) -> preload_memory retrieves stored memories.
  4. Sum usage_metadata tokens across all model calls.
  5. Settle, then pull actual usage from Cloud Monitoring: runtime (vCPU/mem),
     memory_bank (generate tokens, mutations, retrievals), and token cross-check.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import vertexai
from vertexai import agent_engines

from agent_cost_estimator import load_or_build, price_query, Aggregate
from agent_cost_estimator.usage import (
    collect_runtime_usage, price_runtime, collect_publisher_tokens,
    collect_memory_usage,
)

PROJECT, LOCATION = "jsb-genai-sa", "us-central1"
STAGING = "gs://jsb-genai-sa-staging"
DATA = Path(__file__).resolve().parents[1] / "data"
USER = "alice"

FACTS = [
    "Hi! My name is Alice and I'm a marine biologist in Lisbon.",
    "Please remember I always prefer metric units and I'm vegetarian.",
]
RECALL = "Based on what you know about me, suggest what I should pack for a research trip, and note my dietary preference."


def drive(engine, pb):
    agg = Aggregate()
    log = []

    def run(session_id, msg):
        events = []
        t0 = time.time()
        for e in engine.stream_query(user_id=USER, session_id=session_id, message=msg):
            events.append(e)
        qc = price_query(events, pb, latency_s=time.time() - t0)
        agg.add(qc)
        log.append({"session": session_id, "msg": msg, **qc.to_dict()})
        d = qc.to_dict()
        print(f"  [{session_id[:8]}] in={d['prompt_tokens']:5} out={d['output_tokens']:5} "
              f"calls={d['model_calls']} {d['latency_s']}s")
        return events

    # --- Session A: give facts ---
    print("Session A (facts):")
    sa = engine.create_session(user_id=USER)
    sa_id = sa.get("id") if isinstance(sa, dict) else sa.id
    for f in FACTS:
        run(sa_id, f)

    # --- Generate memories from session A ---
    # Remote exposes only async_add_session_to_memory(session=<full session>).
    print("Generating memories from session A...")
    try:
        sess = engine.get_session(user_id=USER, session_id=sa_id)
        asyncio.run(engine.async_add_session_to_memory(session=sess))
        print("  async_add_session_to_memory OK")
    except Exception as ex:
        print("  add_session_to_memory failed:", repr(ex))

    time.sleep(20)  # let memory generation finish before recall

    # --- Session B: recall ---
    print("Session B (recall):")
    sb = engine.create_session(user_id=USER)
    sb_id = sb.get("id") if isinstance(sb, dict) else sb.id
    rec_events = run(sb_id, RECALL)
    for e in rec_events:
        parts = (e.get("content") or {}).get("parts") or []
        for p in parts:
            if p.get("text"):
                print("  RECALL ANSWER:", p["text"][:240])

    return agg, log


def main():
    vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=STAGING)
    dep = json.loads((DATA / "deployment_memory_assistant.json").read_text())
    name = dep["resource_name"]
    engine_id = name.rstrip("/").split("/")[-1]
    engine = agent_engines.get(name)

    print("Remote operations:", [s.get("name") for s in (engine.operation_schemas() or [])])
    pb = load_or_build("gemini-2.5-flash")

    win_start = datetime.now(timezone.utc) - timedelta(seconds=60)
    agg, log = drive(engine, pb)

    s = agg.summary()
    print("\n=== TOKEN COST (usage_metadata) ===")
    print(f"  queries={s['n']} avg_in={s['avg_prompt_tokens']:.0f} "
          f"avg_out={s['avg_output_tokens']:.0f} total_model=${sum(c.model_usd for c in agg.costs):.6f}")

    settle = 300
    print(f"\nWaiting {settle}s for Monitoring ingestion...")
    time.sleep(settle)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    w0, w1 = win_start.strftime(fmt), datetime.now(timezone.utc).strftime(fmt)

    runtime = collect_runtime_usage(PROJECT, engine_id, w0, w1)
    memory = collect_memory_usage(PROJECT, engine_id, w0, w1)
    tokens_mon = collect_publisher_tokens(PROJECT, w0, w1)
    um_in = sum(c.usage.prompt_tokens + c.usage.cached_tokens for c in agg.costs)
    um_out = sum(c.usage.output_tokens for c in agg.costs)

    report = {
        "agent": "memory_assistant", "engine": name, "window": [w0, w1],
        "token_cost_usage_metadata": {
            "input": um_in, "output_incl_thoughts": um_out,
            "model_usd": sum(c.model_usd for c in agg.costs),
        },
        "runtime_by_sku": {"usage": runtime.to_dict(), "priced": price_runtime(runtime, pb)},
        "memory_bank_by_sku": memory,
        "token_xcheck_monitoring": tokens_mon,
        "rows": log,
    }
    print("\n=== ACTUAL USAGE BY SKU ===")
    print(json.dumps({k: report[k] for k in
                      ("runtime_by_sku", "memory_bank_by_sku", "token_xcheck_monitoring")},
                     indent=2))
    out = DATA / "cost_report_memory_assistant.json"
    out.write_text(json.dumps(report, indent=2))
    print("\nReport written to", out)


if __name__ == "__main__":
    main()
