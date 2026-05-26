"""Collect ACTUAL resource usage per SKU from Cloud Monitoring.

Token usage comes from the agent response (`usage_metadata`) — exact and
attributable per query. But Agent Engine **runtime** (vCPU + memory) is billed
for the instance being up regardless of requests, so it is not visible in any
response; the only source is Cloud Monitoring's `reasoning_engine/*` metrics.

This module queries Monitoring time series scoped to a specific reasoning engine
and time window, returning real consumption quantities that map directly onto
the billable runtime SKUs. Combined with PriceBook rates this yields a runtime
cost based on *actual* allocation rather than a prorated per-query guess.
"""

from __future__ import annotations

import json
import subprocess
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

MONITORING_BASE = "https://monitoring.googleapis.com/v3"

# Agent Engine runtime metrics -> the SKU dimension they bill against.
RUNTIME_METRICS = {
    "cpu_core_seconds": "aiplatform.googleapis.com/reasoning_engine/cpu/allocation_time",
    "memory_gib_seconds": "aiplatform.googleapis.com/reasoning_engine/memory/allocation_time",
    "request_count": "aiplatform.googleapis.com/reasoning_engine/request_count",
}

# Project+region aggregate token counter (NOT scoped to one engine — see
# COST_DATA_COLLECTION_PROCESS.md §3). Used only as a cross-check against the
# per-query usage_metadata totals.
PUBLISHER_TOKEN_METRIC = "aiplatform.googleapis.com/publisher/online_serving/token_count"

# Agent Engine Memory Bank metrics (scoped per reasoning_engine_id). These
# capture the extra cost of long-term memory: the LLM tokens spent generating
# memories from a session, plus memory write/read operation counts.
MEMORY_METRICS = {
    "generate_memories_token_count":
        "aiplatform.googleapis.com/reasoning_engine/memory_bank/generate_memories_token_count",
    "memory_mutation_count":
        "aiplatform.googleapis.com/reasoning_engine/memory_bank/memory_mutation_count",
    "memory_retrieval_count":
        "aiplatform.googleapis.com/reasoning_engine/memory_bank/memory_retrieval_count",
}


def _access_token() -> str:
    return subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def _sum_timeseries(
    project: str, metric_type: str, engine_id: str,
    start: str, end: str, token: str,
) -> float:
    """Sum a metric over [start, end] for one reasoning engine.

    start/end are RFC3339 (e.g. 2026-05-23T00:00:00Z). Uses a single alignment
    bucket spanning the window and sums across any matching series.
    """
    flt = (f'metric.type="{metric_type}" AND '
           f'resource.labels.reasoning_engine_id="{engine_id}"')
    # Use fine (60s) alignment and sum the points that fall inside [start,end].
    # A coarse alignmentPeriod (e.g. 24h) buckets far more than the window and
    # silently over/undercounts — the interval does not bound an oversized bucket.
    params = {
        "filter": flt,
        "interval.startTime": start,
        "interval.endTime": end,
        "aggregation.alignmentPeriod": "60s",
        "aggregation.perSeriesAligner": "ALIGN_SUM",
    }
    url = f"{MONITORING_BASE}/projects/{project}/timeSeries?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    total = 0.0
    for series in data.get("timeSeries", []):
        for p in series.get("points", []):
            v = p.get("value", {})
            total += float(v.get("doubleValue", v.get("int64Value", 0)) or 0)
    return total


@dataclass
class ActualRuntimeUsage:
    engine_id: str
    start: str
    end: str
    cpu_core_seconds: float = 0.0
    memory_gib_seconds: float = 0.0
    request_count: float = 0.0
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "engine_id": self.engine_id,
            "window": [self.start, self.end],
            "cpu_core_seconds": self.cpu_core_seconds,
            "memory_gib_seconds": self.memory_gib_seconds,
            "request_count": self.request_count,
        }


def collect_runtime_usage(
    project: str, engine_id: str, start: str, end: str,
    token: str | None = None,
) -> ActualRuntimeUsage:
    """Pull actual Agent Engine vCPU/memory/request usage over a window."""
    token = token or _access_token()
    u = ActualRuntimeUsage(engine_id=engine_id, start=start, end=end)
    for field_name, metric in RUNTIME_METRICS.items():
        val = _sum_timeseries(project, metric, engine_id, start, end, token)
        setattr(u, field_name, val)
        u.raw[metric] = val
    return u


def collect_memory_usage(
    project: str, engine_id: str, start: str, end: str, token: str | None = None,
) -> dict:
    """Pull Agent Engine Memory Bank usage over a window, scoped to one engine."""
    token = token or _access_token()
    out = {}
    for name, metric in MEMORY_METRICS.items():
        out[name] = _sum_timeseries(project, metric, engine_id, start, end, token)
    return out


def price_memory_usage(memory_usage: dict, pb, session_events: int = 0) -> dict:
    """Price Memory Bank + session-persistence usage.

    - generate_memories tokens: priced at the INPUT token rate. The metric gives a
      single total (no in/out split); memory extraction is input-dominated (it reads
      the session), so input rate is the best single-rate proxy. Flagged below.
    - memories retrieved: per-retrieval op rate.
    - memories stored: a MONTHLY per-memory charge — not a per-run cost. We surface
      the write count (mutations) and the monthly rate but do not fold a monthly
      charge into a per-run total.
    - session events appended: per-event rate. Count is approximate (observed events;
      no Cloud Monitoring metric exists — authoritative count is billing-export-only).
    """
    gen_tok = memory_usage.get("generate_memories_token_count", 0) or 0
    retrieved = memory_usage.get("memory_retrieval_count", 0) or 0
    mutations = memory_usage.get("memory_mutation_count", 0) or 0

    gen_tok_usd = gen_tok * (pb.input_token_usd or 0)
    retrieved_usd = retrieved * (pb.memory_retrieved_usd or 0)
    session_usd = session_events * (pb.session_event_usd or 0)

    return {
        "generate_memories_tokens": gen_tok,
        "generate_memories_usd": gen_tok_usd,
        "generate_memories_priced_at": "input_token_rate (no in/out split available)",
        "memories_retrieved": retrieved,
        "memories_retrieved_usd": retrieved_usd,
        "session_events_observed": session_events,
        "session_events_usd": session_usd,
        "session_events_note": "approximate; no Monitoring metric, authoritative count is export-only",
        "memories_written": mutations,
        "memory_stored_month_usd_rate": pb.memory_stored_month_usd,
        "memory_storage_note": "monthly per-memory charge, not a per-run cost; needs export for true stored count",
        "per_run_memory_usd": gen_tok_usd + retrieved_usd + session_usd,
    }


def collect_publisher_tokens(
    project: str, start: str, end: str, token: str | None = None,
) -> dict:
    """Sum project+region-wide Gemini token usage over a window, split in/out.

    NOT engine-scoped — this aggregates every Gemini call in the project for the
    window. Use only to cross-check usage_metadata totals when the test agent is
    the sole source of traffic in the window.
    """
    token = token or _access_token()
    params = {
        "filter": f'metric.type="{PUBLISHER_TOKEN_METRIC}"',
        "interval.startTime": start,
        "interval.endTime": end,
        "aggregation.alignmentPeriod": "60s",
        "aggregation.perSeriesAligner": "ALIGN_SUM",
    }
    url = f"{MONITORING_BASE}/projects/{project}/timeSeries?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    out = {"input": 0.0, "output": 0.0}
    for series in data.get("timeSeries", []):
        ttype = series.get("metric", {}).get("labels", {}).get("type", "")
        s = 0.0
        for p in series.get("points", []):
            v = p.get("value", {})
            s += float(v.get("doubleValue", v.get("int64Value", 0)) or 0)
        if ttype in out:
            out[ttype] += s
    out["total"] = out["input"] + out["output"]
    return out


def price_runtime(usage: ActualRuntimeUsage, pb) -> dict:
    """Cost actual runtime usage with catalog rates.

    Returns total window cost and a per-request amortization (window cost split
    over the requests served in the window) — the realistic "cost per query"
    once continuous/idle allocation is accounted for.
    """
    cpu_usd = usage.cpu_core_seconds * (pb.runtime_vcpu_core_sec_usd or 0)
    mem_usd = usage.memory_gib_seconds * (pb.runtime_mem_gib_sec_usd or 0)
    total = cpu_usd + mem_usd
    per_req = total / usage.request_count if usage.request_count else None
    return {
        "cpu_usd": cpu_usd,
        "memory_usd": mem_usd,
        "runtime_total_usd": total,
        "request_count": usage.request_count,
        "runtime_usd_per_request_amortized": per_req,
    }
