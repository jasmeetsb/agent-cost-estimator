"""Live GCP pricing from the Cloud Billing Catalog API.

Pulls per-unit prices for Gemini model tokens and Vertex AI Agent Engine
(ReasoningEngine) runtime, so the harness can price an agent run from its
usage_metadata without waiting for BigQuery billing-export latency.

No spend data lives in the Billing API — only catalog unit prices. Actual
token counts come from the agent response; this module turns them into dollars.
"""

from __future__ import annotations

import json
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

CATALOG_BASE = "https://cloudbilling.googleapis.com/v1"

# Catalog service IDs (stable).
SERVICE_VERTEX_AI = "C7E2-9256-1C43"

CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "sku_cache.json"


def _access_token() -> str:
    return subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def _get_json(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def fetch_all_skus(service_id: str, token: str | None = None) -> list[dict]:
    """Page through every SKU for a catalog service."""
    token = token or _access_token()
    skus: list[dict] = []
    page_token = ""
    while True:
        url = f"{CATALOG_BASE}/services/{service_id}/skus?pageSize=5000"
        if page_token:
            url += f"&pageToken={page_token}"
        data = _get_json(url, token)
        skus.extend(data.get("skus", []))
        page_token = data.get("nextPageToken", "")
        if not page_token:
            break
    return skus


def _unit_price_usd(sku: dict) -> float | None:
    """Highest-tier unit price in USD (the marginal/standard rate)."""
    pricing = sku.get("pricingInfo")
    if not pricing:
        return None
    expr = pricing[0].get("pricingExpression", {})
    tiers = expr.get("tieredRates", [])
    if not tiers:
        return None
    up = tiers[-1].get("unitPrice", {})
    units = int(up.get("units", 0))
    nanos = int(up.get("nanos", 0))
    return units + nanos / 1e9


def _usage_unit(sku: dict) -> str:
    pricing = sku.get("pricingInfo")
    if not pricing:
        return ""
    return pricing[0].get("pricingExpression", {}).get("usageUnitDescription", "")


@dataclass
class PriceBook:
    """Resolved unit prices the harness actually needs.

    Token prices are USD per single token (catalog unit is "count" = 1 token).
    Runtime prices are USD per gibibyte-second (memory) and per core-second (vCPU).
    """

    model: str
    input_token_usd: float | None = None
    output_token_usd: float | None = None
    cached_input_token_usd: float | None = None
    runtime_mem_gib_sec_usd: float | None = None
    runtime_vcpu_core_sec_usd: float | None = None
    # Agent Engine operation SKUs (memory bank + session persistence).
    memory_retrieved_usd: float | None = None       # per memory retrieved
    memory_stored_month_usd: float | None = None     # per memory stored, per month
    session_event_usd: float | None = None           # per session event appended
    raw_matches: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "input_token_usd": self.input_token_usd,
            "output_token_usd": self.output_token_usd,
            "cached_input_token_usd": self.cached_input_token_usd,
            "runtime_mem_gib_sec_usd": self.runtime_mem_gib_sec_usd,
            "runtime_vcpu_core_sec_usd": self.runtime_vcpu_core_sec_usd,
            "memory_retrieved_usd": self.memory_retrieved_usd,
            "memory_stored_month_usd": self.memory_stored_month_usd,
            "session_event_usd": self.session_event_usd,
        }


# Family aliases -> the phrase used in catalog SKU descriptions.
_MODEL_ALIASES = {
    "gemini-2.5-flash": "gemini 2.5 flash",
    "gemini-2.5-pro": "gemini 2.5 pro",
    "gemini-2.0-flash": "gemini 2.0 flash",
    "gemini-2.0-flash-lite": "gemini 2.0 flash lite",
}


def _match_token_skus(skus: list[dict], phrase: str) -> dict[str, float]:
    """Find on-demand (Predictions, not Batch) text token SKUs for a model.

    Excludes batch, audio, video, image, and live SKUs to isolate the standard
    text input/output/cache rates that a typical text agent incurs. Also guards
    against substring collisions (e.g. "flash" matching "flash lite").
    """
    want_lite = "lite" in phrase
    out: dict[str, float] = {}
    for s in skus:
        d = s.get("description", "").lower().strip()
        if phrase not in d:
            continue
        # Avoid "gemini 2.5 flash" capturing "gemini 2.5 flash lite" SKUs.
        if ("flash lite" in d) and not want_lite:
            continue
        if "batch" in d or "live" in d:
            continue
        if any(m in d for m in ("audio", "video", "image")):
            continue
        if "token" not in d and "predictions" not in d:
            continue
        price = _unit_price_usd(s)
        if price is None:
            continue
        out[s.get("description", "")] = price
    return out


def build_pricebook(model: str, skus: list[dict] | None = None) -> PriceBook:
    """Resolve the prices needed to cost a text agent run for `model`."""
    if skus is None:
        skus = fetch_all_skus(SERVICE_VERTEX_AI)

    phrase = _MODEL_ALIASES.get(model)
    if phrase is None:
        # Best-effort: derive a phrase from the model id.
        phrase = model.replace("-", " ").replace("gemini ", "gemini ").lower()

    pb = PriceBook(model=model)
    matches = _match_token_skus(skus, phrase)
    pb.raw_matches = matches

    pb.input_token_usd = _pick(matches, kind="input")
    pb.output_token_usd = _pick(matches, kind="output")
    pb.cached_input_token_usd = _pick(matches, kind="cache")

    _resolve_runtime(skus, pb)
    _resolve_agent_ops(skus, pb)
    return pb


def _resolve_agent_ops(skus: list[dict], pb: PriceBook) -> None:
    """Resolve Agent Engine memory-bank + session operation SKUs."""
    for s in skus:
        d = s.get("description", "").lower()
        price = _unit_price_usd(s)
        if price is None:
            continue
        if "memory bank memories retrieved" in d:
            pb.memory_retrieved_usd = price
        elif "memory bank memories stored" in d:
            pb.memory_stored_month_usd = price
        elif "sessions events appended" in d:
            pb.session_event_usd = price


def _pick(matches: dict[str, float], kind: str) -> float | None:
    """Deterministically choose the standard on-demand SKU for a token kind.

    Scores candidates so the current GA, non-tiered, non-thinking text rate
    wins over preview/priority/flex/long/thinking variants.
    """
    cands = []
    for desc, price in matches.items():
        dl = desc.lower()
        is_cache = "cach" in dl
        is_output = "output" in dl
        is_input = "input" in dl and not is_cache
        if kind == "cache" and not (is_cache and "input" in dl):
            continue
        if kind == "output" and not is_output:
            continue
        if kind == "input" and not is_input:
            continue
        score = 0
        if "ga" in dl.split():
            score += 4
        for bad in ("priority", "flex", "regional", "global", "(long)",
                    "thinking", "thinking on"):
            if bad in dl:
                score -= 1
        cands.append((score, -len(dl), price))
    if not cands:
        return None
    cands.sort(reverse=True)
    return cands[0][2]


def _resolve_runtime(skus: list[dict], pb: PriceBook) -> None:
    for s in skus:
        d = s.get("description", "").lower()
        if "reasoningengine" not in d.replace(" ", ""):
            continue
        price = _unit_price_usd(s)
        if price is None:
            continue
        unit = _usage_unit(s).lower()
        if "gibibyte" in unit:
            pb.runtime_mem_gib_sec_usd = price
        elif "second" in unit or "core" in unit or "cpu" in unit:
            pb.runtime_vcpu_core_sec_usd = price


def load_or_build(model: str, refresh: bool = False) -> PriceBook:
    """Build a pricebook, caching the raw SKU pull for reuse across models."""
    if not refresh and CACHE_PATH.exists():
        cached = json.loads(CACHE_PATH.read_text())
        skus = cached.get("skus", [])
        ts = cached.get("fetched_at", 0)
        if skus and (time.time() - ts) < 86400:
            return build_pricebook(model, skus)
    skus = fetch_all_skus(SERVICE_VERTEX_AI)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps({"fetched_at": time.time(), "skus": skus}))
    return build_pricebook(model, skus)


if __name__ == "__main__":
    import sys
    m = sys.argv[1] if len(sys.argv) > 1 else "gemini-2.5-flash"
    pb = load_or_build(m, refresh="--refresh" in sys.argv)
    print(json.dumps(pb.to_dict(), indent=2))
    print(f"\nMatched {len(pb.raw_matches)} token SKUs:")
    for k, v in sorted(pb.raw_matches.items()):
        print(f"  {v:.12f}  {k}")
