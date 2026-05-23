# Project Runbook — agent-cost-estimator

Single source of truth for this project: what we're building, what we've decided,
what we've learned, and the results of each experiment. Append to the relevant
section as work proceeds. Newest entries on top within each log.

**Objective:** A harness that takes an agent architecture, deploys it to GCP
(Vertex AI Agent Engine), runs N query iterations, and reports an estimated
average cost per query — broken down by the GCP products the agent consumes.

---

## 1. Key Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-23 | Deploy target = **Vertex AI Agent Engine** | Native ADK runtime; exposes `usage_metadata` per query; runtime billed by vCPU/RAM-hr (extractable). |
| 2026-05-23 | Primary cost method = **token-based catalog estimate** | Instant, per-query, works on internal projects with no billing-export access. BigQuery export deferred as optional ground-truth. |
| 2026-05-23 | Pricing source = **Cloud Billing Catalog API** | Programmatic live unit prices for tokens + runtime; no setup or data-latency. |
| 2026-05-23 | Runtime cost = **prorated wall-clock × assumed 1 vCPU + 1 GiB** | Initial estimate; SUPERSEDED below. |
| 2026-05-23 | Runtime usage = **actual, from Cloud Monitoring `reasoning_engine/*` allocation metrics** | Only needs project-level monitoring read (not billing admin); gives real vCPU-sec + GiB-sec per engine. Replaces the prorated guess (which was ~450× too low). |
| 2026-05-23 | "Cost per query" **must include utilization (queries/hour)** | Agent Engine bills continuous allocation; idle runtime dominates at low QPS, tokens dominate at high QPS. |

---

## 2. Research Notes

### Cost-data extraction paths (and what each can actually do)
- **Billing Catalog API** (`cloudbilling.googleapis.com/v1/services/{id}/skus`) — live per-unit
  **prices** only (no spend). Works now. Vertex AI service id = `C7E2-9256-1C43`; Gemini API =
  `AEFD-7695-64FA`; "Agentic Applications" = `E4EE-DF31-DCDA`. Token unit = "count" (1 token).
- **`usage_metadata` on agent responses** — per-query token counts (prompt, candidates, thoughts,
  cached). Native to ADK/Gemini.
- **BigQuery billing export** — the only **authoritative spend** source (per-SKU, per-resource,
  daily, labeled). NOT set up; requires billing-account admin; daily-grained + delayed; likely
  locked on the shared corp billing account `01CA82-0CFAFB-FC57E0`.
- **Standard Cloud Billing API returns NO spend amounts** — only account metadata + catalog.

### Environment facts
- Project `jsb-genai-sa`, billing account `01CA82-0CFAFB-FC57E0`, billing enabled.
- Enabled APIs incl. `aiplatform` (Agent Engine), `discoveryengine` (Gemini Enterprise),
  `bigquery`, `monitoring`. `cloudbilling` enabled this session.
- Region `us-central1`; staging bucket `gs://jsb-genai-sa-staging` (us-central1).
- This is an internal `@google.com` project — dollar figures may be internal-cost, not list price.
  The catalog-price model gives the "what a customer would pay" estimate, which is the intent.

### Verified Gemini list prices (per 1M tokens, GA, on-demand text)
| Model | Input | Output |
|-------|-------|--------|
| gemini-2.5-flash | $0.30 | $2.50 |
| gemini-2.5-pro | $1.25 | $10.00 |
| gemini-2.0-flash | $0.15 | $0.60 |

Agent Engine runtime: ~$2.4e-5/vCPU-core-sec, ~$2.5e-6/GiB-mem-sec (from ReasoningEngine SKUs).

---

## 3. Learnings Log

- **2026-05-23 — Actual runtime usage lives in Cloud Monitoring, not billing.** The
  `aiplatform.googleapis.com/reasoning_engine/{cpu,memory}/allocation_time` metrics give real
  vCPU-sec / GiB-sec per `reasoning_engine_id`. Accessible with project-level monitoring read —
  no billing-account admin needed. See COST_DATA_COLLECTION_PROCESS.md §6a for the exact queries.
- **2026-05-23 — Idle runtime dominates cost at low QPS.** Our engine held ~7.2 GiB allocated
  continuously; 5 queries over 3 h ⇒ $0.040/query runtime vs ~$0.0003 tokens. Naive per-request
  runtime estimate was ~450× too low. Always report cost against a utilization assumption.
- **2026-05-23 — Monitoring ingestion lag ~3-5 min.** `request_count`/`cpu` read 0 immediately
  after a run, then populate. Let metrics settle before collecting, or scope a generous window.
- **2026-05-23 — Scope Monitoring by `reasoning_engine_id`.** Unfiltered series include other
  engines on the project (e.g. an unrelated "Beads Issue Tracker").
- **2026-05-23 — One query ≠ one model call.** A tool-using query emits 2+ model events, each with
  its own `usage_metadata`. Must sum across all events; reading only the last undercounts.
- **2026-05-23 — Thinking tokens bill at output rate.** `thoughts_token_count` is separate from
  `candidates_token_count`; add it to output tokens.
- **2026-05-23 — Deploy serialization trap.** Tool functions in a module serialize *by reference*,
  so the module must exist in the container. Fix: `os.chdir(agents/)` + `extra_packages=["weather_agent"]`
  → lands at `/code/weather_agent`. Symptom otherwise: engine builds OK but fails to start with
  `ModuleNotFoundError: No module named 'weather_agent'` (visible only in Cloud Logging, not the create call).
- **2026-05-23 — SKU name collisions.** "gemini 2.5 flash" substring-matches "flash lite"; preview
  vs GA SKUs differ in price. Filter lite, score GA highest (see `pricing.py`).
- **2026-05-23 — Background `| tee` masks exit codes.** The deploy "succeeded" (exit 0) but had
  actually failed; the python error was hidden by the pipe. Check the log content, not just exit code.

---

## 4. Experiment Log

### EXP-001 — Baseline: weather_agent, gemini-2.5-flash
- **Date:** 2026-05-23
- **Agent:** `weather_agent` (2 tools: get_weather, get_timezone), single LlmAgent.
- **Workload:** 5 mixed weather/timezone queries (incl. one no-data path).
- **Engine:** `reasoningEngines/1787773471170756608`

| Mode | Avg $/query | $/1k queries | Avg in/out tok | Calls/query | Avg latency |
|------|-------------|--------------|----------------|-------------|-------------|
| local | $0.000441 | $0.44 | 407 / 82 | 2.0 | 4.27s |
| remote | $0.000406 | $0.41 | 400 / 77 | 2.0 | 3.52s |

- Model cost dominates (~$0.00031); runtime ~$0.00009 (prorated, upper bound).
- Local vs remote agree within noise → token cost model is consistent.
- Reports: `data/cost_report_local.json`, `data/cost_report_remote.json`.

**Actual runtime (Cloud Monitoring, 3 h window, same 5 queries):**
- memory = 77,677 GiB-sec (~7.2 GiB continuous), vCPU = 258.6 core-sec, request_count = 5 ✓
- Priced: memory $0.194 + vCPU $0.0062 = **$0.200 runtime over window** → **$0.040/query** amortized.
- ⇒ Actual runtime/query is ~450× the prorated estimate; idle allocation dominates at this QPS.

<!-- Template for new experiments:
### EXP-NNN — <title>
- Date / Agent / Workload / Engine id
- Results table (mode, avg $/query, $/1k, tokens, calls, latency)
- Notes / anomalies / report paths
-->

---

## 5. Open Questions / TODO
- Parameterize the harness to deploy *arbitrary* ADK agents (config-driven), not just weather_agent.
- Config-driven workload spec (set of prompts, iteration count) per experiment.
- Refine runtime-cost model: measure actual Agent Engine instance-time vs prorated estimate.
- If/when billing-account access allows: reconcile catalog estimate against BigQuery export.
- Add a `--label` flag so each run auto-appends a row to the Experiment Log.
