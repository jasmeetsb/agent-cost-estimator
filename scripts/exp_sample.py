"""Generic cost experiment for a deployed ADK-sample agent.

Per run: a 2-turn conversation in one session + add_session_to_memory (to
exercise Sessions + Memory Bank), capturing usage_metadata + transcript. Repeats
N runs for variability, then settles and pulls actual SKU usage from Cloud
Monitoring (runtime, memory_bank) + token cross-check, prices everything, and
writes a cost report. Produces the same shape used for per-agent summaries.

Usage: python scripts/exp_sample.py --package financial_advisor --runs 3 --settle 300
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
    price_memory_usage, collect_publisher_tokens, collect_grounding_usage,
    collect_imagen_usage, extract_grounding_from_events, price_grounding_and_media,
)

PROJECT, LOCATION = "jsb-genai-sa", "us-central1"
STAGING = "gs://jsb-genai-sa-staging"
DATA = Path(__file__).resolve().parents[1] / "data"
USER = "coster"

# 2-turn workloads per agent (kept short; these agents fan out heavily).
WORKLOADS = {
    "financial_advisor": [
        "I'm a moderate-risk investor. Analyze the outlook for NVDA.",
        "Based on that, suggest a simple trading strategy and key risks.",
    ],
    "academic_research": [
        "Summarize recent research directions in efficient transformer architectures.",
        "Which of those directions looks most promising for edge deployment, and why?",
    ],
    "blogger_agent": [
        "Write a short technical blog post about why vector databases matter for RAG.",
        "Make the intro punchier and add a one-line takeaway at the end.",
    ],
    "marketing_coordinator": [
        "Create a brand concept for a new oat-milk startup called OatJoy.",
        "Suggest a tagline and a simple landing-page hero section.",
    ],
    "marketing_agency": [
        "Create a brand concept for a new oat-milk startup called OatJoy.",
        "Suggest a tagline and a simple landing-page hero section.",
    ],
    "nexshift_agent": [
        "Generate a 1-week nurse roster for 5 nurses across 3 daily shifts; minimum 2 nurses per shift.",
        "Now adjust the roster if 1 nurse is unavailable Tuesday morning and another wants Friday off.",
    ],
    "fomc_research": [
        "Summarize the key economic themes from the most recent FOMC meeting.",
        "What was the FOMC's stance on inflation outlook and interest-rate trajectory?",
    ],
    "on_brand_genmedia": [
        "Generate a brand-aligned hero image for a coffee shop's grand opening promotion.",
        "Now create a variation sized for an Instagram banner.",
    ],
    "plumber_agent": [
        "Design a Dataflow pipeline that reads daily CSV uploads from GCS and writes cleaned rows to BigQuery.",
        "What would the dbt model look like to aggregate the daily data into weekly summaries?",
    ],
    # ---- Archetype agents (moderate complexity) ----
    "conversational_chatbot": [
        "Hi, how do I reset my password and what are your support hours?",
        "Also, what are your pricing tiers and do you support SSO?",
    ],
    "workflow_operator": [
        "Process order ORD-1001 end to end and apply discount code SAVE10 with express shipping.",
        "Now process order ORD-1003 — flag any issues before shipping.",
    ],
    "autonomous_researcher": [
        "Research the current state of small modular nuclear reactors (SMRs) and their commercial outlook.",
        "Now focus on the main regulatory and cost barriers, and which companies lead.",
    ],
    "multi_agent_orchestrator": [
        "Analyze last quarter's support-ticket volume trend and recommend actions.",
        "Now draft an executive summary, open a follow-up ticket, and send an update to the ops channel.",
    ],
}


def _with_retry(fn, *, what="call", tries=6, base=8.0):
    """Retry on ResourceExhausted (429 'Query Reasoning Engine requests per minute
    per region' — a per-minute regional rate limit). Exponential backoff so the
    minute window clears between attempts."""
    import time as _t
    for i in range(tries):
        try:
            return fn()
        except Exception as ex:
            m = str(ex)
            transient = ("RESOURCE_EXHAUSTED" in m or "429" in m or "ResourceExhausted" in type(ex).__name__
                         or "503" in m or "ServiceUnavailable" in type(ex).__name__)
            if not transient or i == tries - 1:
                raise
            wait = base * (2 ** i)
            print(f"   {what}: rate-limited, backoff {wait:.0f}s (attempt {i+1}/{tries})")
            _t.sleep(min(wait, 90))


def one_run(engine, pb, user, transcripts):
    in_tok = out_tok = calls = events_total = grounded = 0
    prompts = WORKLOADS.get(_AGENT, WORKLOADS["financial_advisor"])

    def _query(session_id, msg):
        evs = list(engine.stream_query(user_id=user, session_id=session_id, message=msg))
        # Throttling (90 req/min) sometimes yields an EMPTY stream instead of
        # raising 429. Treat a no-event response as transient so _with_retry waits.
        if not evs:
            raise RuntimeError("RESOURCE_EXHAUSTED: empty stream (likely rate-limited)")
        return evs

    def turn(session_id, msg):
        nonlocal in_tok, out_tok, calls, events_total, grounded
        evs = _with_retry(lambda: _query(session_id, msg), what="stream_query")
        events_total += len(evs) + 1
        qc = price_query(evs, pb)
        in_tok += qc.usage.prompt_tokens + qc.usage.cached_tokens
        out_tok += qc.usage.output_tokens
        calls += qc.usage.model_calls
        grounded += extract_grounding_from_events(evs)
        rec = build_turn(msg, evs, session_id=session_id); rec["user"] = user
        transcripts.append(rec)

    s = _with_retry(lambda: engine.create_session(user_id=user), what="create_session")
    sid = s.get("id") if isinstance(s, dict) else s.id
    for m in prompts:
        turn(sid, m)
    try:
        sess = _with_retry(lambda: engine.get_session(user_id=user, session_id=sid),
                           what="get_session")
        _with_retry(lambda: asyncio.run(engine.async_add_session_to_memory(session=sess)),
                    what="add_session_to_memory")
    except Exception as ex:
        print("   memory add skipped:", repr(ex)[:80])
    model_usd = in_tok * (pb.input_token_usd or 0) + out_tok * (pb.output_token_usd or 0)
    return {"user": user, "input_tokens": in_tok, "output_tokens": out_tok,
            "model_calls": calls, "session_events": events_total, "model_usd": model_usd,
            "grounded_responses": grounded}


def variability(rows, key):
    vals = [r[key] for r in rows]
    mean = statistics.mean(vals); sd = statistics.pstdev(vals)
    return {"mean": round(mean, 4), "min": min(vals), "max": max(vals),
            "cv_pct": round(100 * sd / mean, 1) if mean else 0.0}


_AGENT = None


def main():
    global _AGENT
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--settle", type=int, default=300)
    ap.add_argument("--delay", type=float, default=2.0,
                    help="seconds between runs to stay under the per-minute "
                         "Query Reasoning Engine requests quota")
    args = ap.parse_args()
    _AGENT = args.package

    vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=STAGING)
    dep = json.loads((DATA / f"deployment_{args.package}.json").read_text())
    name = dep["resource_name"]; engine_id = name.rstrip("/").split("/")[-1]
    engine = agent_engines.get(name)
    pb = load_or_build("gemini-2.5-flash")

    stamp = int(time.time())
    win_start = datetime.now(timezone.utc) - timedelta(seconds=60)
    rows, transcripts = [], []
    for i in range(args.runs):
        user = f"{USER}-{stamp}-{i}"
        print(f"Run {i+1}/{args.runs} ({args.package})...")
        try:
            r = one_run(engine, pb, user, transcripts)
        except Exception as ex:
            print("  run failed:", repr(ex)[:160]); continue
        if args.delay:
            time.sleep(args.delay)
        rows.append(r)
        print(f"  in={r['input_tokens']:6} out={r['output_tokens']:6} calls={r['model_calls']} "
              f"events={r['session_events']} model=${r['model_usd']:.6f}")

    if not rows:
        print("No successful runs."); return
    var = {k: variability(rows, k) for k in
           ("input_tokens", "output_tokens", "model_calls", "session_events", "model_usd")}

    print(f"\nWaiting {args.settle}s for Monitoring ingestion...")
    time.sleep(args.settle)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    w0, w1 = win_start.strftime(fmt), datetime.now(timezone.utc).strftime(fmt)
    runtime = collect_runtime_usage(PROJECT, engine_id, w0, w1)
    memory = collect_memory_usage(PROJECT, engine_id, w0, w1)
    mem_priced = price_memory_usage(memory, pb, session_events=int(var["session_events"]["mean"]))
    rt_priced = price_runtime(runtime, pb)
    tok_mon = collect_publisher_tokens(PROJECT, w0, w1)
    # PRIMARY grounding signal = per-interaction events (validated 2026-05-28):
    # the project-wide web_search_requests metric does NOT fire for native Gemini
    # Search grounding, but grounding_metadata appears in events when it occurs.
    grounded_events_total = sum(r.get("grounded_responses", 0) for r in rows)
    grounding_xcheck = collect_grounding_usage(PROJECT, w0, w1)  # secondary x-check ("Web Grounding for Enterprise")
    imagen = collect_imagen_usage(PROJECT, w0, w1)               # project-wide Imagen invocations
    media = price_grounding_and_media(grounded_events_total, int(imagen["images_generated"]))
    media["grounded_responses_source"] = "response events (grounding_metadata)"
    media["web_grounding_enterprise_xcheck"] = grounding_xcheck["web_search_requests"]
    media["imagen_by_model"] = imagen["by_model"]

    report = {
        "agent": args.package, "engine": name, "runs": rows, "variability": var,
        "window": [w0, w1],
        # Raw measured runtime usage (vCPU-sec, GiB-sec) from Cloud Monitoring, alongside priced.
        "runtime_usage": runtime.to_dict(),
        "runtime": rt_priced, "memory_and_session": mem_priced, "token_xcheck_monitoring": tok_mon,
        "grounding_and_media": media,
        "per_run_avg": {
            "model_usd": var["model_usd"]["mean"],
            "runtime_usd": rt_priced["runtime_total_usd"] / len(rows),
            "memory_session_usd": mem_priced["per_run_memory_usd"] / max(len(rows), 1),
        },
        "uncaptured_skus": ["Cloud Trace", "Cloud Logging", "Cloud Storage",
                            "memory storage (monthly)"],
    }
    report["per_run_avg"]["total_usd"] = sum(report["per_run_avg"].values())
    print("\n=== ACTUAL SKU USAGE (per agent, over window) ===")
    print(json.dumps({"runtime": rt_priced, "memory_and_session": mem_priced,
                      "grounding_and_media": media, "per_run_avg": report["per_run_avg"]}, indent=2))

    (DATA / f"cost_report_{args.package}.json").write_text(json.dumps(report, indent=2))
    write_transcript(DATA / f"transcript_{args.package}.jsonl", transcripts)
    print(f"\nReport: data/cost_report_{args.package}.json")


if __name__ == "__main__":
    main()
