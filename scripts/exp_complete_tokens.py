"""Option A: complete per-interaction CONVERSATION token capture for an agent.

Runs the agent's canonical workload N times in a single ISOLATED time window (the
caller must ensure no other gemini-2.5-flash traffic in the project during the run),
capturing BOTH:
  - stream tokens   = sum of per-event usage_metadata (what the old summaries used;
                      UNDERCOUNTS AgentTool-encapsulated sub-agent tokens), and
  - complete tokens = Cloud Monitoring `token_count` for model gemini-2.5-flash over
                      the window = EVERY model call in the tree (master + all subs,
                      incl. the AgentTool subs the stream misses).

Skips add_session_to_memory (memory-generation tokens would pollute the conversation
token_count and double-count the separately-measured Memory Bank SKU) and uses a fresh
user per interaction (clean conversation tokens). Writes data/complete_tokens_<pkg>.json
with the complete per-interaction total and the undercount factor (complete/stream).

Usage: python -u scripts/exp_complete_tokens.py --package financial_advisor --runs 80
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))  # for exp_sample

import vertexai
from vertexai import agent_engines

from agent_cost_estimator import load_or_build, price_query, build_turn, write_transcript
from agent_cost_estimator.usage import PUBLISHER_TOKEN_METRIC, MONITORING_BASE, _access_token
from exp_sample import get_scenarios, _with_retry

PROJECT, LOCATION = "jsb-genai-sa", "us-central1"
STAGING = "gs://jsb-genai-sa-staging"
DATA = Path(__file__).resolve().parents[1] / "data"
FMT = "%Y-%m-%dT%H:%M:%SZ"
CANONICAL_MODEL = "gemini-2.5-flash"


def complete_tokens(w0, w1, model=CANONICAL_MODEL, token=None):
    """token_count over [w0,w1] for one model, split input/output (the complete total)."""
    token = token or _access_token()
    params = {
        "filter": f'metric.type="{PUBLISHER_TOKEN_METRIC}"',
        "interval.startTime": w0.strftime(FMT), "interval.endTime": w1.strftime(FMT),
        "aggregation.alignmentPeriod": "60s", "aggregation.perSeriesAligner": "ALIGN_SUM",
    }
    url = f"{MONITORING_BASE}/projects/{PROJECT}/timeSeries?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    data = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    out = {"input": 0.0, "output": 0.0, "by_model": {}}
    for s in data.get("timeSeries", []):
        mid = s.get("resource", {}).get("labels", {}).get("model_user_id", "?")
        ttype = s.get("metric", {}).get("labels", {}).get("type", "")
        tot = sum(float(p["value"].get("int64Value", p["value"].get("doubleValue", 0)) or 0)
                  for p in s.get("points", []))
        out["by_model"][mid] = out["by_model"].get(mid, 0.0) + tot
        if mid == model and ttype in ("input", "output"):
            out[ttype] += tot
    out["total"] = out["input"] + out["output"]
    return out


def one_interaction(engine, pb, user, scenario, transcripts):
    in_tok = out_tok = calls = 0
    sid_holder = {}

    def _query(sid, msg):
        evs = list(engine.stream_query(user_id=user, session_id=sid, message=msg))
        if not evs:
            raise RuntimeError("RESOURCE_EXHAUSTED: empty stream (likely rate-limited)")
        return evs

    s = _with_retry(lambda: engine.create_session(user_id=user), what="create_session")
    sid = s.get("id") if isinstance(s, dict) else s.id
    sid_holder["sid"] = sid
    for msg in scenario:
        evs = _with_retry(lambda: _query(sid, msg), what="stream_query")
        qc = price_query(evs, pb)
        in_tok += qc.usage.prompt_tokens + qc.usage.cached_tokens
        out_tok += qc.usage.output_tokens
        calls += qc.usage.model_calls
        rec = build_turn(msg, evs, session_id=sid); rec["user"] = user
        transcripts.append(rec)
    # NOTE: deliberately NOT calling add_session_to_memory (avoids memory-gen token pollution).
    return {"input_tokens": in_tok, "output_tokens": out_tok, "model_calls": calls,
            "turns": len(scenario)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True)
    ap.add_argument("--runs", type=int, default=80)
    ap.add_argument("--settle", type=int, default=300)
    ap.add_argument("--delay", type=float, default=2.0)
    args = ap.parse_args()

    vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=STAGING)
    dep = json.loads((DATA / f"deployment_{args.package}.json").read_text())
    engine = agent_engines.get(dep["resource_name"])
    pb = load_or_build(CANONICAL_MODEL)
    scenarios = get_scenarios(args.package)

    win_start = datetime.now(timezone.utc) - timedelta(seconds=60)
    rows, transcripts = [], []
    stamp = int(time.time())
    for i in range(args.runs):
        scenario = scenarios[i % len(scenarios)]
        user = f"complete-{stamp}-{i}"  # fresh user each interaction
        try:
            r = one_interaction(engine, pb, user, scenario, transcripts)
            rows.append(r)
            print(f"  {args.package} {i+1}/{args.runs} turns={r['turns']} "
                  f"stream_in={r['input_tokens']} stream_out={r['output_tokens']} "
                  f"calls={r['model_calls']}", flush=True)
        except Exception as ex:
            print(f"  {args.package} {i+1}/{args.runs} FAILED: {repr(ex)[:120]}", flush=True)
        if args.delay:
            time.sleep(args.delay)

    if not rows:
        print("No successful interactions."); return
    n = len(rows)
    stream_in = sum(r["input_tokens"] for r in rows)
    stream_out = sum(r["output_tokens"] for r in rows)
    stream_total = stream_in + stream_out

    print(f"\nWaiting {args.settle}s for Monitoring ingestion...", flush=True)
    time.sleep(args.settle)
    w1 = datetime.now(timezone.utc) + timedelta(seconds=60)
    comp = complete_tokens(win_start, w1)

    factor = (comp["total"] / stream_total) if stream_total else None
    report = {
        "package": args.package, "engine": dep["resource_name"], "model": CANONICAL_MODEL,
        "n_interactions": n, "window": [win_start.strftime(FMT), w1.strftime(FMT)],
        "turns_seen": sorted(set(r["turns"] for r in rows)),
        "stream": {"input": stream_in, "output": stream_out, "total": stream_total,
                   "per_interaction": round(stream_total / n, 1)},
        "complete": {"input": int(comp["input"]), "output": int(comp["output"]),
                     "total": int(comp["total"]),
                     "per_interaction": round(comp["total"] / n, 1),
                     "per_interaction_input": round(comp["input"] / n, 1),
                     "per_interaction_output": round(comp["output"] / n, 1)},
        "undercount_factor": round(factor, 4) if factor else None,
        "token_count_by_model": {k: int(v) for k, v in comp["by_model"].items()},
    }
    out = DATA / f"complete_tokens_{args.package}.json"
    out.write_text(json.dumps(report, indent=2))
    write_transcript(DATA / f"transcript_complete_{args.package}.jsonl", transcripts, append=False)
    print(f"\n=== {args.package}: n={n} stream_total={stream_total} "
          f"complete_total={int(comp['total'])} factor={factor:.3f} ===" if factor else
          f"\n=== {args.package}: n={n} (no factor) ===")
    print("by_model:", report["token_count_by_model"])
    print("Wrote", out, flush=True)


if __name__ == "__main__":
    main()
