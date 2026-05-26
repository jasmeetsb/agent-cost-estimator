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

- **2026-05-26 — Per-run cost variance is large and output-token-driven.** Identical workload over
  4 runs: model cost CV 48% (3.1× min→max), driven by output/thinking tokens (CV 57%). Structural
  usage (model calls, session events, input) is stable (CV 8–16%); recall reliability 100%. Report
  cost as a distribution (mean + CV) over N runs, never a single-run point estimate (EXP-005).
- **2026-05-24 — Memory Bank adds a HIDDEN server-side token cost.** Generating memories from a
  session runs an LLM in Agent Engine, invisible to `stream_query`/usage_metadata. Captured only
  via `reasoning_engine/memory_bank/generate_memories_token_count` (EXP-004: 2,451 tokens, ≈ the
  gap between conversation usage_metadata and project-wide Monitoring). Memory-enabled agents must
  add this metric or they undercount. Memory Bank auto-wires on deploy (ADK >=1.5.0); the remote
  exposes only `async_add_session_to_memory(session=<full session obj>)`.
- **2026-05-24 — The two token sources match EXACTLY (when measured right).** Controlled run
  (research_agent, project otherwise idle): usage_metadata = 57,212 in / 39,334 out;
  Monitoring `publisher/token_count` = 57,212 in / 39,334 out. Identical. Also confirms
  **Monitoring `output` includes thinking tokens** (= candidates + thoughts, not candidates-only).
- **2026-05-24 — BUG (fixed): Monitoring `alignmentPeriod` must be fine-grained.** We used
  `alignmentPeriod=86400s`, which buckets ~24h into one point; the `[start,end]` interval does
  NOT bound an oversized bucket, so sums were wrong (a quiet 30-min window returned 59k tokens —
  a whole-day bucket). Fix: `alignmentPeriod=60s` + sum the points inside the window. This
  affected `usage.py` token AND runtime collection. Prior EXP-001/EXP-002 runtime numbers used
  the buggy alignment; they were only ~right because each engine was fresh and engine-scoped
  (lifetime ≈ window). Re-measure if precision matters.
- **2026-05-24 — Monitoring HAS token usage but it's not attributable.**
  `publisher/online_serving/token_count` is split input/output but labeled only by `type`,
  `source` (region), `request_type` — **no `reasoning_engine_id`, no model**. It's a project+region
  aggregate across all Gemini traffic. So tokens must come from per-query `usage_metadata`;
  Monitoring tokens are a project-wide cross-check only. **Source-selection principle:** pull each
  usage type from whichever source can attribute it to the agent — tokens → `usage_metadata`,
  runtime (vCPU/mem) → Monitoring (only place it exists, and scoped per engine).
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

### Vocabulary / cost units (read first)
Costs are reported per different units across experiments — compare like for like:
- **query / turn** = one user message → agent response (may fan out to several model calls).
- **interaction** = a complete task that may span multiple turns/sessions (e.g. memory flow below).
- **run** = one execution of an experiment's workload (one interaction, or a batch of queries).
- **model call** = one Gemini request (a turn fans out to N calls via tools/sub-agents).
- **request** = one Agent Runtime request (Monitoring `request_count`; > model calls, incl. session ops).

| Experiment | Cost unit | What one unit is |
|------------|-----------|------------------|
| EXP-001 weather | **$/query** | 1 user message; 5 queries/run |
| EXP-002 research | **$/query** | 1 user message; 5 queries/run |
| EXP-004/005 memory | **$/interaction** | 3 user messages across 2 sessions (2 facts + 1 recall) + 1 memory-generation |

⇒ memory_assistant's "per interaction" cost is NOT comparable to weather/research "per query"; an
interaction is ~3 turns. Normalize to $/turn or $/model-call when comparing agents head-to-head.

### EXP-001 — Baseline: weather_agent, gemini-2.5-flash
- **Date:** 2026-05-23 | **Unit: $/query** (1 user message)
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

### EXP-002 — Complex multi-agent: research_coordinator, gemini-2.5-flash
- **Date:** 2026-05-23 | **Unit: $/query** (1 user message; 5 queries/run)
- **Agent:** `research_agent` — coordinator delegating to 2 specialist sub-agents
  (calc_agent: add/multiply/mean; facts_agent: lookup_fact). 4 tools, multi-agent fan-out.
- **Workload:** 5 multi-part math+fact queries (force both specialists).
- **Engine:** `reasoningEngines/1677857492765245440` | Platform: Vertex AI Agent Engine
  (custom ADK agents deploy to Agent Engine; Gemini Enterprise surfaces these, not a separate
  ADK deploy target — so platform held constant vs EXP-001 for a clean complexity comparison).

| Mode | Avg model $/query | $/1k (model) | Avg in/out tok | Calls/query | Avg latency |
|------|-------------------|--------------|----------------|-------------|-------------|
| remote | $0.0177 | $17.73 | 5703 / 6055 | 4.6 | 34.9s |

**Actual runtime usage by SKU (Cloud Monitoring, ~9 min window, 5 queries):**
- vCPU = 909.6 core-sec, memory = 1028 GiB-sec, request_count = 5 ✓
- Priced: vCPU $0.0218 + memory $0.0026 = **$0.0244 runtime over window** → **$0.0049/query** amortized.
- Report: `data/cost_report_research_agent_remote.json`.

**EXP-001 vs EXP-002 (the headline):**
| | weather (simple) | research (complex) | ratio |
|---|---|---|---|
| model calls/query | 2.0 | 4.6 | 2.3× |
| tokens/query (in+out) | ~480 | ~11,760 | ~24× |
| model $/query | $0.0003 | $0.0177 | **~60×** |
| vCPU core-sec/query (active) | ~52 | ~182 | ~3.5× |

⇒ Agent **architecture complexity drives token cost super-linearly** (multi-agent delegation
re-sends context to each sub-agent and adds reasoning turns). For the complex agent, active
**vCPU dominates runtime** (heavy compute, 35s/query); for the idle simple agent, **memory
dominated** — see caveat.

**Caveat — runtime windows differ, so runtime/query is NOT directly comparable across EXPs.**
EXP-001 used a 3 h window (idle memory accrues → memory huge); EXP-002 used a ~9 min window
(little idle → vCPU dominates). vCPU-per-query (active compute) IS comparable; memory-per-query
is a function of window length × provisioned GiB. Fix in harness: report runtime as a provisioned
**$/hour rate** plus marginal vCPU/query, then cost/query = idle_rate ÷ QPS + token + marginal.

### EXP-003 — Token-source validation (usage_metadata vs Cloud Monitoring)
- **Date:** 2026-05-24 | **Agent:** research_agent | **Engine:** `1677857492765245440`
- **Goal:** confirm the two token sources agree; extract both going forward.
- **Window:** 2026-05-24T02:29–02:39Z, project otherwise idle (verified: adjacent windows = 0 tokens).

| Source | input | output |
|--------|-------|--------|
| usage_metadata (per-query sum) | 57,212 | 39,334 |
| Cloud Monitoring publisher/token_count | 57,212 | 39,334 |
| **match** | **exact** | **exact** |

- Confirms Monitoring `output` = candidates + thoughts (thinking tokens included).
- Required fixing the alignmentPeriod bug (see Learnings). Harness now emits a `token_xcheck`
  block every remote run. Report: `data/cost_report_research_agent_remote.json`.
- **Attribution still matters:** they match only because the project was idle. Monitoring tokens
  are project+region aggregate; usage_metadata stays the per-agent source, Monitoring is the cross-check.

### EXP-004 — Memory Bank + sub-agents: personal_assistant, gemini-2.5-flash
- **Date:** 2026-05-24 | **Unit: $/interaction** = 3 turns (2 facts + 1 recall) over 2 sessions
- **Engine:** `4783370910813913088`
- **Agent:** coordinator with `preload_memory` tool + 2 sub-agents (prefs, notes). Agent Engine
  Memory Bank auto-wired on deploy (ADK >=1.5.0).
- **Flow:** Session A (give facts: name/job/vegetarian/metric) → `async_add_session_to_memory`
  → Session B recall query. **Recall succeeded** — Session B correctly remembered "vegetarian"
  with no re-telling ⇒ cross-session Memory Bank recall works.

**Actual usage by SKU (Cloud Monitoring, ~7 min window):**
| SKU dimension | actual usage |
|---|---|
| Gemini tokens (conversation, usage_metadata) | 3,432 in / 748 out |
| **memory_bank generate_memories_token_count** | **2,451** |
| memory_bank memory_mutation_count | 2 (writes) |
| memory_bank memory_retrieval_count | 2 (reads) |
| runtime vCPU / memory | 319.6 core-sec / 588.5 GiB-sec |
| request_count | 9 |

**Headline finding — memory generation is a HIDDEN cost.** Conversation `usage_metadata` = 3,432
input tokens, but project-wide Monitoring = 5,773; the ~2,340 gap ≈ the 2,451 `generate_memories`
tokens. Memory extraction runs an LLM **server-side**, invisible to `stream_query`/usage_metadata.
⇒ For memory-enabled agents you MUST add `memory_bank/generate_memories_token_count` (priced as
Gemini tokens) or you undercount. Report: `data/cost_report_memory_assistant.json`.

**Full priced breakdown by SKU (rerun 2026-05-26, gaps closed):**
| Component | per-run $ | share |
|---|---|---|
| Runtime (vCPU + memory) | $0.0070 | 35% |
| Memory + session ops | **$0.0083** | **42%** |
|  — memory retrievals (9 × $0.0005) | $0.0045 | |
|  — session events appended (~12 × $0.00025) | $0.0030 | |
|  — memory generation (2,518 tok @ input rate) | $0.0008 | |
| Conversation tokens | $0.0046 | 23% |
| **Total per run** | **$0.0199** | |

**Finding:** for a memory-enabled agent, **memory + session operation SKUs (42%) exceed the
conversation token cost (23%)** — the LLM tokens are the smallest slice. Cost-by-SKU is essential;
a token-only estimate would miss most of the bill.

**Resolved gaps:** generate-memory tokens priced (input rate, no in/out split available); memory
retrievals priced ($0.0005/op); session events approximated from observed events (×$0.00025).
**Still export-only / approximate:** session-event count (no Monitoring metric), memory storage
(monthly per-memory charge), and ancillary infra (Trace/Logging/Storage/Build/egress).

### EXP-005 — Variability study: memory_assistant (same deployment, 4 runs)
- **Date:** 2026-05-26 | **Unit: $/interaction** (3 turns over 2 sessions, as EXP-004)
- **Engine:** `4783370910813913088` (no redeploy) | fresh user per run.
- **Goal:** quantify run-to-run usage variability for an identical workload.

| Metric | mean | min–max | CV% | spread% |
|---|---|---|---|---|
| input tokens | 3,398 | 2,552–4,001 | 16% | 43% |
| output tokens | 1,605 | 752–3,150 | **57%** | **150%** |
| model calls | 5.75 | 5–6 | 8% | 17% |
| session events | 11.5 | 10–12 | 8% | 17% |
| model $/run | $0.0050 | $0.0029–$0.0091 | **48%** | 123% |
| recall success | — | — | **100%** | — |

Aggregate (Monitoring, 4 runs): runtime $0.0142 (35 reqs); memory bank 9,973 generate-tokens,
~2.5 retrievals/run, ~3.25 memories written/run. Report: `data/cost_report_exp005_variability.json`.

**Finding:** identical task, **model cost swung 3.1×**. Driver = **output/thinking tokens (CV 57%)**;
structural usage (calls, events, input) is stable (CV 8–16%). Function is reliable (100% recall) —
the *cost* is what's noisy. ⇒ A single run can misestimate by 2–3×; report cost as a distribution
(mean + CV, min/max) over N runs, not a point estimate.

<!-- Template for new experiments:
### EXP-NNN — <title>
- Date / Agent / Workload / Engine id
- Results table (mode, avg $/query, $/1k, tokens, calls, latency)
- Notes / anomalies / report paths
-->

---

## 5. Open Questions / TODO
- [done] Parameterize deploy + harness by `--agent` (EXP-002).
- [done] Integrate actual runtime SKU extraction from Cloud Monitoring into the harness.
- **Report runtime as a provisioned $/hour rate + marginal vCPU/query**, so cost/query is
  `idle_rate ÷ QPS + token_cost + marginal_compute` — fixes the window-length comparability issue.
- Make workloads config-driven (file/JSON) instead of the in-code `WORKLOADS` dict.
- If/when billing-account access allows: reconcile catalog estimate against BigQuery export.
- Capture the other touched SKUs (Storage, Artifact Registry/Build, Logging, Trace, egress) via
  their own Monitoring metrics for a full picture.
