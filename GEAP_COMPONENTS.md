# Gemini Enterprise Agent Platform (GEAP) — Components & Metering

A map of the Gemini Enterprise Agent Platform: its key features/sub-products and, for each,
**how it is metered for usage** — plus how this project's harness extracts that usage.

GEAP is Google's rebrand/expansion of **Vertex AI** for agents (GA April 22, 2026). The
underlying APIs are still `aiplatform.googleapis.com` (e.g. ReasoningEngine = Agent Runtime),
which is why our catalog/Monitoring extraction (built against Vertex AI) works unchanged.

Sources at the bottom. Rates are **public list prices** and vary by region/model/machine — treat
as representative, pull live values from the Billing Catalog API (`pricing.py`) for exact figures.

---

## 0. Quick reference — all components at a glance

| Component | Description | Metering unit (rate) | Notes |
|-----------|-------------|----------------------|-------|
| **Models (Gemini)** | LLM powering the agent | Per token: input / output / cached (e.g. 2.5 Flash $0.30 / $2.50 / $0.03 per 1M) | Thinking tokens bill as output; cached ≈10% of input; long-context (>200K) & audio premiums; Priority ×1.8, Flex/Batch −50%; no charge on failed requests. Capture: `usage_metadata` |
| **Model Garden (3rd-party)** | Claude/GPT/etc. via ADK | Per provider's own token rate | Same wiring, different rate card |
| **Agent Runtime** (ex-Reasoning Engine) | Managed sandbox hosting/scaling the agent | vCPU-sec ($0.0864/vCPU-hr) + GiB-sec ($0.009/GiB-hr); GPU-sec if used | Free tier 180k vCPU-s + 360k GiB-s/mo; 30-sec increments; vCPU scales to zero, memory held continuously (idle-cost driver). Capture: `Monitoring` allocation_time |
| **Sessions** | Managed multi-turn session/state | Per session event appended ($0.00025/event) | Billing began Feb 11 2026. No Monitoring metric → export-only; approximate from observed events |
| **Memory Bank — stored** | Long-term memory persistence | Per memory per month ($0.00025) | Monthly cost shape, not per-run; export-only |
| **Memory Bank — retrieved** | Recall memories into context | Per retrieval op ($0.0005) | Capture: `Monitoring` memory_retrieval_count |
| **Memory Bank — generate** | LLM extracts memories from a session | Gemini tokens (server-side) | Hidden cost — invisible to `usage_metadata`; capture via `Monitoring` generate_memories_token_count |
| **Vector Search** | Vector index backing RAG | Index serving per node-hour (~$0.094/node-hr × replicas); building $3/GiB; storage GB-mo | Large fixed cost (~$700–800/mo for 3 replicas) independent of query volume |
| **RAG Engine** | Managed retrieval-augmented generation | Composite: corpus storage + retrieval + embeddings + Gemini tokens | Managed Search app → app query rate; custom pipeline → underlying SKUs directly |
| **Grounding / Search** | Ground in Google Search/Maps/your data | Per grounded prompt/query: 5,000/mo free then $14/1k (Gemini 3); $35/1k (2.x); your-data $2.50/1k | Capture: `Monitoring` web_search_requests metrics |
| **ADK** | Agent-building framework | No platform SKU | Cost = resources it consumes |
| **Agent Studio / Agent Designer** | Low-code/visual agent authoring | No per-use SKU | Cost = model/runtime consumed |
| **Evaluation** | Evalsets, LLM-as-judge, trajectory scoring | No platform SKU | Cost = model tokens during eval runs |
| **A2A protocol** | Agent-to-agent wire format | No platform SKU | Cost shows up as the calls it triggers |
| **Agent Gateway** | Secures/governs agent connectivity | No per-call agent SKU | Bills as underlying networking |
| **Agent Registry** | Catalog of agents/tools/MCP servers | No per-use SKU | Governance layer |
| **Gemini Enterprise (publish)** | Lists agent for discovery (ADK/A2A) | Gemini Enterprise seat/subscription | Not a per-call agent SKU |
| **Observability — Cloud Trace** | Distributed tracing of spans | Per span ingested (Trace pricing) | `enable_tracing=True` turns this on every deploy |
| **Observability — Logging** | Prompt/response + content logs | Per GiB ingested/stored (Logging pricing) | NO_CONTENT metadata mode by default when deployed |
| **Observability — BQ Agent Analytics** | Structured events → BigQuery | BQ storage + query/AI-function pricing | Opt-in `--bq-analytics`; a 3rd per-agent token source |
| **GCS (staging/content)** | Deploy package + log/content offload | GB-month (Standard $0.020) | Ancillary |
| **Cloud Run** (alt deploy) | Container host instead of Agent Runtime | Per-request + vCPU/mem-sec | Different SKU surface |
| **GKE** (alt deploy) | Cluster host instead of Agent Runtime | Node/cluster pricing | Different SKU surface |
| **Security (SA, IAP, WIF, VPC-SC, PSC)** | Identity/network governance | Mostly free; IAP/PSC minor charges | — |

The sections below expand each area with exact rate tables and capture details.

---

## 1. Component inventory

| Component | What it does | Lifecycle phase |
|-----------|--------------|-----------------|
| **Agent Development Kit (ADK)** | Model-agnostic framework for building agents (agents, tools, orchestration, callbacks, state). | Build |
| **Agent Studio** | Low-code visual canvas for designing/prototyping agent reasoning loops & workflows. | Build |
| **Agent Designer** | Guided/visual agent authoring in the Gemini Enterprise surface. | Build |
| **Models (Model Garden)** | Gemini + third-party (Claude, GPT, etc.) models that power agents. | Build/Run |
| **Agent Runtime** (formerly Reasoning Engine / Agent Engine) | Fully managed sandbox that hosts & scales a deployed agent; REST-first. 5 deploy paths (ADK/LangChain/LangGraph/AG2/LlamaIndex). | Deploy/Run |
| **Sessions** | Managed conversational session + state for multi-turn interactions (survives restarts, scales horizontally). | Run |
| **Memory Bank** | Long-term memory across sessions: extract, store, retrieve memories to ground future runs. | Run |
| **RAG Engine** | Managed retrieval-augmented generation: corpus storage + embedding + retrieval + generation. | Build/Run |
| **Vector Search** | AI-native vector index for storing/searching embeddings (backs RAG). | Run |
| **Grounding** | Ground responses in Google Search, Google Maps, or your own data. | Run |
| **Agent Gateway** | Networking layer securing/governing user↔agent, agent↔tool, agent↔agent connectivity. | Run/Govern |
| **Agent Registry** | Centralized catalog of agents, tools, and MCP servers across the org. | Publish/Govern |
| **Gemini Enterprise (publish)** | Registers a deployed agent so humans/other agents can discover it (ADK or A2A modes). | Publish |
| **A2A protocol** | Agent-to-agent wire format for cross-process / cross-org agent calls. | Orchestrate |
| **Evaluation** | Evalsets, LLM-as-judge, trajectory scoring against a rubric before deploy. | Evaluate |
| **Observability** | OpenTelemetry → Cloud Trace; prompt/response logging → GCS/BigQuery/Cloud Logging; BigQuery Agent Analytics plugin. | Observe |
| **Deployment alternatives** | Same agent can also deploy to **Cloud Run** or **GKE** instead of Agent Runtime. | Deploy |
| **Security/Identity** | Per-agent service account, IAP, Workload Identity Federation, VPC-SC, Private Service Connect. | Govern |

---

## 2. Metering analysis — how each component bills

Legend for **"how we capture it"**: `usage_metadata` = from the agent response (exact, per-query);
`Monitoring` = Cloud Monitoring metric scoped per `reasoning_engine_id`; `Catalog` = unit price from
Billing Catalog API; `export-only` = only in BigQuery billing export (no per-agent Monitoring metric).

### 2.1 Models — Gemini tokens (usually the headline, but not always — see EXP-004)
Metered **per token**, split input / output / cached, with long-context (>200K) and audio/video
premiums, plus Priority (1.8×) and Flex/Batch (−50%) tiers.

| Model | Input /1M | Output /1M | Cached input /1M |
|-------|-----------|------------|------------------|
| Gemini 3.1 Pro | $2 (≤200K) / $4 | $12 / $18 | $0.20 / $0.40 |
| Gemini 3.5 Flash | $1.50 | $9.00 | $0.15 |
| Gemini 3.1 Flash-Lite | $0.25 (text) | $1.50 | — |
| Gemini 2.5 Pro | $1.25 / $2.50 | $10 / $15 | $0.13 / $0.25 |
| Gemini 2.5 Flash | $0.30 (text) | $2.50 | $0.03 / $0.10 |
| Gemini 2.0 Flash | $0.15 | $0.60 | — |

- **No charge** for failed (4xx/5xx) requests. Cached input ≈ 10% of input rate. Image ≈ 1,290 tokens/1024².
- **How we capture it:** `usage_metadata` (conversation) × `Catalog`. Thinking tokens bill as output.

### 2.2 Agent Runtime — compute
Metered **per vCPU-second and per GiB-memory-second** of actual execution (GPU-seconds if used).
- Rates: **$0.0864 / vCPU-hour** (= $2.4e-5/vCPU-sec), **$0.0090 / GiB-hour** (= $2.5e-6/GiB-sec).
- **Free tier:** first 180,000 vCPU-sec (50h) + 360,000 GiB-sec (100h) per month.
- Billed in **30-second increments** for whatever vCPU/RAM/GPU the node is using at that moment.
- **vCPU scales to zero when idle; memory is held continuously** (the idle-cost driver — see EXP-001/004).
- **How we capture it:** `Monitoring` `reasoning_engine/cpu|memory/allocation_time` × `Catalog`.

### 2.3 Sessions
Metered **per session event appended** (managed session persistence).
- Rate: **$0.00025 per event**. Billing began **Feb 11, 2026**.
- **How we capture it:** **export-only** for the authoritative count (no Monitoring metric); we
  approximate from observed events × `Catalog`.

### 2.4 Memory Bank
Three distinct meters:
| Sub-meter | Unit | Rate | Capture |
|-----------|------|------|---------|
| Memories **stored** | per memory **per month** | $0.00025 | export-only (monthly; no stored-count metric) |
| Memories **retrieved** | per retrieval op | $0.0005 | `Monitoring` `memory_bank/memory_retrieval_count` × `Catalog` |
| **Generate** memories | Gemini **tokens** (server-side LLM) | model token rate | `Monitoring` `memory_bank/generate_memories_token_count` × `Catalog` |
- Billing began **Feb 11, 2026**. **Hidden cost:** generate-memory tokens are invisible to
  `usage_metadata` (run server-side) — must add the Monitoring metric or you undercount (EXP-004).

### 2.5 Vector Search (backs RAG)
Infrastructure-metered, not per-query:
- **Index serving:** per **node-hour** (machine-type dependent, e.g. ~$0.094/node-hr e2-standard-2/us-central1; ×replicas).
- **Index building:** **$3.00 per GiB** processed. **Storage:** GB-month (Standard $0.020, SSD $0.170).
- **How we capture it:** `Monitoring` node/replica metrics + `Catalog`; storage via `export`. Note:
  a moderately sized 3-replica index ≈ $700–800/month — a large fixed cost independent of query volume.

### 2.6 RAG Engine
Composite: **corpus storage + retrieval queries + underlying model calls** (embeddings + Gemini).
- **Caveat:** if RAG runs *through* a managed Agent Builder/Search app you're billed at the
  app's per-query rate; a *custom* RAG pipeline bills the Vector Search + embedding + token SKUs
  directly. Same functionality, different SKUs — know which path you're on.

### 2.7 Grounding / Search
Metered **per grounded prompt / per query**:
- Gemini 3: Google Web/Image Search & Maps **5,000 queries/mo free**, then **$14 / 1,000**.
  Grounding-with-your-data **$2.50 / 1,000 prompts**.
- Gemini 2.0/2.5: Google Search **1,500/day free** (Flash) / 10,000/day (Pro), then **$35 / 1,000**;
  Web Grounding for Enterprise **$45 / 1,000**; Maps overage **$25 / 1,000**.
- **How we capture it:** `Monitoring` `web_search_requests_per_publisher` metrics + `Catalog`; or export.

### 2.8 Observability (no GEAP-specific SKU — bills as underlying GCP)
- **Cloud Trace:** per span ingested (Trace pricing). **Cloud Logging:** per GiB ingested/stored.
- **GCS** (prompt/response + content offload) and **BigQuery Agent Analytics** (storage + query/AI funcs).
- **Self-inflicted note:** `enable_tracing=True` on every deploy turns on Trace billing.
- **How we capture it:** export-only / each product's own metrics.

### 2.9 Components with no direct usage meter (priced indirectly)
- **ADK, Agent Studio, Agent Designer, A2A, Evaluation** — no per-use platform SKU; cost is the
  resources they *consume* (model tokens during eval, runtime during a run, etc.).
- **Agent Gateway, Agent Registry, Gemini Enterprise publish** — governance/networking; any charge
  shows up as the underlying networking/Gemini Enterprise seat/subscription, not a per-call agent SKU.
- **Cloud Run / GKE** (alt deploy targets) — billed by their own models (Cloud Run: request + vCPU/mem;
  GKE: node/cluster). Different SKU surface than Agent Runtime.

---

## 3. Coverage map for this project's harness

| Component | Capturable today (Monitoring + usage_metadata + Catalog) | Needs billing export |
|-----------|----------------------------------------------------------|----------------------|
| Gemini tokens (conversation) | ✅ exact | — |
| Memory-generation tokens | ✅ Monitoring | — |
| Memory retrievals | ✅ Monitoring | — |
| Agent Runtime vCPU/memory | ✅ Monitoring | — |
| Sessions (events) | ⚠️ approximate (observed events) | ✅ authoritative |
| Memory storage (monthly) | ❌ | ✅ |
| Vector Search nodes / storage | ⚠️ node metrics | ✅ storage |
| Grounding/Search queries | ⚠️ Monitoring metrics exist | ✅ |
| Trace / Logging / GCS / BQ | ❌ | ✅ |

**Validation:** our live Catalog rates reconcile with published Agent Runtime pricing —
$2.4e-5/vCPU-sec = $0.0864/vCPU-hr and $2.5e-6/GiB-sec = $0.009/GiB-hr (exact match). Sessions
$0.00025/event, memory retrieved $0.0005, memory stored $0.00025/mo all match the catalog SKUs we pull.

**Key cross-cutting lessons (from EXP-001/004):**
1. At low QPS, **idle Agent Runtime memory** dominates — "cost per query" requires a utilization assumption.
2. For memory agents, **Memory Bank + Session ops can exceed model-token cost** — per-SKU costing is essential.
3. **Server-side costs (memory generation) are invisible to `usage_metadata`** — Monitoring/export needed.

---

## Sources
- [GEAP pricing](https://cloud.google.com/products/gemini-enterprise-agent-platform/pricing)
- [Agent Platform / Generative AI pricing](https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing)
- [Agent Platform overview](https://docs.cloud.google.com/gemini-enterprise-agent-platform/overview)
- [Agent Runtime docs](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/runtime)
- [Introducing GEAP (blog)](https://cloud.google.com/blog/products/ai-machine-learning/introducing-gemini-enterprise-agent-platform)
- [agents-cli (lifecycle, deploy, observability docs)](https://google.github.io/agents-cli/)
- [Vector Search / Vertex AI pricing guides (CloudZero, nOps)](https://www.cloudzero.com/blog/google-vertex-ai-pricing/)
