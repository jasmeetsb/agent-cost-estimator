# Master Summary — Implemented Agent Architectures

**Living index** of every agent architecture deployed in this project, the SKUs each consumes, measured per-interaction usage, and derived list-price cost. Update this doc whenever a new agent is added. Per-agent details (architecture, methodology, full usage distribution + variability) live in linked files below.

## Executive summary

- **13 agents deployed** on Vertex AI Agent Engine (Gemini Enterprise Agent Platform).
- **Cost spans $0.0011–$0.0934 per interaction** at catalog list price (83× spread), driven by architecture (sub-agent fan-out, analysis depth) more than the prompt.
- **Architecture matters more than prompt:** financial-advisor consumes ~7× more input tokens than the lightest agent and is the only **runtime-dominated** one.
- **Run-to-run variability is real:** identical task can swing total cost ~2× (output/thinking tokens are the noisy SKU).
- **Memory + session SKUs are a meaningful slice** even when memories are never read back — always present for any session-persisted agent.
- **Collectors built and validated** for tokens, vCPU/memory, sessions, Memory Bank, Search grounding, and Imagen. Still uncaptured: Cloud Trace, Logging, Storage.

## What "per interaction" means

All usage and cost figures below are **per interaction** — the unit of work the cost harness measures. One interaction =

- **For the 4 ADK sample agents (financial-advisor, academic-research, blog-writer, marketing-agency):** a **2-turn conversation in one session** + an `add_session_to_memory` call that triggers Memory Bank generation. Typically fans out to 2–6 model calls and ~4–7 session events depending on sub-agent delegation.
- **For `memory_assistant`:** a **3-turn flow across 2 sessions** — Session A receives 2 user facts → `add_session_to_memory` → Session B issues 1 recall query. ~5.75 model calls and ~11.5 session events.

**Caveat:** interaction turn-counts differ (archetypes 2–5 turns, samples 2 turns, memory_assistant 3) so raw $/interaction is not strictly apples-to-apples — normalize to **$/turn or $/model-call** for head-to-head comparison. Variability stats (low/high range) are over each agent's full run set (archetypes 40–80 interactions; samples 40).

All agents: model `gemini-2.5-flash`, deployed to Vertex AI Agent Engine. Reproduce: `python scripts/exp_sample.py --package <pkg> --runs 40 --settle 300`.

## Agents at a glance

- **conversational-chatbot (archetype)** — Calculator archetype: Conversational Chatbot / Moderate. Single support agent + light tools + Memory Bank. Cheapest archetype; volume-driven. → [details](conversational_chatbot.md)
- **workflow-operator (archetype)** — Calculator archetype: Workflow Operator / Moderate. Single agent driving an 8-tool order workflow. Tool-fan-out-driven (highest session-event churn). → [details](workflow_operator.md)
- **autonomous-researcher (archetype)** — Calculator archetype: Autonomous Researcher / Moderate. Single agent + Google Search grounding, long outputs. Token-depth-driven; exercises Search grounding. → [details](autonomous_researcher.md)
- **multi-agent-orchestrator (archetype)** — Calculator archetype: Multi-Agent Orchestrator / Moderate. Coordinator + 3 specialist sub-agents. Fan-out-driven; most expensive archetype. → [details](multi_agent_orchestrator.md)
- **financial-advisor** — Stock analysis & trading-strategy advisor. Hierarchical: coordinator + 4 AgentTool specialists (data, trading, execution, risk). Heaviest input-token consumer; runtime-dominated. → [details](financial_advisor.md)
- **academic-research** — Academic literature discovery & analysis. Coordinator + AgentTool websearch + new-research specialists. → [details](academic_research.md)
- **marketing-agency** — End-to-end branding suite: domain, website, marketing, logo (Imagen) creators wrapped as AgentTools under one coordinator. → [details](marketing_agency.md)
- **blog-writer** — Multi-agent technical blog authoring. Coordinator + 4 sub-agents (outline, draft, edit, social) + HITL refinement. → [details](blogger_agent.md)
- **on-brand-genmedia** — Brand-compliant iterative image generation. Loop + Hierarchical: prompt → image (gemini-2.5-flash-image) → score → re-prompt if below threshold. Heaviest image-gen SKU usage in the corpus. → [details](on_brand_genmedia.md)
- **plumber-data-engineering-assistant** — Build/deploy data pipelines. Deepest hierarchy in the corpus: root + 6 specialist sub-agents (Dataflow / Dataproc / Dataproc-templates / dbt / GitHub / Cloud Monitoring). Touches ~10–11 distinct GCP product SKUs by intent. → [details](plumber_agent.md)
- **memory_assistant** — Personal assistant with long-term cross-session memory. Coordinator + 2 sub-agents + Memory Bank (write+read). Exercises the most Agent Platform features in this corpus. → [details](memory_assistant.md)
- **fomc-research** — FOMC meeting financial-analysis report. Hierarchical + Sequential multimodal pipeline (BigQuery metadata + PDF transcripts via pdfplumber + multimodal Gemini). → [details](fomc_research.md)
- **nexshift-agent** — AI nurse rostering optimizer. Coordinator + 7 sub-agents + OR-Tools CP-SAT solver. 4 orchestration patterns (Hierarchical + Sequential + Parallel + HITL), 31 tools — broadest tool surface in the corpus. → [details](nexshift_agent.md)

## 0. All SKUs at a glance — full per-interaction matrix (PRIMARY)

Every measured SKU, per interaction, for all agents in one view. The **Interactions** column is the number of interactions each agent was tested over. Ranges, distributions, and derived cost breakdown are in the sections below.

| Agent | Interactions | Total turns | Input tok | Output tok | Master tok | Sub tok | Model calls | vCPU-s | GiB-s | Session events | Mem-gen tok | Mem retrieved | Firestore W/R | RAG queries | Web grounding | Imagen | $/intxn |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--:|--:|--:|--:|--:|
| [conversational-chatbot (archetype)](conversational_chatbot.md) | 120 | 432 | 6369 | 693 | 7061 | 0 | 7.5 | 20.9 | 39 | 15.0 | 2486 | 0.00 | 0.03/0.00 | 2.15 | 0.00 | 0 | 0.0139 |
| [workflow-operator (archetype)](workflow_operator.md) | 118 | 425 | 20107 | 1485 | 21591 | 0 | 14.0 | 25.3 | 47 | 27.9 | 2549 | 0.67 | 1.42/1.23 | 0.00 | 0.00 | 0 | 0.0232 |
| [autonomous-researcher (archetype)](autonomous_researcher.md) | 79 | 253 | 32585 | 10739 | 39468 | 3856 | 7.8 | 171.2 | 201 | 15.6 | 7999 | 0.38 | 1.34/2.06 | 1.18 | 1.62 | 0 | 0.0822 |
| [multi-agent-orchestrator (archetype)](multi_agent_orchestrator.md) | 120 | 432 | 149080 | 6080 | 26067 | 129093 | 18.9 | 90.6 | 100 | 37.9 | 2793 | 0.20 | 0.29/0.63 | 0.42 | 0.00 | 0 | 0.0932 |
| [financial-advisor](financial_advisor.md) | 80 | 160 | 23206 | 9812 | 27174 | 5844 | 3.5 | 135.6 | 174 | 7.2 | 3151 | 0.55 | 0.03/0.95 | 0.26 | 0.90 | 0 | 0.0595 |
| [academic-research](academic_research.md) | 80 | 160 | 4507 | 1120 | 4254 | 1373 | 3.0 | 66.5 | 85 | 6.0 | 2480 | 0.00 | 0.04/0.56 | 0.34 | 0.70 | 0 | 0.0201 |
| [marketing-agency](marketing_agency.md) | 80 | 160 | 10304 | 4046 | 13288 | 1062 | 3.7 | 187.9 | 231 | 7.6 | 2762 | 0.40 | 0.05/1.01 | 1.70 | 0.53 | 0 | 0.0339 |
| [blog-writer](blogger_agent.md) | 80 | 160 | 11345 | 5425 | 11957 | 4813 | 4.8 | 101.3 | 138 | 11.1 | 4603 | 0.31 | 0.00/0.95 | 0.80 | 0.50 | 0 | 0.0638 |
| [on-brand-genmedia](on_brand_genmedia.md) | 35 | — | 83460 | 7349 | — | — | 17.2 | 322.7 | 329 | 31.6 | 4191 | 0.00 | 0.00/0.00 | 0.00 | 0.00 | 27 | 0.0934 |
| [plumber-data-engineering-assistant](plumber_agent.md) | 35 | — | 13800 | 1958 | — | — | 4.0 | 104.1 | 127 | 8.0 | 2853 | 0.00 | 0.00/0.00 | 0.00 | 0.00 | 0 | 0.0143 |
| [memory_assistant](memory_assistant.md) | — | — | 3398 | 1605 | — | — | 5.8 | 39.0 | 560 | 11.5 | 2493 | 2.50 | 0.00/0.00 | 0.00 | 0.00 | 0 | 0.0165 |
| [fomc-research](fomc_research.md) | 35 | — | 1838 | 479 | — | — | 2.3 | 30.1 | 55 | 4.8 | 2358 | 0.00 | 0.00/0.00 | 0.00 | 0.00 | 0 | 0.0035 |
| [nexshift-agent](nexshift_agent.md) | 35 | — | 0 | 0 | — | — | 0.0 | 12.8 | 37 | 2.0 | 2390 | 0.00 | 0.00/0.00 | 0.00 | 0.00 | 0 | 0.0011 |

**Legend** — what each column means (all values are **per interaction**, averaged over the Interactions column, unless noted):

- **Interactions** — number of interactions the agent was tested over (sample size for every average in the row).
- **Total turns** — total user turns sent to the agent across the whole experiment (Σ turns over all interactions); multi-turn archetypes send far more turns than interactions.
- **Input tok / Output tok** — Gemini prompt tokens (incl. cached) / output tokens (candidates + thinking). Billed at the input / output rates. For multi-agent agents these are the **complete** totals from Cloud Monitoring `token_count` (captures AgentTool sub-agent tokens the response stream misses).
- **Master tok / Sub tok** — the input+output total split into coordinator/master vs sub-agent/tool tokens, using the per-agent architecture-driven % from the two-model validation (single-agent agents are 100% master; '—' = split not measured).
- **Model calls** — model invocations per interaction; one tool-using turn emits several.
- **vCPU-s / GiB-s** — Agent Runtime vCPU-seconds / memory GiB-seconds, amortized over the measurement window (upper bound, not actual billed instance-time).
- **Session events** — events appended to the Sessions (short-term memory) store.
- **Mem-gen tok** — Memory Bank generation tokens (LLM extraction triggered by `add_session_to_memory`).
- **Mem retrieved** — Memory Bank memories retrieved via `load_memory`; 0 when the workload doesn't recall prior context.
- **Firestore W/R** — Firestore document writes / reads (`save_note` / `load_note`).
- **RAG queries** — Vertex AI Search (RAG) queries against the synthetic corpus.
- **Web grounding** — Google Search grounded query-turns (`google_search` via a web-research AgentTool).
- **Imagen** — images generated (Imagen / `gemini-2.5-flash-image`).
- **$/intxn** — derived cost per interaction = Σ(usage × catalog list price); includes Model Armor (all tokens scanned @ $0.10/1M, folded in, no column). **Reference only — list price, not actual billed dollars.**
- **'—'** — not tracked for that legacy entry (`memory_assistant`).

**Billing alignment & caveats** — how each measure maps to how the product is actually billed:

- **Billing-accurate units** (our count = the billed dimension): Gemini input/output tokens (cached split to the cheaper rate; thinking billed as output), RAG queries, memories retrieved, Firestore document ops, Imagen images.
- **AgentTool token-undercount correction:** multi-agent agents wrapping a sub-agent as an `AgentTool` emit sub-agent token events that never reach the parent response stream, so the old `usage_metadata` sums under-counted them. Input/Output tok here are the **complete** `token_count` totals from isolated canonical-2.5-flash runs (per-agent factors 1.00–1.41×); Master/Sub split is the architecture-driven % from the two-model (3.5-flash/3.1-flash-lite) validation.
- **Estimates** (right dimension, approximated): **vCPU-s / GiB-s** are `allocation_time` amortized per-interaction over the window incl. idle — an upper bound, not actual billed instance-hours; **Session events** is event-stream-observed (not metered) and excludes session storage GiB-hr; **Mem-gen tok** is priced at the input rate (single-rate proxy) and excludes the monthly per-memory storage charge.
- **Proxy / lower bound:** **Web grounding** is billed per grounded prompt, but we count the web-research AgentTool invocation (internal multi-search would bill more).
- **Not a billing unit:** **Model calls** — Gemini bills tokens, not calls (shown as a usage driver).
- **$/intxn is catalog list price, not billed dollars** (no account discounts/CUDs). Uncaptured SKUs: Cloud Logging/Trace/Monitoring, Cloud Storage, networking, RAG datastore storage/indexing. True spend requires BigQuery billing export (not set up).

## 0b. Calculator SKU coverage — columns vs. the GE AP pricing calculator

How the §0 columns map to the rows in the GE AP pricing calculator (the reference cost model). The columns cover the calculator's core, currently-deployable **per-interaction** SKUs — it is **not** a 1:1 of every calculator row: parked/deferred/monthly-storage SKUs have no column, the three Gemini token buckets are collapsed into one Input/Output total, and Firestore is an addition (the calculator models the data layer as BigQuery, not Firestore).

**Mapping — calculator SKU → master-table column:**

| Calculator SKU row | Calculator unit | Master-table column | Status |
|---|---|---|---|
| Gemini — User Query | input / output tokens | Input tok / Output tok | ✅ aligned |
| Gemini — Tools & API Calls | input / output tokens | _(folded into Input/Output tok)_ | ⚠️ not broken out |
| Gemini — Agent Calls | input / output tokens | _(folded into Input/Output tok)_ | ⚠️ not broken out |
| Agent Runtime | $/vCPU-hr + $/GiB-hr | vCPU-s / GiB-s | ✅ aligned (allocation-time) |
| Agent Sessions | $/1K events | Session events | ✅ aligned |
| Memory Bank — generation | $/1K stored/mo + LLM MTOK | Mem-gen tok | ✅ MTOK part (monthly storage excluded) |
| Memory Bank — retrieval | $/1K returned | Mem retrieved | ✅ aligned |
| Agent Search (RAG) | $/1K queries (+ $/GB indexed/mo) | RAG queries | ✅ queries (indexed-storage not columned) |
| Grounding — Google Search | $/1K | Web grounding | ✅ aligned |
| Imagen | per image | Imagen | ✅ aligned |
| Model Armor | $/1M tokens scanned | _(folded into $/intxn)_ | ✅ in cost, no column |
| # Queries / # Turns / # Tools per turn | scale inputs (not billed) | Interactions / Total turns / Model calls | ✅ driver inputs |
| _(none — not a calculator SKU)_ | — | Firestore W/R | ➕ added (representative op-DB) |

**Calculator SKUs with no column (and why):**

| Calculator SKU | Reason not columned |
|---|---|
| Apigee, BigQuery, Veo, Google Maps grounding | Parked — tools mocked / not deployed |
| Agent Sandbox (Code Execution, Computer Use) | Deferred (no per-agent metric) / Not Launched |
| Agent Gateway, Semantic Policies, Anomaly Detection | Not Launched / unavailable |
| Agent Evaluation, Cloud Logging / Trace / Monitoring | Pending (separate collection task) |
| RAG indexed-data storage ($/GB/mo), Memory storage ($/1K/mo) | Monthly storage — not a per-interaction unit |
| Security Command Center, Identity, Registry | TBD / included at no cost |

## 1. SKU usage per interaction — model & compute (PRIMARY)

| Agent | Input tokens (range) | Output tokens (range) | Model calls | vCPU-seconds | GiB-seconds |
|---|---|---|---|---|---|
| [conversational-chatbot (archetype)](conversational_chatbot.md) | 6369 (2030–17874) | 693 (185–1876) | 7.5 | 20.9 | 39 |
| [workflow-operator (archetype)](workflow_operator.md) | 20107 (3343–74345) | 1485 (419–3502) | 14.0 | 25.3 | 47 |
| [autonomous-researcher (archetype)](autonomous_researcher.md) | 32585 (12516–122408) | 10739 (5728–18665) | 7.8 | 171.2 | 201 |
| [multi-agent-orchestrator (archetype)](multi_agent_orchestrator.md) | 149080 (6076–8349717) | 6080 (1140–106637) | 18.9 | 90.6 | 100 |
| [financial-advisor](financial_advisor.md) | 23206 (3928–149479) | 9812 (3888–93198) | 3.5 | 135.6 | 174 |
| [academic-research](academic_research.md) | 4507 (2631–9301) | 1120 (399–3734) | 3.0 | 66.5 | 85 |
| [marketing-agency](marketing_agency.md) | 10304 (3843–27818) | 4046 (1828–10681) | 3.7 | 187.9 | 231 |
| [blog-writer](blogger_agent.md) | 11345 (4187–22789) | 5425 (337–11277) | 4.8 | 101.3 | 138 |
| [on-brand-genmedia](on_brand_genmedia.md) | 83460 (24021–198338) | 7349 (2732–13376) | 17.2 | 322.7 | 329 |
| [plumber-data-engineering-assistant](plumber_agent.md) | 13800 (13475–14578) | 1958 (829–3695) | 4.0 | 104.1 | 127 |
| [memory_assistant](memory_assistant.md) | 3398 (2552–4001) | 1605 (752–3150) | 5.8 | 39.0 | 560 |
| [fomc-research](fomc_research.md) | 1838 (1306–2800) | 479 (188–949) | 2.3 | 30.1 | 55 |
| [nexshift-agent](nexshift_agent.md) | 0 (0–0) | 0 (0–0) | 0.0 | 12.8 | 37 |

## 2. SKU usage per interaction — Agent Platform features (PRIMARY)

| Agent | Session events | Memory-gen tokens | Memories written | Memory retrievals |
|---|---|---|---|---|
| [conversational-chatbot (archetype)](conversational_chatbot.md) | 15.0 | 2486 | 0.0 | 0.0 |
| [workflow-operator (archetype)](workflow_operator.md) | 27.9 | 2549 | 1.1 | 0.7 |
| [autonomous-researcher (archetype)](autonomous_researcher.md) | 15.6 | 7999 | 0.6 | 0.4 |
| [multi-agent-orchestrator (archetype)](multi_agent_orchestrator.md) | 37.9 | 2793 | 1.2 | 0.2 |
| [financial-advisor](financial_advisor.md) | 7.2 | 3151 | 0.9 | 0.6 |
| [academic-research](academic_research.md) | 6.0 | 2480 | 0.0 | 0.0 |
| [marketing-agency](marketing_agency.md) | 7.6 | 2762 | 0.6 | 0.4 |
| [blog-writer](blogger_agent.md) | 11.1 | 4603 | 0.3 | 0.3 |
| [on-brand-genmedia](on_brand_genmedia.md) | 31.6 | 4191 | 0.5 | 0.0 |
| [plumber-data-engineering-assistant](plumber_agent.md) | 8.0 | 2853 | 0.6 | 0.0 |
| [memory_assistant](memory_assistant.md) | 11.5 | 2493 | 3.2 | 2.5 |
| [fomc-research](fomc_research.md) | 4.8 | 2358 | 0.0 | 0.0 |
| [nexshift-agent](nexshift_agent.md) | 2.0 | 2390 | 1.0 | 0.0 |

_Memory retrievals are ~0 for the sample agents (no preload_memory tool); memory_assistant retrieves because cross-session recall is its purpose._

## 2b. Grounding & image generation

Collectors: **`extract_grounding_from_events`** (per-interaction, attributable — validated with a separate `grounded_news` agent) and **`collect_imagen_usage`** (Cloud Monitoring `model_invocation_count` for imagen models — validated with 7 captured invocations). Measured 0 for the agents below: their 2-turn workloads did not trigger Search or image generation; the collectors themselves are validated working.

| Agent | Grounded prompts | Images generated |
|---|---|---|
| [conversational-chatbot (archetype)](conversational_chatbot.md) | 0 | 0 |
| [workflow-operator (archetype)](workflow_operator.md) | 0 | 0 |
| [autonomous-researcher (archetype)](autonomous_researcher.md) | 0 | 0 |
| [multi-agent-orchestrator (archetype)](multi_agent_orchestrator.md) | 0 | 0 |
| [financial-advisor](financial_advisor.md) | 0 | 0 |
| [academic-research](academic_research.md) | 0 | 0 |
| [marketing-agency](marketing_agency.md) | 0 | 0 |
| [blog-writer](blogger_agent.md) | 61 | 0 |
| [on-brand-genmedia](on_brand_genmedia.md) | 0 | 27 |
| [plumber-data-engineering-assistant](plumber_agent.md) | 0 | 0 |
| [memory_assistant](memory_assistant.md) | 0 | 0 |
| [fomc-research](fomc_research.md) | 0 | 0 |
| [nexshift-agent](nexshift_agent.md) | 0 | 0 |

_Would bill ~$0.035 per grounded prompt (Gemini 2.x) and ~$0.04 per image (Imagen) if triggered._

## 3. SKU presence matrix (which agents touch which SKUs)

| Agent | Gemini tokens | Agent Runtime | Sessions | Memory Bank | Search grounding | Image gen |
|---|---|---|---|---|---|---|
| [conversational-chatbot (archetype)](conversational_chatbot.md) | ✓ | ✓ | ✓ | ✓ (write) | — | — (BigQuery KB mocked) |
| [workflow-operator (archetype)](workflow_operator.md) | ✓ | ✓ | ✓ | ✓ (write) | — | — (BigQuery/Apigee mocked) |
| [autonomous-researcher (archetype)](autonomous_researcher.md) | ✓ | ✓ | ✓ | ✓ (write) | **measured non-zero** | — |
| [multi-agent-orchestrator (archetype)](multi_agent_orchestrator.md) | ✓ | ✓ | ✓ | ✓ (write) | — | — (BigQuery/RAG mocked) |
| [financial-advisor](financial_advisor.md) | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — |
| [academic-research](academic_research.md) | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — |
| [marketing-agency](marketing_agency.md) | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | capable, 0 measured |
| [blog-writer](blogger_agent.md) | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — |
| [on-brand-genmedia](on_brand_genmedia.md) | ✓ | ✓ | ✓ | ✓ (write) | — | **27 images measured (gemini-2.5-flash-image)** |
| [plumber-data-engineering-assistant](plumber_agent.md) | ✓ | ✓ | ✓ | ✓ (write) | — | — (+BQ/GCS/Dataflow/Dataproc/Dataform by intent) |
| [memory_assistant](memory_assistant.md) | ✓ | ✓ | ✓ | ✓ (write+read) | — | — |
| [fomc-research](fomc_research.md) | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — (BigQuery + Cloud Storage intended) |
| [nexshift-agent](nexshift_agent.md) | ✓ | ✓ (CP-SAT compute) | ✓ | ✓ (write) | — | — |

**+ Firestore (operational DB):** the 4 archetype agents also exercise a real **Firestore** SKU (save_note/load_note → document writes/reads, scoped per authenticated user). Measured non-zero on all 4 (workflow_operator heaviest: ~1 read + ~1 write/interaction). Cost is negligible (~$3e-7/interaction) but the SKU is exercised + measured. Not in the calculator (it only models BigQuery + Vector Search for data). The sample agents (EXP-006/007) don't use it.

## 4. Secondary: derived cost per interaction (usage × catalog list price)

Reference only — list price, not actual billed. The usage tables above are the deliverable.

| Agent | Gemini $ | Runtime $ | Mem+Sess $ | Total $ (range) | Cost variability |
|---|---|---|---|---|---|
| [on-brand-genmedia](on_brand_genmedia.md) | 0.0434 | 0.0086 | 0.0015 | 0.0934 (0.0549–0.1254) | Medium |
| [multi-agent-orchestrator (archetype)](multi_agent_orchestrator.md) | 0.0599 | 0.0067 | 0.0104 | 0.0932 (0.0225–2.7886) | Very high |
| [autonomous-researcher (archetype)](autonomous_researcher.md) | 0.0366 | 0.0101 | 0.0065 | 0.0822 (0.0347–0.1000) | Medium |
| [blog-writer](blogger_agent.md) | 0.0170 | 0.0058 | 0.0043 | 0.0638 (0.0389–0.0719) | High |
| [financial-advisor](financial_advisor.md) | 0.0315 | 0.0084 | 0.0030 | 0.0595 (0.0223–0.2893) | Very high |
| [marketing-agency](marketing_agency.md) | 0.0132 | 0.0062 | 0.0030 | 0.0339 (0.0149–0.0442) | Medium |
| [workflow-operator (archetype)](workflow_operator.md) | 0.0097 | 0.0029 | 0.0081 | 0.0232 (0.0132–0.0416) | High |
| [academic-research](academic_research.md) | 0.0042 | 0.0028 | 0.0023 | 0.0201 (0.0069–0.0172) | High |
| [memory_assistant](memory_assistant.md) | 0.0050 | 0.0035 | 0.0080 | 0.0165 (0.0144–0.0206) | High |
| [plumber-data-engineering-assistant](plumber_agent.md) | 0.0090 | 0.0028 | 0.0009 | 0.0143 (0.0099–0.0172) | Medium |
| [conversational-chatbot (archetype)](conversational_chatbot.md) | 0.0036 | 0.0019 | 0.0045 | 0.0139 (0.0074–0.0160) | High |
| [fomc-research](fomc_research.md) | 0.0017 | 0.0009 | 0.0007 | 0.0035 (0.0025–0.0048) | Medium |
| [nexshift-agent](nexshift_agent.md) | 0.0000 | 0.0004 | 0.0007 | 0.0011 (0.0011–0.0011) | Low |

## 5. Usage-pattern observations

1. **Input-token usage is the biggest differentiator** — financial-advisor consumes ~149080 input tokens/interaction vs ~0 for the lightest, a 149080× spread driven by depth of multi-specialist analysis.
2. **vCPU-seconds track analysis depth**, not just call count — the heaviest agent burns far more compute per interaction.
3. **Output-token usage is the most variable SKU** run-to-run (the model varies how much it reasons), so token usage should be reported as a range, not a single number.
4. **Memory generation + session events are consumed even when memories are never read back** — a real SKU footprint for any session-persisted agent.
5. **Grounding and Imagen collectors are validated** (separate validation runs registered non-zero usage). For the 5 agents above the workloads simply didn't trigger them.

## 6. Experiment query volume (what we actually sent)

Each agent's test consists of N **interactions**, each = a 2-turn conversation + a memory-write (memory_assistant = 3-turn). Inside one interaction the user_id stays constant; across interactions we mint a fresh user_id so memory state doesn't carry over. Sample agents (EXP-006/007) repeat one 2-turn workload; **archetype agents (EXP-008) cycle multiple conversation scenarios of varying length** (2–5 turns).

| Agent | Interactions | Turns/interaction | Total user turns | Source |
|---|---|---|---|---|
| [conversational-chatbot (archetype)](conversational_chatbot.md) | 85 | 2–40 | **432** | EXP-008 (archetype) |
| [multi-agent-orchestrator (archetype)](multi_agent_orchestrator.md) | 85 | 2–40 | **432** | EXP-008 (archetype) |
| [workflow-operator (archetype)](workflow_operator.md) | 85 | 2–35 | **426** | EXP-008 (archetype) |
| [autonomous-researcher (archetype)](autonomous_researcher.md) | 45 | 2–32 | **253** | EXP-008 (archetype) |
| [financial-advisor](financial_advisor.md) | 45 | 2–16 | **160** | EXP-006 |
| [academic-research](academic_research.md) | 45 | 2–16 | **160** | EXP-006 |
| [blog-writer](blogger_agent.md) | 45 | 2–16 | **160** | EXP-006 |
| [marketing-agency](marketing_agency.md) | 45 | 2–16 | **160** | EXP-006 |
| [nexshift-agent](nexshift_agent.md) | 35 | 2 | **70** | EXP-007 |
| [fomc-research](fomc_research.md) | 35 | 2 | **70** | EXP-007 |
| [plumber-data-engineering-assistant](plumber_agent.md) | 35 | 2 | **70** | EXP-007 |
| [on-brand-genmedia](on_brand_genmedia.md) | 35 | 2 | **70** | EXP-007 |
| [memory_assistant](memory_assistant.md) | 4 | 3 | **12** | EXP-005 |
| grounded_news (validation) | 2 | 1 | **2** | collector-validation |
| **TOTAL** | — | — | **2477** | all experiments combined |

Full per-turn transcripts (input, output_text, tool calls/responses, per-step usage) live at `data/transcript_<agent>.jsonl` locally. **Not committed** — `data/` is gitignored as runtime artifact. Each per-agent doc's §7 shows the workload prompts + one sample interaction inline.

## Per-agent detail docs

- [conversational-chatbot (archetype)](conversational_chatbot.md) — Calculator archetype: Conversational Chatbot / Moderate.
- [workflow-operator (archetype)](workflow_operator.md) — Calculator archetype: Workflow Operator / Moderate.
- [autonomous-researcher (archetype)](autonomous_researcher.md) — Calculator archetype: Autonomous Researcher / Moderate.
- [multi-agent-orchestrator (archetype)](multi_agent_orchestrator.md) — Calculator archetype: Multi-Agent Orchestrator / Moderate.
- [financial-advisor](financial_advisor.md) — Stock analysis & trading-strategy advisor.
- [academic-research](academic_research.md) — Academic literature discovery & analysis.
- [marketing-agency](marketing_agency.md) — End-to-end branding suite: domain, website, marketing, logo (Imagen) creators wrapped as AgentTools under one coordinator.
- [blog-writer](blogger_agent.md) — Multi-agent technical blog authoring.
- [on-brand-genmedia](on_brand_genmedia.md) — Brand-compliant iterative image generation.
- [plumber-data-engineering-assistant](plumber_agent.md) — Build/deploy data pipelines.
- [memory_assistant](memory_assistant.md) — Personal assistant with long-term cross-session memory.
- [fomc-research](fomc_research.md) — FOMC meeting financial-analysis report.
- [nexshift-agent](nexshift_agent.md) — AI nurse rostering optimizer.

## Method & reproducibility

Per agent: `python scripts/exp_sample.py --package <pkg> --runs 40 --settle 300`. Token usage from model responses (exact); vCPU/GiB-seconds + Memory Bank usage from Cloud Monitoring (per-engine); grounding from event `grounding_metadata` (per-interaction); Imagen from Monitoring `model_invocation_count` (model_user_id contains 'imagen'). Prices from the live Cloud Billing Catalog. Master summary regenerated by `scripts/build_summaries.py`.

_See also: [COMBINED_SKU_USAGE_REPORT.md](../COMBINED_SKU_USAGE_REPORT.md) (repo-root version of §1–§5 above), [GEAP_COMPONENTS.md](../GEAP_COMPONENTS.md), [COST_DATA_COLLECTION_PROCESS.md](../COST_DATA_COLLECTION_PROCESS.md), [PROJECT_RUNBOOK.md](../PROJECT_RUNBOOK.md)._