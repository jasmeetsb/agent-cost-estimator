"""Cost-estimation harness.

Sends a workload of queries to an agent (local in-process or deployed on Agent
Engine), captures per-query token usage, prices it via the live Billing Catalog,
and reports the average cost per query plus a projection per 1k queries.

Usage:
  python scripts/harness.py --mode local  --iters 5
  python scripts/harness.py --mode remote --iters 5
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agents"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import vertexai

from agent_cost_estimator import load_or_build, price_query, Aggregate

PROJECT = "jsb-genai-sa"
LOCATION = "us-central1"
STAGING = "gs://jsb-genai-sa-staging"
DATA = Path(__file__).resolve().parents[1] / "data"

WORKLOAD = [
    "What's the weather in Tokyo?",
    "What's the weather in London?",
    "What timezone is San Francisco in?",
    "Tell me the weather and timezone for New York.",
    "What's the weather in Paris?",  # triggers the no-data path
]


def get_agent(mode: str):
    vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=STAGING)
    if mode == "local":
        from vertexai.preview import reasoning_engines
        from weather_agent.agent import root_agent
        return reasoning_engines.AdkApp(agent=root_agent), "local"
    # remote
    from vertexai import agent_engines
    dep = json.loads((DATA / "deployment.json").read_text())
    name = dep["resource_name"]
    return agent_engines.get(name), name


def run_query(agent, user_id, message):
    events = []
    t0 = time.time()
    for event in agent.stream_query(user_id=user_id, message=message):
        events.append(event)
    return events, time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["local", "remote"], default="local")
    ap.add_argument("--iters", type=int, default=len(WORKLOAD))
    ap.add_argument("--model", default="gemini-2.5-flash")
    args = ap.parse_args()

    pb = load_or_build(args.model)
    print(f"Pricebook for {args.model}: in={pb.input_token_usd} out={pb.output_token_usd} "
          f"runtime_vcpu/s={pb.runtime_vcpu_core_sec_usd} mem/s={pb.runtime_mem_gib_sec_usd}\n")

    agent, target = get_agent(args.mode)
    print(f"Target: {target}\n")

    agg = Aggregate()
    rows = []
    for i in range(args.iters):
        msg = WORKLOAD[i % len(WORKLOAD)]
        events, latency = run_query(agent, f"harness-{i}", msg)
        qc = price_query(events, pb, latency_s=latency)
        agg.add(qc)
        d = qc.to_dict()
        rows.append({"query": msg, **d})
        print(f"[{i+1}/{args.iters}] {msg[:42]:42} "
              f"in={d['prompt_tokens']:4} out={d['output_tokens']:4} "
              f"calls={d['model_calls']} {latency:5.2f}s  "
              f"model=${d['model_usd']:.6f} total=${d['total_usd']:.6f}")

    summary = agg.summary()
    print("\n=== SUMMARY ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    out = {
        "model": args.model, "mode": args.mode, "target": target,
        "summary": summary, "rows": rows,
    }
    rpt = DATA / f"cost_report_{args.mode}.json"
    rpt.write_text(json.dumps(out, indent=2))
    print(f"\nReport written to {rpt}")


if __name__ == "__main__":
    main()
