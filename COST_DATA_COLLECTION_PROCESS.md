# Cost Data Collection Process

How this project measures the cost of an agent: how experiments run, how usage
is collected, how it's priced, and — critically — **which numbers are estimates
vs. actual billed amounts from the GCP project**.

> TL;DR: We combine two sources. **Token usage** is exact (from the agent
> response) but priced at **public catalog list price** (not the project's actual
> billed rate). **Runtime usage** (Agent Engine vCPU + memory) is now **actual** —
> read from Cloud Monitoring's `reasoning_engine/*` allocation metrics (see §6a) —
> also priced at catalog rate. We still do **not** read actual billed *dollars*;
> that requires BigQuery billing export, which is not set up (see §7).

---

## 1. End-to-end pipeline

```
                 ┌─────────────────────────────────────────────┐
                 │ Cloud Billing Catalog API (cloudbilling)     │  ← PRICES (public list)
                 │   services/{id}/skus  →  unit price per SKU  │
                 └───────────────────────┬─────────────────────┘
                                         │  pricing.py (cache 24h → data/sku_cache.json)
                                         ▼
  workload ──► agent (local AdkApp OR    │   PriceBook{input$, output$, cache$, runtime$}
              deployed Agent Engine) ──► events[] with usage_metadata  ← USAGE (per query)
                                         │
                                         ▼  cost.py
                       per-query QueryCost = usage × prices + prorated runtime
                                         │
                                         ▼  harness.py
                       Aggregate → avg $/query, $/1k, token & latency stats
                                         │
                                         ▼
                       data/cost_report_{mode}.json  +  PROJECT_RUNBOOK.md row
```

Two independent data streams meet in `cost.py`:
- **Usage** — *how much* the agent consumed (tokens, calls, latency). Measured per query.
- **Prices** — *how much each unit costs* (public catalog list price). Fetched live, cached.

Cost = usage × price. Neither stream reads actual billed spend.

---

## 2. Running an experiment

```bash
. .venv/bin/activate
python scripts/harness.py --mode local  --iters 5   # in-process AdkApp, no deploy
python scripts/harness.py --mode remote --iters 5   # queries deployed Agent Engine
```

- **Workload**: a fixed list of prompts in `harness.py:WORKLOAD` (currently 5 mixed
  weather/timezone queries, including one that hits the agent's no-data path). Iterations
  cycle through the list (`WORKLOAD[i % len]`).
- **Modes**:
  - `local` — runs the agent in-process via `reasoning_engines.AdkApp`. Real Gemini API
    calls (real token usage + real model cost basis), but **no Agent Engine runtime** — so
    the runtime portion of the estimate is synthetic and latency reflects your machine.
  - `remote` — calls the deployed Agent Engine endpoint (`data/deployment.json`). This is
    the representative path: real network round-trip, real server-side latency, real runtime.
- **Per query** the harness records: token counts, model-call count, wall-clock latency, and
  the priced breakdown. Results are written to `data/cost_report_{mode}.json` and summarized.

---

## 3. Usage collection (the "how much consumed" stream)

Source: every ADK event carries a `usage_metadata` block from the Gemini backend. `cost.py`
walks **all** events in a query and sums them (`QueryUsage.add_event`).

Fields consumed per model call:

| Field | Meaning | How we use it |
|-------|---------|---------------|
| `prompt_token_count` | input tokens (incl. cached) | input cost; we subtract cached to avoid double-count |
| `cached_content_token_count` | cached input tokens | priced at cache rate (or input rate if no cache SKU) |
| `candidates_token_count` | output/answer tokens | output cost |
| `thoughts_token_count` | thinking tokens | added to output (bills at output rate) |
| `total_token_count` | sanity check only | not used directly |
| `traffic_type` | `ON_DEMAND` vs provisioned | confirms we use on-demand SKUs |

**Key correctness points** (see Learnings Log in the runbook):
- One query = **multiple model calls**. A tool-using turn makes ≥2 calls; we sum every one.
- Thinking tokens are billed but live in a separate field; we fold them into output.
- This is **directly measured per query**, not sampled or estimated — the token counts are
  exactly what Gemini reports.

What usage we do **not** yet collect: tool-side compute, embedding/search calls (this agent
has none), or any usage outside the model response stream.

---

## 4. Price collection (the "what a unit costs" stream)

Source: **Cloud Billing Catalog API** — `GET cloudbilling.googleapis.com/v1/services/{id}/skus`.
This returns **public list prices**, not your negotiated/internal rates and not actual spend.

`pricing.py`:
1. Pages through all SKUs for the Vertex AI service (`C7E2-9256-1C43`), caches raw to
   `data/sku_cache.json` (24 h TTL).
2. For a given model (e.g. `gemini-2.5-flash`) selects the standard on-demand **text** SKUs:
   - filters out batch, live, audio/video/image, and "flash lite" collisions;
   - scores candidates so the **GA**, non-priority, non-flex, non-thinking, non-long SKU wins;
   - extracts the highest-tier unit price (USD per single token; catalog unit = "count").
3. Resolves runtime SKUs (`ReasoningEngine` management fee) → USD per vCPU-core-second and per
   GiB-memory-second.

Result is a `PriceBook`:
```
input_token_usd, output_token_usd, cached_input_token_usd,
runtime_vcpu_core_sec_usd, runtime_mem_gib_sec_usd
```

Verified against published Vertex pricing (2.5-flash $0.30/$2.50, 2.5-pro $1.25/$10 per 1M).

---

## 5. Cost computation — per product / SKU

`cost.py:price_query` produces this breakdown per query:

| Cost component | Product / SKU family | Formula | Estimate or Actual? |
|----------------|----------------------|---------|---------------------|
| `input_usd` | Vertex AI — Gemini text **input** | `prompt_tokens × input_token_usd` | **Estimate** (measured usage × list price) |
| `output_usd` | Vertex AI — Gemini text **output** (incl. thinking) | `(candidates + thoughts) × output_token_usd` | **Estimate** |
| `cached_usd` | Vertex AI — Gemini **cached input** | `cached_tokens × cache_rate` | **Estimate** |
| `runtime_usd` | Agent Engine — ReasoningEngine vCPU + memory | `latency × (vcpu_rate×nCPU + mem_rate×GiB)` | **Estimate (rough)** — see §6 |
| `model_usd` | sum of the three token components | — | **Estimate** |
| `total_usd` | `model_usd + runtime_usd` | — | **Estimate** |

`Aggregate.summary()` then reports avg/min/max/p50 total, avg per-component, avg tokens, avg
model calls, avg latency, and a `projected_cost_per_1k_queries`.

---

## 6. Estimate vs Actual — the honest accounting

### What is an ESTIMATE (everything we currently report)
- **All token costs** — usage is exact (Gemini-reported), but the **price** is public list
  price from the catalog, not what `jsb-genai-sa` is actually charged. On an internal corp
  project the real charge may be $0 or an internal-cost rate. We deliberately report the
  "list-price equivalent" (what an external customer would pay).
- **Runtime cost** — doubly approximate:
  1. We **assume 1 vCPU + 1 GiB**. We have **not** confirmed the deployed Agent Engine
     instance's actual CPU/memory allocation.
  2. We **prorate by request wall-clock latency**, treating one instance as fully dedicated to
     the request. Real Agent Engine billing is **provisioned instance-time** (the instance is
     billed while it's up, across all requests and idle periods), so true per-query runtime is
     `instance_cost_over_window / queries_in_window` — which drops sharply at higher QPS and
     rises with idle time. Our number is an **upper bound per request**, not the amortized cost.

### What we currently do NOT capture at all (real costs, not in our estimate)
These are consumed by the experiment but absent from `total_usd`:
- **Cloud Storage** — the staging bucket (`gs://jsb-genai-sa-staging`) holds the deploy package.
- **Artifact Registry / Cloud Build** — building the agent container on deploy.
- **Cloud Logging** — Agent Engine logs (we read these for debugging).
- **Cloud Trace** — we deployed with `enable_tracing=True`, which emits traces (billable).
- **Network egress** — responses leaving the region/project.
- **Idle Agent Engine runtime** — time the engine is up but not serving our queries.

### What would be ACTUAL billed spend (not yet wired up)
- **Nothing in the current pipeline reads actual spend.** The standard Cloud Billing API does
  not expose spend amounts. The only authoritative source is **BigQuery billing export** (§7),
  which is not configured and is likely locked on the shared corp billing account.

### Summary
| Question | Answer today |
|----------|--------------|
| Are token *usage counts* real? | **Yes** — exact, from the agent response. |
| Are token *prices* real for this project? | **No** — public list price, not the project's actual rate. |
| Is runtime cost real? | **No** — assumed instance size + per-request proration. |
| Do we capture storage/logging/trace/egress/build? | **No.** |
| Do we read any actual billed dollars from GCP? | **No.** |

---

## 6a. How we access ACTUAL usage data (Cloud Monitoring)

This section documents exactly how actual resource usage was discovered and is
retrieved, so it can be reproduced and extended to other products.

### The source: Cloud Monitoring time series
Every GCP service emits usage/operational metrics to Cloud Monitoring
(`monitoring.googleapis.com`, already enabled on `jsb-genai-sa`). For Agent Engine,
the relevant metrics are under the `aiplatform.googleapis.com/reasoning_engine/`
namespace and are **scoped per engine** via the `reasoning_engine_id` resource label.

### Access requirements (what made this work)
- **API enabled:** `monitoring.googleapis.com` (was already on).
- **IAM:** the caller needs `monitoring.timeSeries.list` (e.g. `roles/monitoring.viewer`)
  on the project. Our user account (`jasmeetbhatia@google.com`) already had read access
  to the project, so no grant was needed.
- **Auth:** a standard OAuth access token from `gcloud auth print-access-token`.
- Notably this needs **only project-level monitoring read** — *not* billing-account
  admin. That's why it works here even though BigQuery billing export (which needs
  billing-account admin) does not.

### Step 1 — discover the available metrics
List metric descriptors for the Vertex/Agent Engine namespace:
```bash
TOKEN=$(gcloud auth print-access-token)
curl -s "https://monitoring.googleapis.com/v3/projects/jsb-genai-sa/metricDescriptors\
?filter=metric.type%3Dstarts_with(%22aiplatform.googleapis.com%22)&pageSize=300" \
  -H "Authorization: Bearer $TOKEN"
```
This surfaced the metrics that map onto billable runtime SKUs:
| Metric type | Unit | Maps to SKU |
|-------------|------|-------------|
| `aiplatform.googleapis.com/reasoning_engine/cpu/allocation_time` | `s{CPU}` (vCPU-seconds) | Agent Engine vCPU |
| `aiplatform.googleapis.com/reasoning_engine/memory/allocation_time` | `GiBy.s` (GiB-seconds) | Agent Engine memory |
| `aiplatform.googleapis.com/reasoning_engine/request_count` | `1` | (denominator for per-query amortization) |

(Gemini token metrics also exist — `publisher/online_serving/token_count`,
`model_invocation_count` — but those are project-wide and mix in other engines'
traffic, so we keep using per-query `usage_metadata` for tokens, §3.)

### Step 2 — query actual usage over a window, scoped to our engine
`timeSeries.list` with a filter on metric type **and** `reasoning_engine_id`, summed
over the experiment window:
```bash
curl -s -G "https://monitoring.googleapis.com/v3/projects/jsb-genai-sa/timeSeries" \
  --data-urlencode 'filter=metric.type="aiplatform.googleapis.com/reasoning_engine/memory/allocation_time" AND resource.labels.reasoning_engine_id="1787773471170756608"' \
  --data-urlencode "interval.startTime=2026-05-23T03:29:16Z" \
  --data-urlencode "interval.endTime=2026-05-23T06:29:16Z" \
  --data-urlencode "aggregation.alignmentPeriod=86400s" \
  --data-urlencode "aggregation.perSeriesAligner=ALIGN_SUM" \
  -H "Authorization: Bearer $TOKEN"
```
This is wrapped in code at `src/agent_cost_estimator/usage.py`
(`collect_runtime_usage()` + `price_runtime()`).

### Step 3 — result (validated against our run)
For engine `1787773471170756608` over a 3-hour window containing 5 queries:
- memory = **77,677 GiB-seconds** (~7.2 GiB allocated continuously)
- vCPU = **258.6 core-seconds**
- request_count = **5** (matches the 5 queries we sent ✓)
- Priced at catalog rate: memory $0.194 + vCPU $0.0062 = **$0.200 runtime over the window**
  → **$0.040 / query** amortized over 5 requests.

### Gotchas observed
- **Ingestion lag:** immediately after the run, `request_count` and `cpu/allocation_time`
  read `0`; after ~3-5 minutes they populated (5 requests, 258 CPU-sec). Always let
  Monitoring settle before pulling, or the window will undercount.
- **Continuous allocation:** `memory/allocation_time` accrues whether or not requests
  arrive — the instance is billed for being up. This is why actual runtime ($0.040/query
  at 5 q/3h) is ~450× the naive per-request estimate, and why **utilization
  (queries/hour) must be a parameter of any "cost per query" claim.**
- **Per-engine scoping is essential:** without the `reasoning_engine_id` filter the
  series includes other engines on the project (e.g. an unrelated "Beads Issue Tracker"
  engine was visible in the raw query).

### What this gives us (actual) vs still doesn't
- **Actual:** runtime resource *quantities* (vCPU-sec, GiB-sec, requests) for our engine.
- **Still catalog-priced:** the per-unit price is list price, not the project's billed rate.
- **Still not captured via Monitoring here:** Cloud Storage, Artifact Registry/Build,
  Logging, Trace, egress — each has its own Monitoring metrics that could be added the
  same way, but they aren't wired in yet.

---

## 7. Path to ACTUAL billing dollars (future work)

To validate estimates against ground truth:
1. **Enable BigQuery billing export** on billing account `01CA82-0CFAFB-FC57E0`
   (Billing → Billing export → BigQuery export → Standard + Detailed usage cost). Requires
   billing-account admin — likely **not available** on this shared corp account.
2. Once flowing (data lands daily, delayed hours), query the export table filtered to
   `project.id = 'jsb-genai-sa'` and a time window around the experiment:
   ```sql
   SELECT service.description, sku.description,
          SUM(cost) AS cost, SUM(usage.amount) AS usage_amount, usage.unit
   FROM `PROJECT.DATASET.gcp_billing_export_resource_v1_XXXX`
   WHERE project.id = 'jsb-genai-sa'
     AND usage_start_time BETWEEN @start AND @end
   GROUP BY 1,2, usage.unit ORDER BY cost DESC;
   ```
3. **Reconcile** per-SKU actuals against the harness estimate. Caveats: export is daily-grained
   and delayed (no per-query attribution), and mixes in other workloads on the same project
   unless isolated by resource labels or a dedicated project.

**Alternative for finer attribution:** label/resource-scope the agent (or run experiments in a
dedicated project) so export rows are cleanly attributable to a run, and use Cloud Monitoring
token metrics for near-real-time usage cross-checks.

---

## 8. Reproducing a run / where the data lives
- Resolved prices: `python src/agent_cost_estimator/pricing.py <model>`
- Raw SKU cache: `data/sku_cache.json` (delete or `--refresh` to refetch)
- Per-run reports: `data/cost_report_local.json`, `data/cost_report_remote.json`
- Deployed engine id: `data/deployment.json`
- Narrative + results history: `PROJECT_RUNBOOK.md`
