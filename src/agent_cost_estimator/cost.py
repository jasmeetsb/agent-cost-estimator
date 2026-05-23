"""Turn ADK agent events into a per-query cost breakdown.

A single agent query can trigger several Gemini calls (one per reasoning turn:
tool-call decision, post-tool answer, ...). Each emits its own usage_metadata.
We sum token usage across every model event in the query, then price it with
a PriceBook. Thinking ("thoughts") tokens bill at the output rate.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .pricing import PriceBook


@dataclass
class QueryUsage:
    prompt_tokens: int = 0
    output_tokens: int = 0          # candidates + thoughts
    cached_tokens: int = 0
    thoughts_tokens: int = 0
    model_calls: int = 0

    def add_event(self, event: dict) -> None:
        um = _usage_of(event)
        if not um:
            return
        self.model_calls += 1
        prompt = int(um.get("prompt_token_count") or 0)
        cached = int(um.get("cached_content_token_count") or 0)
        cand = int(um.get("candidates_token_count") or 0)
        thoughts = int(um.get("thoughts_token_count") or 0)
        # prompt_token_count already includes cached tokens; split them so the
        # cheaper cached rate can be applied to that portion.
        self.cached_tokens += cached
        self.prompt_tokens += max(prompt - cached, 0)
        self.output_tokens += cand + thoughts
        self.thoughts_tokens += thoughts


@dataclass
class QueryCost:
    usage: QueryUsage
    input_usd: float = 0.0
    output_usd: float = 0.0
    cached_usd: float = 0.0
    runtime_usd: float = 0.0
    latency_s: float = 0.0

    @property
    def model_usd(self) -> float:
        return self.input_usd + self.output_usd + self.cached_usd

    @property
    def total_usd(self) -> float:
        return self.model_usd + self.runtime_usd

    def to_dict(self) -> dict:
        u = self.usage
        return {
            "prompt_tokens": u.prompt_tokens,
            "cached_tokens": u.cached_tokens,
            "output_tokens": u.output_tokens,
            "thoughts_tokens": u.thoughts_tokens,
            "model_calls": u.model_calls,
            "latency_s": round(self.latency_s, 3),
            "input_usd": self.input_usd,
            "output_usd": self.output_usd,
            "cached_usd": self.cached_usd,
            "runtime_usd": self.runtime_usd,
            "model_usd": self.model_usd,
            "total_usd": self.total_usd,
        }


def _usage_of(event: dict) -> dict | None:
    """Extract usage_metadata from an ADK event (dict or object)."""
    if isinstance(event, dict):
        return event.get("usage_metadata")
    return getattr(event, "usage_metadata", None)


def price_query(
    events: list,
    pb: PriceBook,
    latency_s: float = 0.0,
    runtime_vcpu: float = 1.0,
    runtime_mem_gib: float = 1.0,
) -> QueryCost:
    """Cost one query's worth of events.

    Runtime cost prorates Agent Engine vCPU/memory-seconds over the wall-clock
    latency of the query, assuming `runtime_vcpu` cores and `runtime_mem_gib`
    GiB are allocated to the instance. This is an upper-bound attribution (one
    instance fully dedicated to the request for its duration).
    """
    usage = QueryUsage()
    for ev in events:
        usage.add_event(_as_dict(ev))

    qc = QueryCost(usage=usage, latency_s=latency_s)
    if pb.input_token_usd:
        qc.input_usd = usage.prompt_tokens * pb.input_token_usd
    if pb.output_token_usd:
        qc.output_usd = usage.output_tokens * pb.output_token_usd
    if pb.cached_input_token_usd:
        qc.cached_usd = usage.cached_tokens * pb.cached_input_token_usd
    elif pb.input_token_usd:
        # Fall back to full input rate if no cache SKU resolved.
        qc.cached_usd = usage.cached_tokens * pb.input_token_usd

    if latency_s and (pb.runtime_vcpu_core_sec_usd or pb.runtime_mem_gib_sec_usd):
        vcpu = (pb.runtime_vcpu_core_sec_usd or 0) * runtime_vcpu * latency_s
        mem = (pb.runtime_mem_gib_sec_usd or 0) * runtime_mem_gib * latency_s
        qc.runtime_usd = vcpu + mem
    return qc


def _as_dict(ev) -> dict:
    if isinstance(ev, dict):
        return ev
    # vertexai stream_query yields dicts already; objects fall back to attrs.
    um = getattr(ev, "usage_metadata", None)
    if um is None:
        return {}
    if not isinstance(um, dict):
        um = {
            "prompt_token_count": getattr(um, "prompt_token_count", 0),
            "candidates_token_count": getattr(um, "candidates_token_count", 0),
            "thoughts_token_count": getattr(um, "thoughts_token_count", 0),
            "cached_content_token_count": getattr(um, "cached_content_token_count", 0),
        }
    return {"usage_metadata": um}


@dataclass
class Aggregate:
    """Average-and-spread report over N priced queries."""

    costs: list = field(default_factory=list)

    def add(self, qc: QueryCost) -> None:
        self.costs.append(qc)

    def summary(self) -> dict:
        n = len(self.costs)
        if n == 0:
            return {"n": 0}
        totals = sorted(c.total_usd for c in self.costs)
        avg = sum(totals) / n
        return {
            "n": n,
            "avg_total_usd": avg,
            "min_total_usd": totals[0],
            "max_total_usd": totals[-1],
            "p50_total_usd": totals[n // 2],
            "avg_model_usd": sum(c.model_usd for c in self.costs) / n,
            "avg_runtime_usd": sum(c.runtime_usd for c in self.costs) / n,
            "avg_prompt_tokens": sum(c.usage.prompt_tokens for c in self.costs) / n,
            "avg_output_tokens": sum(c.usage.output_tokens for c in self.costs) / n,
            "avg_model_calls": sum(c.usage.model_calls for c in self.costs) / n,
            "avg_latency_s": sum(c.latency_s for c in self.costs) / n,
            "projected_cost_per_1k_queries": avg * 1000,
        }
