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
| 2026-06-15 | Map the calculator's 4 archetypes to **purpose-built, deployable GCP/ADK agents** | The calculator inputs are placeholders; representative agents let us replace them with *measured* per-SKU usage. Moderate complexity built first (EXP-008). |
| 2026-06-16 | Test with **multi-scenario, variable-length, additive** workloads (`--append`) | Real interactions vary in length/topic; cycling 3–4 scenarios (2–5 turns) and accumulating batches gives a representative dataset rather than one repeated script. |
| 2026-06-15 | **Pin `google-adk` to local + deploy sequentially + ADC for REST** | Hard-won deploy reliability (see Learnings 2026-06-15): unpinned ADK → empty-response crash; concurrent deploys → staging-race; gcloud-CLI token → auth-expiry failures. |
| 2026-06-17 | Report **authoritative token totals from Monitoring `token_count`**, not `usage_metadata` sums, for AgentTool agents | `stream_query` never surfaces AgentTool-encapsulated sub-agent events → 5 agents undercounted. `token_count` captures every model call (needs isolated windows to attribute). |
| 2026-06-17 | Separate **master vs sub-agent tokens via a two-model split** (`COST_TWO_MODEL=1`); keep single-model as the canonical default | `token_count` splits only by model, so coordinator-on-one-model + subs-on-another is the only way to attribute role. Default stays single 2.5-flash for the baseline; split is opt-in. |
| 2026-06-17 | Correct the undercount on the **same canonical model in isolated windows**; re-measure **only token rows** | Two-model engines are a different cost basis (3.5-flash/3.1-lite). Non-token SKUs are count-based + model-independent → don't re-measure them. |

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

- **2026-06-19 — adk-sample agents need their OWN pyproject deps in the deploy, or the engine
  builds but won't start.** Deploying a sample via the generic `deploy.py` (archetype reqs only)
  → container builds, then crashes on startup: `ModuleNotFoundError: No module named
  'diff_match_patch'` → API returns `400 ... failed to start and cannot serve traffic` (the real
  error is only in Cloud Logging, not the create call). Fix: `deploy.py` now reads the original
  sample's `pyproject.toml` `[project].dependencies` (mapped per package) and merges them, minus
  dev tools and the base-provided pins (google-adk/aiplatform/genai). fomc needs diff-match-patch +
  pdfplumber + tabulate + scikit-learn; plumber needs apache-beam[gcp] + GitPython + dbt-bigquery +
  google-api-python-client; on_brand needs scikit-learn + pandas + tenacity.
- **2026-06-19 — APPENDED tool instructions get ignored by a strong existing prompt; PREPEND a
  mandatory preamble (or wrap router agents).** Adding `+ _TOOL_SUFFIX` to fomc/plumber's existing
  workflow prompts → the new tools (load_memory/RAG/web_research/save_note) **never fired** (the
  model followed the dominant original prompt). Fixes: (a) fomc — PREPEND a numbered "MANDATORY
  FIRST STEPS" preamble; (b) plumber (a pure router that `transfer_to_agent`s on turn 1) — the
  preamble alone wasn't enough until the workload itself explicitly demanded recall/RAG/web; (c)
  on_brand (a tool-less LoopAgent root) — wrap it in a coordinator LlmAgent whose primary job IS the
  tool sequence, invoking the loop as an AgentTool. Lesson: to exercise a SKU you must make tool-use
  the agent's primary instruction, not an afterthought.
- **2026-06-19 — a coordinator wrapper can suppress the wrapped agent's core SKU.** Wrapping
  on_brand's image-gen loop in a memory/RAG coordinator dropped image generation from ~0.77/intxn
  (EXP-007 standalone loop) to ~0.10/intxn — the coordinator often answers from memory/RAG without
  delegating to the image loop. The Imagen SKU is still exercised, just at a lower rate for this
  architecture. (`apply_split` leaves the image model untouched — guarded by name/`-image`.)

- **2026-06-17 — AgentTool sub-agent tokens are INVISIBLE to `stream_query` (the real undercount).**
  The deployed remote stream surfaces events from the coordinator and from `sub_agents` reached via
  `transfer_to_agent`, but **NOT** from sub-agents wrapped as **`AgentTool`** — an AgentTool runs a
  nested Runner whose events never propagate to the parent stream. So `usage_metadata`-summed token
  totals **undercount** for the 5 AgentTool agents (researcher, blogger, academic, financial,
  marketing). NOTE: thoughts tokens ARE counted for the events we DO see — the undercount is entirely
  *missing sub-agent events*, not missing thought tokens. Authoritative fix: Cloud Monitoring
  `publisher/online_serving/token_count` captures EVERY model call regardless of the stream.
- **2026-06-17 — Splitting master vs sub-agent tokens needs a two-model trick + sequential isolation.**
  Within one agent, `token_count` separates only by **model** (`resource.labels.model_user_id`), never
  by agent-role. To split coordinator vs sub tokens, put the coordinator on one model and ALL
  descendants on another, then split the metric by model. Impl (`agents/_gmodel.py`): `GlobalGemini`
  (a `Gemini` subclass pinning `api_client` to `Client(vertexai=True, location="global")`) +
  `apply_split(root)` that walks `sub_agents` AND `tool.agent` (AgentTool) recursively, skipping
  workflow agents (Loop/Sequential/Parallel — no `model` field). Guarded behind env `COST_TWO_MODEL=1`
  (set at deploy time, since `apply_split` runs at import and the result is cloudpickled) so the default
  deploy stays canonical single-model. Because `token_count` is **project-wide**, the split — and any
  complete-total capture — requires **one agent at a time in an isolated time window** with no other
  same-model traffic. (Deploys are sequential regardless: fixed-GCS-path staging race.)
- **2026-06-17 — gemini-3.x models are GLOBAL-only.** `gemini-3.5-flash` ✓ and `gemini-3.1-flash-lite`
  ✓ exist but **404 in `us-central1`**; `gemini-3.1-flash` does NOT exist at all. Route per-model via
  `location="global"` while the Agent Engine itself stays regional (us-central1). Available regionally:
  gemini-2.5-flash, -flash-lite, -pro.
- **2026-06-17 — Two delegation patterns have OPPOSITE token distributions (validated, 15 intxn/agent).**
  `sub_agents`+transfer = **sub-heavy** (orchestrator **17% master / 83% sub** — transfer hands the
  full conversation context to the sub, which does the bulk of the processing). `AgentTool` =
  **master-heavy** (71–93% master — the AgentTool sub only sees a narrow sub-task prompt; the
  coordinator carries the whole conversation and re-ingests each tool result). Single-agent = 100%
  master. **Consequence for the undercount:** transfer-subs WERE already in the old stream (not
  undercounted); only AgentTool-subs were missed — so the shortcut `1/%master` **over-corrects**
  mixed-topology agents (those with both a transfer sub AND an AgentTool). The split ratio is
  **per-agent and architecture-driven** → portable across model tiers as a *percentage*, applied on
  top of canonical totals. The clean undercount fix is a direct `token_count` re-measure, not the ratio.
- **2026-06-17 — Correcting the undercount: re-measure on the SAME canonical model, isolated.** Redeploy
  the undercounted agents on **canonical 2.5-flash** (NOT the two-model engines — different models =
  different tokenization/prices/cost basis) and read `token_count` per isolated window = the complete
  total (master + all subs incl. the AgentTool subs the stream missed). The capture **skips
  `add_session_to_memory`** — memory-generation runs an LLM that would otherwise add to the
  conversation `token_count` and **double-count** the separately-measured Memory Bank SKU — and uses
  **fresh users** (clean conversation tokens; memory-retrieval prompt inflation is a separate measured
  effect). Undercount factor = complete ÷ stream. `scripts/exp_complete_tokens.py`.

- **2026-06-15 — EXP-008: 4 calculator archetypes (Moderate) deployed + measured.** Built representative
  GCP/ADK agents for Conversational Chatbot / Workflow Operator / Autonomous Researcher / Multi-Agent
  Orchestrator (see ARCHETYPE_ARCHITECTURES.md), 35 sessions each. Measured $/interaction:
  chatbot $0.0036 (1.4k in, 4 calls) · workflow $0.0150 (13k in, 12.5 calls, 25 session events) ·
  researcher $0.093 incl. ~$0.069 Search grounding (2.6k in / 6k out, 69 grounded searches — first
  material grounding cost) · orchestrator $0.027 (20k in, 12.5 calls). Profiles match archetype theory:
  chatbot=volume/cheap, workflow=tool-fan-out, researcher=output-depth+grounding, orchestrator=fan-out.
- **2026-06-15 — THREE deployment gotchas (all fixed in scripts):**
  1. **Never deploy engines concurrently** — `agent_engines.create()` stages to a FIXED GCS path
     (`agent_engine/agent_engine.pkl` + `dependencies.tar.gz`); parallel deploys race and cross-
     contaminate (a chatbot engine got another agent's tarball → "No module named ..."). Deploy
     sequentially.
  2. **Pin `google-adk` to the local version on deploy** — the unpinned `[adk]` extra let the container
     pull a NEWER ADK than the local one that cloudpickled the agent; every query then crashed with
     `AttributeError: 'LlmAgent' object has no attribute 'mode'` and returned EMPTY event streams (0
     tokens, no exception). `deploy.py` now pins `google-adk==<local>`.
  3. **REST auth via ADC, not the gcloud CLI** — `pricing.py`/`usage.py` shelled out to
     `gcloud auth print-access-token`, which broke when the gcloud CLI credential expired (Context
     Aware Access) even though ADC was valid. Now use `google.auth` default creds.
- **2026-06-15 — Agent Engine query quota is 90 req/min/project/region** ("Query Reasoning Engine
  requests"). Shared across ALL engines in the region. When exceeded, `stream_query` sometimes RAISES
  429 and sometimes returns an EMPTY stream (silent). `exp_sample.py` now retries both (backoff to 90s)
  and paces runs (`--delay`). Orchestrator/sub-agent fan-out hits it fastest.

- **2026-05-28 — Validated grounding collector; native Search grounding comes from events, NOT Monitoring.**
  Built a minimal `grounded_news` agent (single ADK `google_search` tool) and queried it with current-info
  prompts. Result: 2 of 2 responses were grounded (fresh web info; e.g. "Kimi Antonelli won the 2026
  Canadian GP on May 24"), `grounding_metadata` was present in the stream events, and
  `extract_grounding_from_events` correctly returned 2. **But Monitoring
  `web_search_requests_per_publisher` stayed 0** — that metric tracks a different path (likely "Web
  Grounding for Enterprise"), NOT native Gemini Search grounding via the ADK `google_search` tool.
  Corrects the 2026-05-27 entry (financial-advisor just wasn't grounding). Pivoted: events-based
  `extract_grounding_from_events` is the primary, attributable signal; `collect_grounding_usage` is now
  a secondary cross-check with a clear docstring caveat. price_grounding_and_media now takes the events
  count. Validation engine: `reasoningEngines/8904366879997427712` (grounded_news).
- **2026-05-28 — Validated media collectors; Imagen comes from Monitoring, not events.** Triggering
  workloads: marketing-agency generated **7 images** (`imagen-3.0-generate-002`) — captured via Cloud
  Monitoring `model_invocation_count` (model_user_id contains 'imagen'), priced $0.28. Event-based image
  detection was unreliable (free-text tool messages → false positives like "cannot generate the image"),
  so `extract_image_count` is now conservative (inline image bytes only) and `collect_imagen_usage`
  (Monitoring) is the authoritative signal. Grounding stayed 0: financial-advisor answers from model
  knowledge and never invokes native Search, so there was nothing to capture (collector source correct).

- **2026-05-27 — Grounding usage comes from Monitoring, not events; Imagen from events.** Agent Engine
  does NOT surface `grounding_metadata` in streamed `stream_query` events (checked), so grounded-request
  count is read from Cloud Monitoring `*web_search_requests_per_publisher` (project-wide, attribution
  caveat). Imagen has no Monitoring metric → counted from response events. For EXP-006 workloads both
  measured **0** (agents capable but 2-turn tasks didn't trigger Search/image-gen). Collectors:
  `usage.py:collect_grounding_usage` / `extract_image_count` / `price_grounding_and_media`.

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

### EXP-006 — 4 complex adk-sample agents (financial-advisor, academic-research, blog-writer, marketing-agency)
- **Date:** 2026-05-27 | **Unit: $/interaction** (2-turn conversation + memory generation, 3 runs each)
- **Goal:** deploy real complex multi-agent adk-samples (GCP-only, no external keys) and run full
  SKU cost extraction. Engines: financial_advisor `343270278970736640`, academic_research
  `4540625131680038912`, blogger_agent `3729977198753349632`, marketing_agency `6855475340148473856`.

| Agent | Total $/interaction | Model $ | Runtime $ | notable |
|-------|--------------------|---------|-----------|---------|
| financial-advisor | $0.0336 | $0.0125 | $0.0196 | runtime-dominated; 17k–34k input tok/run |
| blog-writer | $0.0156 | $0.0085 | $0.0055 | balanced |
| academic-research | $0.0144 | $0.0078 | $0.0054 | model CV 76% |
| marketing-agency | $0.0111 | $0.0043 | $0.0055 | cheapest |

**Findings:** ~3× cost spread across agents; financial-advisor is the only runtime-dominated one
(deep multi-specialist analysis). Search grounding + Imagen NOT yet metered (uncaptured). Per-agent
summaries in `agent_summaries/`; cross-agent comparison in `COMBINED_SKU_USAGE_REPORT.md`. Tooling:
`scripts/deploy_sample.py`, `scripts/exp_sample.py`, `scripts/build_summaries.py`.
- **Parity rerun (2026-05-28):** re-ran all 4 at **35 iters** (were 3); averages settled lower as
  noisy 3-run samples smoothed out — financial $0.0289, blog $0.0116, academic $0.0074,
  marketing $0.0163. All 8 sample agents now at 35×2 = 70 user queries each.

### EXP-007 — 4 MOST-complex adk-sample agents (35 runs each)
- **Date:** 2026-05-28 | **Unit: $/interaction** (2-turn + memory-write)
- **Goal:** deploy the highest-complexity GCP-only samples and extract per-SKU usage. Engines:
  nexshift_agent, fomc_research, plumber_agent, on_brand_genmedia.

| Agent | Total $/interaction | notable |
|-------|--------------------|---------|
| on-brand-genmedia | **$0.084** ($0.053 compute+tokens + **27 Imagen images ≈ $0.031**) | costliest; Loop+gen-media; ~83k in tok, 17 calls |
| plumber-data-eng | $0.0127 | deepest hierarchy (6 sub-agents); broadest SKU *intent* (~10–11 GCP products) |
| fomc-research | $0.0033 | multimodal pipeline; BigQuery/PDF capable but light on our prompts |
| nexshift-agent | $0.0011 | 7 sub-agents + OR-Tools; returned **empty responses** to free-form prompts (needs structured input) — only memory-gen + runtime billed |

**Findings:** on-brand-genmedia validated the **Imagen SKU** (27 `gemini-2.5-flash-image` invocations,
captured via Monitoring `model_invocation_count`). nexshift shows even a non-responding agent still
incurs Sessions + Memory Bank + Runtime cost. plumber has the broadest SKU intent but most are mocked/
untriggered by 2-turn prompts. Per-agent summaries (with Mermaid architecture diagrams) in `agent_summaries/`.

### EXP-008 — 4 calculator archetypes, purpose-built (Moderate complexity)
- **Date:** 2026-06-15/16 | **Unit: $/interaction** | initially 35 runs, then **expanded to ~85** via
  additive multi-turn batches (`--append`).
- **Goal:** build representative GCP/ADK agents matching the calculator's 4 archetypes (see
  `ARCHETYPE_ARCHITECTURES.md`) and measure their real per-SKU usage to replace placeholder inputs.
- **Engines:** conversational_chatbot, workflow_operator, autonomous_researcher, multi_agent_orchestrator.

| Archetype (Moderate) | $/interaction | interactions | turns | defining SKU signal |
|----------------------|---------------|--------------|-------|---------------------|
| Conversational Chatbot | $0.0059 | 88 | 2–4 | volume/cheap; light tools + Memory Bank |
| Workflow Operator | $0.0204 | 85 | 2–4 | tool fan-out (8 tools → ~25 session events) |
| Autonomous Researcher | $0.0265* | 85 | 2–3 | long outputs + **Google Search grounding** (measured non-zero) |
| Multi-Agent Orchestrator | $0.0323 | 85 | 2–5 | agent-call fan-out (coord + 3 sub-agents); ~20k in tok |

*researcher token+runtime only; with Search grounding folded in it was ~$0.09 at peak grounding rate.

**Findings:** measured profiles match archetype theory (volume / tool-fan-out / output-depth+grounding /
agent-fan-out). Researcher is the **first agent to materially exercise Search grounding**. Multi-turn
expansion (2–5 turns, 3–4 distinct scenarios/agent) makes the dataset representative of varied real
interactions, not one repeated script. **Corpus total now: 1,443 user turns across all experiments.**

### EXP-008b — SKU coverage gap vs the reference calculator (2026-06-16)
The calculator (`Reference/AGENT_CALCULATOR_INPUTS.md`) pre-populates **16–17 SKU sections per
archetype** as placeholders. What our deployed archetype agents actually exercise is narrower:

| SKU | Calculator (placeholder) | Our agents (measured) |
|-----|--------------------------|-----------------------|
| Gemini tokens, Agent Runtime, Sessions, Memory Bank | all 4 | ✅ measured all 4 |
| BigQuery, Apigee, Agent Search/RAG | all 4 | ⚠️ architected but **mocked** (local stand-in tools; 0 billed) |
| Google Search grounding | all 4 | ✅ measured (researcher only) |
| Google Maps grounding | researcher + orchestrator | ❌ not built |
| Agent Sandbox (Code Exec / Computer Use) | all 4 | ❌ not used by any agent |
| Model Armor, Agent Evaluation, Cloud Logging, Cloud Trace | all 4 | ❌ not exercised (Trace enabled on deploy, not metered) |

Calculator Sections defined but left blank for these archetypes: Gemini **Agent Calls**, **Imagen**,
**Veo**, Security Command Center / Anomaly Detection / Semantic Policies (coming soon), Agent Identity
& Registry (no cost), Cloud Monitoring (pricing TBD). **The placeholder→measured delta** = build agents
that also exercise Sandbox, RAG, Maps, Model Armor, and Eval.

### EXP-009 — Firestore SKU added to the 4 archetypes (P0)
- **Date:** 2026-06-16 | 40 fresh interactions each (new Firestore-enabled architecture; not
  appended onto the pre-Firestore 85 to avoid diluting the new SKU).
- **Goal:** close part of the EXP-008b gap — add a real operational database (Firestore) to all 4
  archetype agents and measure the SKU. (BigQuery was the only calculator data SKU; Firestore is the
  more representative agentic operational store, though not in the calculator.)
- **Provisioning:** enabled `firestore.googleapis.com` + created default DB (us-central1) via **ADC
  REST** (gcloud CLI was auth-expired). `fs_state.py` (save_note=write / load_note=read) copied into
  each package; `google-cloud-firestore` added to deploy requirements.

| Agent | Firestore ops (40 runs) | total $/interaction | notable |
|-------|-------------------------|---------------------|---------|
| workflow-operator | 43 writes / 56 reads | $0.0134 | heaviest Firestore user (order history per run) |
| multi-agent-orchestrator | 8 writes / 31 reads | $0.0269 | persists analysis, recalls prior |
| autonomous-researcher | 0 writes / 36 reads | $0.0048 | recalls prior research; restructured to coordinator + web_researcher sub-agent — ⚠ **see EXP-010: this `sub_agents`/transfer wiring never actually ran `google_search` (0 grounding); fixed via AgentTool** |
| conversational-chatbot | 2 writes / 1 read | $0.0058 | saves user prefs |

**Findings:** Firestore SKU now exercised + measured on all 4 (counted per-interaction from
save_note/load_note events; cross-checkable via Firestore Monitoring `billable_*_units`). Cost is
**negligible (~$3e-7/interaction)** — the value is SKU coverage, not dollars. All 4 archetypes now
measure **5 SKUs**: Gemini tokens, Agent Runtime, Sessions, Memory Bank, **Firestore** (+ Search
grounding for researcher).
- **Security fix mid-build:** commit review flagged the Firestore tools as IDOR/prompt-injection risk
  (keyed by LLM `topic`). Fixed (own code): scoped docs by runtime `tool_context.user_id`
  (`agent_state/<user_id>/notes/<sha256(topic)>`); op counts unchanged so measurement unaffected.
- **Agent Sandbox: Code Execution — DEFERRED.** `AgentEngineSandboxCodeExecutor` exists but (a) has
  no per-agent Monitoring metric and (b) auto-provisions a separate engine at runtime. Documented as
  a gap alongside Agent Gateway (Not Launched).

### EXP-010 — Full SKU range + scaled campaign (RAG, Google Search grounding, researcher fix)
- **Date:** 2026-06-16 | Archetypes: chatbot/workflow/orchestrator **80** interactions each
  (40 validation + 40 `--append`), researcher **40** (fresh, post-fix). Multi-turn workloads
  (2–5 turns, ≥70% >2-turn). All gemini-2.5-flash.
- **Goal:** add the remaining P0/P1 SKUs (Vertex AI Search **RAG**, **Google Search grounding**) to
  the 4 archetypes and scale the run for variability.
- **RAG (Vertex AI Search):** synthetic corpus `agent-knowledge` + customer-safe
  `agent-knowledge-public` ingested **via GCS + JSONL manifest** (inline raw_bytes import is silently
  rejected — datastore ends up empty). Runtime SA granted `roles/discoveryengine.viewer` (search
  returned 403 otherwise). Metered per-interaction by counting `discovery_engine_search` tool_calls;
  priced $1.50/1K (calculator).
- **Researcher web-search fix (the key finding):** the `web_researcher` **sub_agent** (LLM
  `transfer_to_agent`) **never executed `google_search`** in the deployed `stream_query` — the
  coordinator handed off control and the stream ended, so the researcher's signature SKU was silently
  **0** across 80 interactions. Rewired `web_researcher` as an **`AgentTool`** (coordinator *calls* it
  → google_search runs). Probe-verified. Now **1.43 grounded turns/interaction**. Native
  google_search grounding_metadata is encapsulated by the AgentTool and the Monitoring
  `web_search_requests` metric does not track it, so we count the AgentTool invocation as the grounded
  query-turn unit (priced $14/1K, calculator).
- **Also fixed:** Firestore client used project *number* (404) → project ID.
- **Memory Bank metric bug (found post-run):** Memory Bank usage was reported as 0 for ALL agents
  due to (a) `exp_sample` reading the wrong metric key (`generate_memories_tokens` vs the real
  `generate_memories_token_count`) and (b) `memory_mutation_count` hardcoded to 0 — compounded by
  Memory Bank generation being **async** (lags the 300s settle). The metric *does* capture it: a
  later query shows ~2,500–8,200 gen-tokens/interaction. Fixed the keys in `exp_sample`; added
  `scripts/backfill_memory.py` to re-query the settled per-engine metric and rewrite reports.
  Backfilled all 4 (and the EXP-011 samples). Memory Bank generation is a real ~$0.004–0.008/intxn
  SKU that was previously shown as $0.

| Agent | Intxns | RAG q/intxn | Search grounded turns | Mem-gen tok/intxn | Firestore w/r | $/interaction |
|-------|--------|-------------|------------------------|--------------------|----------------|----------------|
| conversational-chatbot | 80 | 2.24 | – | 2,461 | 0.03 / 0 | $0.0139 |
| workflow-operator | 80 | – | – | 2,552 | 1.50 / 1.00 | $0.0242 |
| multi-agent-orchestrator | 80 | 0.41 | – | 2,797 | 0.28 / 0.61 | $0.0742 |
| autonomous-researcher | 40 | 1.23 | **1.43** | 8,202 | 1.27 / 1.95 | $0.0793 |

**Findings:** all 4 archetypes now measure the full P0/P1 SKU set (Gemini tokens, Agent Runtime,
Sessions, Memory Bank, Firestore, Vertex AI Search/RAG, Model Armor [derived], + Google Search
grounding for researcher). The researcher is now the costliest archetype — web search adds heavy
input tokens (~42k/intxn) on top of grounding. Old/zombie engines torn down (explicit-ID allowlist;
Beads untouched).

### EXP-011 — Full SKU range extended to 4 adk-sample agents (in progress)
- **Date:** 2026-06-16 | financial_advisor, academic_research, marketing_agency, blogger_agent.
  Added Firestore + RAG (corpus extended with synthetic finance + marketing briefs → 36 docs);
  academic_research's `google_search` (academic_websearch AgentTool) registered for grounding
  metering. Switched these samples to gemini-2.5-flash for parity. 40 interactions each. Two hit the
  transient deploy 500 and were retried (same flaky LRO as the researcher).

### EXP-012 — Memory Bank RETRIEVAL added to the 4 archetypes (returning-user blend)
- **Date:** 2026-06-16 | +40 **returning-user** interactions per archetype, `--append` onto the
  EXP-010 cold-start runs → chatbot 120, workflow 118, researcher 79, orchestrator 120. Realistic
  mix (~33% returning). All gemini-2.5-flash.
- **load_memory, not preload_memory:** `preload_memory` retrieves but is **unmeasurable** — the
  `memory_retrieval_count` metric stays 0 for it AND it runs automatically (no event). Switched all 4
  to **`load_memory`** (LLM-invoked → countable `function_call`; response is `{result:{memories:[...]}}`).
  Counted **memories retrieved** (not raw calls) from the transcript — empty for new users, populated
  for returning. (Bonus: the metric DOES fire for load_memory — workflow 79 / researcher 30 /
  orchestrator 24 — matching the transcript counts.)
- **`--user-pool N`** run mode (round-robin over N returning users) so a user's earlier session
  (memory written + ~90s async generation settle) is recalled on a later visit. pool=5.
- **Denominator bug fixed:** per-interaction rates had divided by transcript *distinct users* (the
  returning batch reused 5 user_ids → collapsed to ~85 groups); now divide by actual interaction count.

| Agent | Intxns | Memories retrieved / intxn | Mem-gen tok/intxn | $/interaction |
|-------|--------|-----------------------------|--------------------|----------------|
| workflow-operator | 118 | **0.67** | 2,549 | $0.0232 |
| autonomous-researcher | 79 | **0.38** | 7,999 | $0.0810 |
| multi-agent-orchestrator | 120 | **0.20** | 2,793 | $0.0932 |
| conversational-chatbot | 120 | 0.00 (see note) | 2,486 | $0.0139 |

**Note on the chatbot:** retrieval = 0 because its support-FAQ workload answers directly (faq_lookup +
RAG) and never invokes `load_memory` — it IS retrieval-capable (probe confirmed it recalls
"Enterprise plan / email / EU" when asked), the FAQ turns just don't trigger it. The 3 task agents
(recall is task-relevant) + `memory_assistant` exercise the retrieval SKU. **Engine-aware backfill:**
adding load_memory redeployed each agent (new engine), so the dataset spans the old (cold-run) and new
(returning-run) engines; `backfill_memory.py` groups batches by engine and sums.

### EXP-013 — Retrieval + web grounding on the 4 use-case (adk-sample) agents
- **Date:** 2026-06-16 | financial_advisor, academic_research, marketing_agency, blogger_agent.
  Added `load_memory` (retrieval) to all 4 + a dedicated `web_research_agent` (google_search AgentTool)
  to marketing + blogger (financial already searches via `data_analyst`, academic via
  `academic_websearch`). Returning-user run: **40 new + 40 returning** (`--user-pool 5 --append`) →
  **80 interactions each** (~50% returning). All gemini-2.5-flash.

| Agent | Intxns | Web grounding/intxn | Mem retrieved/intxn | RAG/intxn | $/interaction |
|-------|--------|----------------------|----------------------|-----------|----------------|
| financial-advisor | 80 | **0.90** | **0.55** | 0.26 | $0.0380 |
| academic-research | 80 | **0.70** | 0.00¹ | 0.34 | $0.0195 |
| marketing-agency | 80 | **0.53** | **0.40** | 1.70 | $0.0252 |
| blog-writer | 80 | **0.50** | **0.31** | 0.80 | $0.0595 |

**Findings:** web grounding now measured for all 4 (the user's ask) — it was previously 0 because the
search was buried in non-dedicated AgentTools (financial `data_analyst`, marketing/blogger) or the
transfer pattern; financial/academic count their dedicated search sub-agents, marketing/blogger got a
new `web_research_agent`. ¹**academic retrieval = 0**: it *calls* `load_memory` (32×) but its
topic-research sessions generate ~no user-centric memories (2 mutations), so nothing comes back —
a workload reality (cf. the support-FAQ chatbot). The other 3 retrieve. Engine-aware memory backfill
across each agent's cold-run + returning-run engines.

### EXP-014 — Master/sub token split + AgentTool undercount correction
- **Date:** 2026-06-17 | All 8 agents (4 archetypes + 4 use-case). Two phases.
- **Goal:** (1) separate coordinator/master tokens from sub-agent tokens per agent; (2) fix the
  AgentTool token undercount in the canonical 80-run totals. Motivated by the realization that
  `stream_query` never surfaces AgentTool sub-agent events (see Learnings 2026-06-17).

**Phase A — two-model split validation (FINAL).** Deployed every agent with `COST_TWO_MODEL=1`
(coordinator → `gemini-3.5-flash`, all descendants → `gemini-3.1-flash-lite`, both via the global
endpoint). Ran **15 interactions/agent**, each agent in an isolated window, then split project-wide
`token_count` by `model_user_id`. 0 failures; clean separation (no model leakage); single-agent
agents correctly 100/0.

| agent | master tok (3.5-flash) | sub tok (3.1-flash-lite) | %master | pattern |
|-------|------------------------|---------------------------|---------|---------|
| multi_agent_orchestrator | 35,865 | 177,994 | **17%** | sub_agents/transfer (sub-heavy) |
| autonomous_researcher | 1,308,504 | 128,062 | **91%** | AgentTool (master-heavy) |
| financial_advisor | 703,291 | 151,013 | **82%** | AgentTool |
| academic_research | 539,706 | 174,545 | **76%** | AgentTool |
| marketing_agency | 316,642 | 25,418 | **93%** | AgentTool |
| blogger_agent | 189,773 | 76,289 | **71%** | AgentTool + transfer subs |
| conversational_chatbot | 93,625 | 0 | **100%** | single agent |
| workflow_operator | 554,231 | 0 | **100%** | single agent |

**Phase B — Option A complete-token re-measure (IN PROGRESS).** Redeployed the 5 AgentTool agents on
**canonical single 2.5-flash** (split guarded off) and run **80 isolated interactions each**, replaying
the exact canonical workloads (`get_scenarios`), capturing both stream tokens and the complete
`token_count` (filtered to gemini-2.5-flash) per window. Skips `add_session_to_memory`; fresh users.
Smoke-verified all 5 canonical engines return non-empty streams and emit only `gemini-2.5-flash`
(no gemini-3.x). Output: `data/complete_tokens_<pkg>.json` (complete per-interaction total +
undercount factor). Only the **token rows** of the summaries/master table get rewritten; non-token
SKUs (runtime/Sessions/Memory Bank/Firestore/RAG/grounding) stay at their EXP-010..013 values.
Tooling: `scripts/exp_complete_tokens.py`, `agents/_gmodel.py`.

**Phase B results (80 interactions/agent, complete `token_count` vs old stream):**

| agent | stream tok/intxn | complete tok/intxn | undercount factor | corrected master / sub tok |
|-------|------------------|--------------------|-------------------|----------------------------|
| financial_advisor | 23,389 | 33,018 | **1.412×** | 27,174 / 5,844 |
| marketing_agency | 11,683 | 14,350 | **1.228×** | 13,288 / 1,062 |
| autonomous_researcher | 38,835 | 43,324 | **1.116×** | 39,468 / 3,856 |
| blogger_agent | 15,143 | 16,770 | **1.108×** | 11,957 / 4,813 |
| academic_research | 5,627 | 5,627 | **1.000×** | 4,254 / 1,373 |

**Findings:** the undercount is **real but agent- and workload-dependent**, 0–41%. The split ratio
(`1/%master`) is NOT a reliable proxy for the undercount — it **over**-corrects mixed-topology agents
(blogger has transfer subs already in-stream + one AgentTool, so actual 1.11× ≪ ratio-implied 1.41×)
and **under**-corrects others (financial actual 1.41× > ratio-implied 1.22×). academic = 1.000× exactly
(on its canonical 2.5-flash workload it barely invokes its AgentTool sub → nothing missed). This is why
the **direct `token_count` re-measure** (not the ratio) is the correct fix. The 3 non-AgentTool agents
(chatbot, workflow = single-agent; orchestrator = transfer subs) were never undercounted and were not
re-run. Applied: `build_summaries.py` reads `data/complete_tokens_<pkg>.json` (override + re-price) and
`data/master_sub_split.json` (role %); §0 master matrix gained **Master tok / Sub tok** columns;
per-agent summaries show the corrected source + factor. docx + xlsx regenerated.

### EXP-015 — Full-SKU + two-model build of 4 legacy agents
- **Date:** 2026-06-18/19 | fomc_research, plumber_agent, on_brand_genmedia, memory_assistant
  (nexshift skipped — returns empty to free-form prompts → no meaningful tokens). All canonical
  **gemini-2.5-flash @ 80 interactions** (`--user-pool 5`), + a 15-interaction two-model run for the
  master/sub split. Brings these 4 to parity with the existing 12-agent corpus.
- **Build:** copied `fs_state.py` + `_gmodel.py` into each; added Firestore (`save_note`/`load_note`)
  + `load_memory` to all; RAG (`VertexAiSearchTool` on `agent-knowledge`) to fomc/plumber/on_brand;
  a dedicated `web_research` **AgentTool** to fomc/plumber; on_brand wrapped in a coordinator that
  invokes the image-gen loop as an AgentTool. Two-model split guarded behind `COST_TWO_MODEL=1`;
  canonical default forces uniform 2.5-flash via `apply_uniform` (fixes plumber's mixed 2.0/2.5-pro
  sub-agents). Corpus extended with 18 docs (`fomc-*`/`de-*`/`brand-*` → 54). memory_assistant
  promoted from a hardcoded legacy row to a full `derive()` agent (META + PACKAGES).
- **Methodology:** per-engine SKUs from `exp_sample` (with memory); **complete** conversation tokens
  from a separate no-memory `exp_complete_tokens` run (memory-gen shares the 2.5-flash token bucket,
  so it can't be cleanly separated in one run); master/sub % from the two-model run.

| Agent | Intxns | in/out tok | %master | RAG/intxn | web grnd/intxn | mem retr/intxn | Imagen | undercount factor | $/intxn |
|-------|--------|------------|---------|-----------|----------------|----------------|--------|-------------------|---------|
| memory_assistant | 80 | 6,294 / 2,336 | 66.9% | – | – | 0.89 | – | 1.00 (transfer subs) | $0.0097 |
| fomc_research | 80 | 27,327 / 2,103 | 45.6% | 0.65 | 0.66 | 0.07 | – | **2.19×** | $0.0274 |
| plumber_agent | 79 | 31,203 / 4,318 | 55.2% | 1.11 | 1.09 | 1.89 | – | 1.07× | $0.0425 |
| on_brand_genmedia | 80 | 63,013 / 9,560 | 39.7% | 1.24 | – | 1.16 | 0.10 img/intxn | **4.63×** | $0.0572 |

**Findings:** all 4 now measure their full applicable SKU set + the master/sub split. The complete-
token factors track topology exactly — on_brand **4.63×** (the entire image-gen loop is AgentTool-
encapsulated, so the stream missed ~78% of its text tokens), fomc **2.19×** (heavy AgentTool
web_research), plumber **1.07×** (mostly transfer subs already in-stream; only web_research missed),
memory_assistant 1.00× (transfer subs → stream complete). **Caveat:** on_brand's Imagen rate
(0.10/intxn) is well below EXP-007's standalone loop (0.77) — the coordinator wrapper often satisfies
requests via memory/RAG without delegating to the image loop. Corpus now spans **13 agents**.
Pre-EXP-015 + canonical engines saved for teardown by explicit ID (`data/old_engines_exp015.json`,
`data/canonical_engines_exp015.json`); two-model engines are the current deployment.

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
- [done] Build + measure the 4 calculator archetypes (Moderate); multi-turn, multi-scenario,
  additive (`--append`) datasets ~85 interactions each (EXP-008).
- [done] Validate Search-grounding (researcher) + Imagen (on-brand-genmedia) collectors against
  real non-zero usage.
- [done] Quantify the **master vs sub-agent token split** per agent (EXP-014 Phase A: two-model
  validation, 15 intxn/agent). Found the AgentTool `stream_query` undercount in the process.
- [in progress] **Correct the AgentTool token undercount** (EXP-014 Phase B): re-measure the 5
  AgentTool agents' complete `token_count` on canonical 2.5-flash in isolated windows, rewrite the
  token rows + layer the master/sub %. Then tear down the superseded two-model engines
  (`data/twomodel_engines.json`, explicit-ID allowlist; Beads untouched).
- **Close the placeholder→measured SKU gap (EXP-008b):** build agents that actually exercise
  **Agent Sandbox (Code Exec / Computer Use), Vertex AI Search / RAG, Google Maps grounding,
  Model Armor, and Agent Evaluation** — the SKUs the calculator assumes but we haven't billed.
- Build the **Low + High** variants of each archetype (only Moderate done) to fill the calculator grid.
- Un-mock BigQuery / Apigee / RAG in the archetype agents (provision real resources) so those SKUs
  bill and get measured instead of stubbed.
- **Report runtime as a provisioned $/hour rate + marginal vCPU/query** (`idle_rate ÷ QPS + token +
  marginal`) to fix window-length comparability.
- Make workloads config-driven (file/JSON) instead of the in-code `WORKLOADS`/`SCENARIOS` dicts.
- If/when billing-account access allows: reconcile catalog estimate against BigQuery export.
