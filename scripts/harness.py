"""Cost-estimation harness (agent-parameterized, with actual SKU extraction).

Sends a workload to an ADK agent (local in-process or deployed Agent Engine),
captures per-query token usage (exact, from usage_metadata), prices it via the
live Billing Catalog, and — in remote mode — also pulls ACTUAL Agent Engine
runtime usage (vCPU/memory) from Cloud Monitoring and prices that too.

Usage:
  python scripts/harness.py --agent weather_agent  --mode local  --iters 5
  python scripts/harness.py --agent research_agent --mode remote --iters 5 --settle 300
"""

import argparse
import importlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agents"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import vertexai

from agent_cost_estimator import load_or_build, price_query, Aggregate, build_turn, write_transcript
from agent_cost_estimator.usage import (
    collect_runtime_usage, price_runtime, collect_publisher_tokens,
)

PROJECT = "jsb-genai-sa"
LOCATION = "us-central1"
STAGING = "gs://jsb-genai-sa-staging"
DATA = Path(__file__).resolve().parents[1] / "data"

WORKLOADS = {
    "weather_agent": [
        "What's the weather in Tokyo?",
        "What's the weather in London?",
        "What timezone is San Francisco in?",
        "Tell me the weather and timezone for New York.",
        "What's the weather in Paris?",
    ],
    "research_agent": [
        "What is the mean of 4, 8 and 15, and what is the speed of light?",
        "Multiply 12 by 9, then tell me Avogadro's number.",
        "What's the earth radius? Also add 100 and 250.",
        "Compute the mean of 3, 6, 9, 12 and give me the value of pi.",
        "What is 7 times 8, and what is the speed of light?",
    ],
}


def get_agent(mode: str, agent_name: str):
    vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=STAGING)
    if mode == "local":
        from vertexai.preview import reasoning_engines
        root = importlib.import_module(f"{agent_name}.agent").root_agent
        return reasoning_engines.AdkApp(agent=root), "local", None
    from vertexai import agent_engines
    dep = json.loads((DATA / f"deployment_{agent_name}.json").read_text())
    name = dep["resource_name"]
    engine_id = name.rstrip("/").split("/")[-1]
    return agent_engines.get(name), name, engine_id


def run_query(agent, user_id, message):
    events = []
    t0 = time.time()
    for event in agent.stream_query(user_id=user_id, message=message):
        events.append(event)
    return events, time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--mode", choices=["local", "remote"], default="local")
    ap.add_argument("--iters", type=int, default=5)
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--settle", type=int, default=300,
                    help="seconds to wait for Monitoring ingestion before pulling runtime")
    args = ap.parse_args()

    workload = WORKLOADS.get(args.agent, WORKLOADS["weather_agent"])
    pb = load_or_build(args.model)
    print(f"Pricebook[{args.model}]: in={pb.input_token_usd} out={pb.output_token_usd} "
          f"vcpu/s={pb.runtime_vcpu_core_sec_usd} mem/s={pb.runtime_mem_gib_sec_usd}\n")

    agent, target, engine_id = get_agent(args.mode, args.agent)
    print(f"Agent={args.agent} mode={args.mode} target={target}\n")

    agg = Aggregate()
    rows = []
    transcripts = []
    win_start = datetime.now(timezone.utc) - timedelta(seconds=60)
    for i in range(args.iters):
        msg = workload[i % len(workload)]
        events, latency = run_query(agent, f"harness-{i}", msg)
        qc = price_query(events, pb, latency_s=latency)
        agg.add(qc)
        transcripts.append(build_turn(msg, events, session_id=f"harness-{i}"))
        d = qc.to_dict()
        rows.append({"query": msg, **d})
        print(f"[{i+1}/{args.iters}] {msg[:40]:40} in={d['prompt_tokens']:6} "
              f"out={d['output_tokens']:6} calls={d['model_calls']} {latency:5.2f}s "
              f"model=${d['model_usd']:.6f}")

    summary = agg.summary()
    print("\n=== TOKEN COST SUMMARY (exact usage x catalog price) ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    runtime = None
    token_xcheck = None
    if args.mode == "remote" and engine_id:
        print(f"\nWaiting {args.settle}s for Cloud Monitoring ingestion...")
        time.sleep(args.settle)
        win_end = datetime.now(timezone.utc)
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        w0, w1 = win_start.strftime(fmt), win_end.strftime(fmt)

        u = collect_runtime_usage(PROJECT, engine_id, w0, w1)
        runtime = {"usage": u.to_dict(), "priced": price_runtime(u, pb)}
        print("\n=== ACTUAL RUNTIME USAGE BY SKU (Cloud Monitoring) ===")
        print(json.dumps(runtime, indent=2))

        # Cross-check: per-query usage_metadata totals vs project-wide Monitoring tokens.
        um_input = sum(c.usage.prompt_tokens + c.usage.cached_tokens for c in agg.costs)
        um_out_with_thoughts = sum(c.usage.output_tokens for c in agg.costs)
        um_thoughts = sum(c.usage.thoughts_tokens for c in agg.costs)
        mon = collect_publisher_tokens(PROJECT, w0, w1)
        token_xcheck = {
            "window": [w0, w1],
            "usage_metadata": {
                "input": um_input,
                "output_candidates_only": um_out_with_thoughts - um_thoughts,
                "thoughts": um_thoughts,
                "output_incl_thoughts": um_out_with_thoughts,
            },
            "monitoring_publisher": mon,
            "note": "Monitoring is project+region aggregate (all Gemini traffic in window); "
                    "usage_metadata is this agent's queries only. Match only if agent is sole "
                    "traffic source.",
        }
        print("\n=== TOKEN SOURCE CROSS-CHECK (usage_metadata vs Cloud Monitoring) ===")
        print(json.dumps(token_xcheck, indent=2))

    out = {
        "agent": args.agent, "model": args.model, "mode": args.mode, "target": target,
        "token_summary": summary, "runtime": runtime, "token_xcheck": token_xcheck,
        "rows": rows,
    }
    rpt = DATA / f"cost_report_{args.agent}_{args.mode}.json"
    rpt.write_text(json.dumps(out, indent=2))
    tpath = DATA / f"transcript_{args.agent}_{args.mode}.jsonl"
    write_transcript(tpath, transcripts)
    print(f"\nReport written to {rpt}")
    print(f"Transcript ({len(transcripts)} turns) written to {tpath}")


if __name__ == "__main__":
    main()
