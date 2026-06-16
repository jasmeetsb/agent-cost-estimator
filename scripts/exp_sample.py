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
    extract_firestore_ops, price_firestore,
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


# Multi-conversation scenarios (varying turn counts + topics) for the archetype
# agents. Real-world interactions differ in length and subject; cycling these
# across interactions makes the accumulated dataset more representative than one
# repeated 2-turn workload. Turn counts raised where it makes sense per archetype.
# 5 scenarios per agent, exactly ONE 2-turn + four 3-5 turn → ~80% of cycled
# interactions are >2 turns (meets the ≥70% multi-turn requirement). Diverse topics.
SCENARIOS = {
    "conversational_chatbot": [
        ["How do I reset my password, and what are your support hours?",          # 2
         "Also, what are your pricing tiers and do you support SSO?"],
        ["I'd like a refund on my last order.",                                   # 3
         "How long does that take to process?",
         "Can it go to a different card than I paid with?"],
        ["Do you integrate with Slack?",                                          # 4
         "What about exporting my data?",
         "Is data export on the Pro tier or Enterprise only?",
         "Okay — how do I upgrade my plan?"],
        ["My shipment hasn't arrived yet.",                                       # 4
         "It's order ORD-1002. What's the ETA?",
         "Can you switch it to express shipping?",
         "Will I be charged extra for that?"],
        ["I'm new — can you walk me through setting up my account?",              # 5
         "How do I invite my team?",
         "What roles can I assign them?",
         "Do you support SSO for the team?",
         "And what does all that cost on the Pro tier?"],
    ],
    "workflow_operator": [
        ["Process order ORD-1001 end to end and apply discount code SAVE10 with express shipping.",  # 2
         "Now process order ORD-1003 — flag any issues before shipping."],
        ["Process order ORD-1002 with standard shipping.",                        # 3
         "Apply the WELCOME discount and recalculate shipping.",
         "Send the customer an email confirmation and log it."],
        ["Check inventory for the items in order ORD-1001.",                      # 4
         "Validate the address and calculate express shipping.",
         "Apply SAVE10 and update the status to confirmed.",
         "Notify the customer by SMS and log the transaction."],
        ["Look up order ORD-1003 and tell me its current state.",                 # 4
         "The address issue is fixed — re-validate it.",
         "Calculate standard shipping and apply WELCOME.",
         "Confirm the order and notify by email."],
        ["Start processing order ORD-1001.",                                      # 5
         "Check inventory and confirm availability.",
         "Validate the shipping address.",
         "Apply SAVE10 with express shipping and update status.",
         "Notify the customer and write the audit log."],
    ],
    "autonomous_researcher": [
        ["Research the current state of small modular reactors (SMRs) and their commercial outlook.",  # 2
         "Now focus on the main regulatory and cost barriers, and which companies lead."],
        ["Research the state of solid-state EV batteries in 2026.",               # 3
         "Which companies are closest to mass production, and what hurdles remain?",
         "Summarize the investment outlook."],
        ["Research recent advances in direct-air carbon capture.",                # 3
         "Compare it with point-source capture on cost and scalability.",
         "Which approach is more likely to scale this decade, and why?"],
        ["Research the latest in efficient transformer architectures.",           # 4
         "Which techniques work best for edge deployment?",
         "How do quantization and distillation compare there?",
         "Summarize the practical recommendation."],
        ["Research the RAG vs long-context-window tradeoff for enterprise search.",  # 4
         "What are the cost implications of each?",
         "When does hybrid (keyword + vector) retrieval help?",
         "Give a recommended architecture for a 10M-document corpus."],
    ],
    "multi_agent_orchestrator": [
        ["Analyze last quarter's support-ticket volume trend and recommend actions.",  # 2
         "Now draft an executive summary, open a follow-up ticket, and send an update to the ops channel."],
        ["Pull our key product metrics for the last 30 days and analyze the trend.",   # 3
         "Fetch the related customer records.",
         "Summarize the findings, create a ticket for the biggest issue, and notify the team."],
        ["Gather sales metrics and the internal playbook on churn.",              # 5
         "Analyze the churn trend.",
         "Cross-reference it with recent support tickets.",
         "Draft an executive summary of what's driving churn.",
         "Open a remediation ticket and send an update to the ops channel."],
        ["Look at activation-rate metrics for the last 30 days.",                 # 4
         "Compare against the prior period and detect the trend.",
         "Check the onboarding playbook for known friction points.",
         "Draft recommendations and open a ticket."],
        ["Pull weekly active accounts and ticket volume per 100 accounts.",       # 4
         "Analyze whether support load is tracking growth.",
         "Summarize the finding with the key numbers.",
         "Notify the ops channel with the summary."],
    ],
}


def get_scenarios(pkg):
    """Return a list of conversations (each a list of turn strings) for an agent.
    Multi-scenario for archetypes; single repeated workload otherwise."""
    if pkg in SCENARIOS:
        return SCENARIOS[pkg]
    return [WORKLOADS.get(pkg, WORKLOADS["financial_advisor"])]


def one_run(engine, pb, user, transcripts, scenario):
    in_tok = out_tok = calls = events_total = grounded = 0
    prompts = scenario

    def _query(session_id, msg):
        evs = list(engine.stream_query(user_id=user, session_id=session_id, message=msg))
        # Throttling (90 req/min) sometimes yields an EMPTY stream instead of
        # raising 429. Treat a no-event response as transient so _with_retry waits.
        if not evs:
            raise RuntimeError("RESOURCE_EXHAUSTED: empty stream (likely rate-limited)")
        return evs

    fs_reads = fs_writes = 0

    def turn(session_id, msg):
        nonlocal in_tok, out_tok, calls, events_total, grounded, fs_reads, fs_writes
        evs = _with_retry(lambda: _query(session_id, msg), what="stream_query")
        events_total += len(evs) + 1
        qc = price_query(evs, pb)
        in_tok += qc.usage.prompt_tokens + qc.usage.cached_tokens
        out_tok += qc.usage.output_tokens
        calls += qc.usage.model_calls
        grounded += extract_grounding_from_events(evs)
        fs = extract_firestore_ops(evs)
        fs_reads += fs["reads"]; fs_writes += fs["writes"]
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
            "grounded_responses": grounded, "turns": len(prompts),
            "fs_reads": fs_reads, "fs_writes": fs_writes}


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
    ap.add_argument("--append", action="store_true",
                    help="accumulate onto the existing cost report + transcript "
                         "instead of overwriting (additive dataset across batches)")
    args = ap.parse_args()
    _AGENT = args.package

    vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=STAGING)
    dep = json.loads((DATA / f"deployment_{args.package}.json").read_text())
    name = dep["resource_name"]; engine_id = name.rstrip("/").split("/")[-1]
    engine = agent_engines.get(name)
    pb = load_or_build("gemini-2.5-flash")

    scenarios = get_scenarios(args.package)
    stamp = int(time.time())
    win_start = datetime.now(timezone.utc) - timedelta(seconds=60)
    rows, transcripts = [], []
    for i in range(args.runs):
        scenario = scenarios[i % len(scenarios)]
        user = f"{USER}-{stamp}-{i}"
        print(f"Run {i+1}/{args.runs} ({args.package}, {len(scenario)} turns)...")
        try:
            r = one_run(engine, pb, user, transcripts, scenario)
        except Exception as ex:
            print("  run failed:", repr(ex)[:160]); continue
        if args.delay:
            time.sleep(args.delay)
        rows.append(r)
        print(f"  turns={r['turns']} in={r['input_tokens']:6} out={r['output_tokens']:6} "
              f"calls={r['model_calls']} events={r['session_events']} model=${r['model_usd']:.6f}")

    if not rows:
        print("No successful runs."); return

    print(f"\nWaiting {args.settle}s for Monitoring ingestion...")
    time.sleep(args.settle)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    w0, w1 = win_start.strftime(fmt), datetime.now(timezone.utc).strftime(fmt)
    runtime = collect_runtime_usage(PROJECT, engine_id, w0, w1)
    memory = collect_memory_usage(PROJECT, engine_id, w0, w1)
    rt_priced = price_runtime(runtime, pb)
    imagen = collect_imagen_usage(PROJECT, w0, w1)
    grounded_events_total = sum(r.get("grounded_responses", 0) for r in rows)

    # This batch's window-total cost components (priced).
    batch_n = len(rows)
    batch_runtime_usd = rt_priced["runtime_total_usd"]
    batch_gen_tokens = memory.get("generate_memories_tokens", 0) or 0
    batch_session_events = sum(r.get("session_events", 0) for r in rows)
    batch_mem_retrieved = memory.get("memory_retrieval_count", 0) or 0
    batch_images = int(imagen["images_generated"])
    batch_fs_reads = sum(r.get("fs_reads", 0) for r in rows)
    batch_fs_writes = sum(r.get("fs_writes", 0) for r in rows)

    rpt_path = DATA / f"cost_report_{args.package}.json"
    # ---- accumulate onto prior batches when --append ----
    prior = {}
    if args.append and rpt_path.exists():
        prior = json.loads(rpt_path.read_text())
    all_rows = (prior.get("runs", []) if args.append else []) + rows
    cum = prior.get("cumulative", {}) if args.append else {}
    # Reconstruct cumulative from a pre-`cumulative` report (the original 35-run
    # batches) so their interactions/runtime aren't dropped from the amortization.
    if args.append and prior and "cumulative" not in prior:
        pr = prior.get("runs", []); pa = prior.get("per_run_avg", {})
        pgm = prior.get("grounding_and_media", {}); pms = prior.get("memory_and_session", {})
        cum = {"interactions": len(pr),
               "runtime_usd_total": pa.get("runtime_usd", 0.0) * len(pr),
               "generate_memories_tokens": pms.get("generate_memories_tokens", 0),
               "session_events": sum(r.get("session_events", 0) for r in pr),
               "memory_retrieved": pms.get("memories_retrieved", 0),
               "grounded_responses": int(pgm.get("web_search_requests", 0) or 0),
               "images_generated": int(pgm.get("images_generated", 0) or 0)}
    cum_n = cum.get("interactions", 0) + batch_n
    cum_runtime_usd = cum.get("runtime_usd_total", 0.0) + batch_runtime_usd
    cum_gen_tokens = cum.get("generate_memories_tokens", 0) + batch_gen_tokens
    cum_session_events = cum.get("session_events", 0) + batch_session_events
    cum_mem_retrieved = cum.get("memory_retrieved", 0) + batch_mem_retrieved
    cum_grounded = cum.get("grounded_responses", 0) + grounded_events_total
    cum_images = cum.get("images_generated", 0) + batch_images
    cum_fs_reads = cum.get("fs_reads", 0) + batch_fs_reads
    cum_fs_writes = cum.get("fs_writes", 0) + batch_fs_writes
    batches = prior.get("batches", []) if args.append else []
    batches.append({"window": [w0, w1], "interactions": batch_n,
                    "runtime_usd": round(batch_runtime_usd, 6),
                    "turns_per_interaction": sorted(set(r.get("turns", 0) for r in rows))})

    var = {k: variability(all_rows, k) for k in
           ("input_tokens", "output_tokens", "model_calls", "session_events", "model_usd", "turns")
           if all(k in rr for rr in all_rows)}

    # Priced cumulative memory+session and grounding/media (over cumulative counts).
    cum_memory = {"generate_memories_token_count": cum_gen_tokens,
                  "memory_retrieval_count": cum_mem_retrieved, "memory_mutation_count": 0}
    mem_priced = price_memory_usage(cum_memory, pb, session_events=cum_session_events)
    media = price_grounding_and_media(cum_grounded, cum_images)
    media["grounded_responses_source"] = "response events (grounding_metadata)"
    media["imagen_by_model"] = imagen["by_model"]
    firestore = price_firestore(cum_fs_reads, cum_fs_writes)

    per_run = {
        "model_usd": var["model_usd"]["mean"],                      # exact per-interaction mean
        "runtime_usd": cum_runtime_usd / max(cum_n, 1),             # amortized over all interactions
        "memory_session_usd": mem_priced["per_run_memory_usd"] / max(cum_n, 1),
        "firestore_usd": firestore["firestore_usd"] / max(cum_n, 1),
    }
    per_run["total_usd"] = sum(per_run.values())

    report = {
        "agent": args.package, "engine": name, "runs": all_rows, "variability": var,
        "window": [w0, w1],
        "cumulative": {"interactions": cum_n, "runtime_usd_total": cum_runtime_usd,
                       "generate_memories_tokens": cum_gen_tokens,
                       "session_events": cum_session_events, "memory_retrieved": cum_mem_retrieved,
                       "grounded_responses": cum_grounded, "images_generated": cum_images,
                       "fs_reads": cum_fs_reads, "fs_writes": cum_fs_writes},
        "batches": batches,
        "runtime_usage": runtime.to_dict(),
        "runtime": rt_priced, "memory_and_session": mem_priced,
        "grounding_and_media": media, "firestore": firestore,
        "per_run_avg": per_run,
        "uncaptured_skus": ["Cloud Trace", "Cloud Logging", "Cloud Storage",
                            "memory storage (monthly)",
                            "Agent Sandbox: Code Execution (no Monitoring metric; orchestrator only)"],
    }
    print(f"\n=== {'ACCUMULATED' if args.append else 'BATCH'} SKU USAGE "
          f"({cum_n} total interactions) ===")
    print(json.dumps({"per_run_avg": per_run, "n_interactions": cum_n,
                      "turns_seen": sorted(set(r.get('turns', 0) for r in all_rows))}, indent=2))

    rpt_path.write_text(json.dumps(report, indent=2))
    write_transcript(DATA / f"transcript_{args.package}.jsonl", transcripts, append=args.append)
    print(f"\nReport: {rpt_path}  (total interactions: {cum_n})")


if __name__ == "__main__":
    main()
