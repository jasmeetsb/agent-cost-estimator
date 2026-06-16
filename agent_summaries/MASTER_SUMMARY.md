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

- **multi-agent-orchestrator (archetype)** — Calculator archetype: Multi-Agent Orchestrator / Moderate. Coordinator + 3 specialist sub-agents. Fan-out-driven; most expensive archetype. → [details](multi_agent_orchestrator.md)
- **on-brand-genmedia** — Brand-compliant iterative image generation. Loop + Hierarchical: prompt → image (gemini-2.5-flash-image) → score → re-prompt if below threshold. Heaviest image-gen SKU usage in the corpus. → [details](on_brand_genmedia.md)
- **autonomous-researcher (archetype)** — Calculator archetype: Autonomous Researcher / Moderate. Single agent + Google Search grounding, long outputs. Token-depth-driven; exercises Search grounding. → [details](autonomous_researcher.md)
- **financial-advisor** — Stock analysis & trading-strategy advisor. Hierarchical: coordinator + 4 AgentTool specialists (data, trading, execution, risk). Heaviest input-token consumer; runtime-dominated. → [details](financial_advisor.md)
- **workflow-operator (archetype)** — Calculator archetype: Workflow Operator / Moderate. Single agent driving an 8-tool order workflow. Tool-fan-out-driven (highest session-event churn). → [details](workflow_operator.md)
- **plumber-data-engineering-assistant** — Build/deploy data pipelines. Deepest hierarchy in the corpus: root + 6 specialist sub-agents (Dataflow / Dataproc / Dataproc-templates / dbt / GitHub / Cloud Monitoring). Touches ~10–11 distinct GCP product SKUs by intent. → [details](plumber_agent.md)
- **blog-writer** — Multi-agent technical blog authoring. Coordinator + 4 sub-agents (outline, draft, edit, social) + HITL refinement. → [details](blogger_agent.md)
- **marketing-agency** — End-to-end branding suite: domain, website, marketing, logo (Imagen) creators wrapped as AgentTools under one coordinator. → [details](marketing_agency.md)
- **conversational-chatbot (archetype)** — Calculator archetype: Conversational Chatbot / Moderate. Single support agent + light tools + Memory Bank. Cheapest archetype; volume-driven. → [details](conversational_chatbot.md)
- **academic-research** — Academic literature discovery & analysis. Coordinator + AgentTool websearch + new-research specialists. → [details](academic_research.md)
- **memory_assistant** — Personal assistant with long-term cross-session memory. Coordinator + 2 sub-agents + Memory Bank (write+read). Exercises the most Agent Platform features in this corpus. → [details](memory_assistant.md)
- **fomc-research** — FOMC meeting financial-analysis report. Hierarchical + Sequential multimodal pipeline (BigQuery metadata + PDF transcripts via pdfplumber + multimodal Gemini). → [details](fomc_research.md)
- **nexshift-agent** — AI nurse rostering optimizer. Coordinator + 7 sub-agents + OR-Tools CP-SAT solver. 4 orchestration patterns (Hierarchical + Sequential + Parallel + HITL), 31 tools — broadest tool surface in the corpus. → [details](nexshift_agent.md)

## 1. SKU usage per interaction — model & compute (PRIMARY)

| Agent | Input tokens (range) | Output tokens (range) | Model calls | vCPU-seconds | GiB-seconds |
|---|---|---|---|---|---|
| [multi-agent-orchestrator (archetype)](multi_agent_orchestrator.md) | 106645 (8224–6403427) | 5680 (1576–74261) | 17.9 | 144.8 | 177 |
| [on-brand-genmedia](on_brand_genmedia.md) | 83460 (24021–198338) | 7349 (2732–13376) | 17.2 | 322.7 | 329 |
| [autonomous-researcher (archetype)](autonomous_researcher.md) | 42348 (16990–92711) | 8993 (4939–14742) | 7.8 | 407.9 | 432 |
| [financial-advisor](financial_advisor.md) | 27586 (3667–139557) | 1724 (780–8097) | 3.6 | 347.5 | 420 |
| [workflow-operator (archetype)](workflow_operator.md) | 21146 (3343–74345) | 1528 (583–3502) | 15.3 | 52.8 | 84 |
| [plumber-data-engineering-assistant](plumber_agent.md) | 13800 (13475–14578) | 1958 (829–3695) | 4.0 | 104.1 | 127 |
| [blog-writer](blogger_agent.md) | 8121 (3278–13401) | 5334 (451–8595) | 5.0 | 225.9 | 259 |
| [marketing-agency](marketing_agency.md) | 6206 (3386–18972) | 1031 (578–2626) | 4.2 | 79.7 | 138 |
| [conversational-chatbot (archetype)](conversational_chatbot.md) | 6034 (2030–17874) | 669 (188–1860) | 7.5 | 28.9 | 57 |
| [academic-research](academic_research.md) | 4058 (2367–8369) | 890 (393–3026) | 3.1 | 72.7 | 125 |
| [memory_assistant](memory_assistant.md) | 3398 (2552–4001) | 1605 (752–3150) | 5.8 | 39.0 | 560 |
| [fomc-research](fomc_research.md) | 1838 (1306–2800) | 479 (188–949) | 2.3 | 30.1 | 55 |
| [nexshift-agent](nexshift_agent.md) | 0 (0–0) | 0 (0–0) | 0.0 | 12.8 | 37 |

## 2. SKU usage per interaction — Agent Platform features (PRIMARY)

| Agent | Session events | Memory-gen tokens | Memories written | Memory retrievals |
|---|---|---|---|---|
| [multi-agent-orchestrator (archetype)](multi_agent_orchestrator.md) | 35.7 | 2797 | 1.3 | 0.0 |
| [on-brand-genmedia](on_brand_genmedia.md) | 31.6 | 4191 | 0.5 | 0.0 |
| [autonomous-researcher (archetype)](autonomous_researcher.md) | 15.5 | 8171 | 0.8 | 0.0 |
| [financial-advisor](financial_advisor.md) | 7.3 | 3377 | 0.8 | 0.0 |
| [workflow-operator (archetype)](workflow_operator.md) | 30.6 | 2552 | 1.2 | 0.0 |
| [plumber-data-engineering-assistant](plumber_agent.md) | 8.0 | 2853 | 0.6 | 0.0 |
| [blog-writer](blogger_agent.md) | 11.5 | 5386 | 0.2 | 0.0 |
| [marketing-agency](marketing_agency.md) | 8.3 | 2753 | 0.7 | 0.0 |
| [conversational-chatbot (archetype)](conversational_chatbot.md) | 14.9 | 2461 | 0.0 | 0.0 |
| [academic-research](academic_research.md) | 6.2 | 2555 | 0.1 | 0.0 |
| [memory_assistant](memory_assistant.md) | 11.5 | 2493 | 3.2 | 2.5 |
| [fomc-research](fomc_research.md) | 4.8 | 2358 | 0.0 | 0.0 |
| [nexshift-agent](nexshift_agent.md) | 2.0 | 2390 | 1.0 | 0.0 |

_Memory retrievals are ~0 for the sample agents (no preload_memory tool); memory_assistant retrieves because cross-session recall is its purpose._

## 2b. Grounding & image generation

Collectors: **`extract_grounding_from_events`** (per-interaction, attributable — validated with a separate `grounded_news` agent) and **`collect_imagen_usage`** (Cloud Monitoring `model_invocation_count` for imagen models — validated with 7 captured invocations). Measured 0 for the agents below: their 2-turn workloads did not trigger Search or image generation; the collectors themselves are validated working.

| Agent | Grounded prompts | Images generated |
|---|---|---|
| [multi-agent-orchestrator (archetype)](multi_agent_orchestrator.md) | 0 | 0 |
| [on-brand-genmedia](on_brand_genmedia.md) | 0 | 27 |
| [autonomous-researcher (archetype)](autonomous_researcher.md) | 0 | 0 |
| [financial-advisor](financial_advisor.md) | 0 | 0 |
| [workflow-operator (archetype)](workflow_operator.md) | 0 | 0 |
| [plumber-data-engineering-assistant](plumber_agent.md) | 0 | 0 |
| [blog-writer](blogger_agent.md) | 40 | 0 |
| [marketing-agency](marketing_agency.md) | 0 | 0 |
| [conversational-chatbot (archetype)](conversational_chatbot.md) | 0 | 0 |
| [academic-research](academic_research.md) | 0 | 0 |
| [memory_assistant](memory_assistant.md) | 0 | 0 |
| [fomc-research](fomc_research.md) | 0 | 0 |
| [nexshift-agent](nexshift_agent.md) | 0 | 0 |

_Would bill ~$0.035 per grounded prompt (Gemini 2.x) and ~$0.04 per image (Imagen) if triggered._

## 3. SKU presence matrix (which agents touch which SKUs)

| Agent | Gemini tokens | Agent Runtime | Sessions | Memory Bank | Search grounding | Image gen |
|---|---|---|---|---|---|---|
| [multi-agent-orchestrator (archetype)](multi_agent_orchestrator.md) | ✓ | ✓ | ✓ | ✓ (write) | — | — (BigQuery/RAG mocked) |
| [on-brand-genmedia](on_brand_genmedia.md) | ✓ | ✓ | ✓ | ✓ (write) | — | **27 images measured (gemini-2.5-flash-image)** |
| [autonomous-researcher (archetype)](autonomous_researcher.md) | ✓ | ✓ | ✓ | ✓ (write) | **measured non-zero** | — |
| [financial-advisor](financial_advisor.md) | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — |
| [workflow-operator (archetype)](workflow_operator.md) | ✓ | ✓ | ✓ | ✓ (write) | — | — (BigQuery/Apigee mocked) |
| [plumber-data-engineering-assistant](plumber_agent.md) | ✓ | ✓ | ✓ | ✓ (write) | — | — (+BQ/GCS/Dataflow/Dataproc/Dataform by intent) |
| [blog-writer](blogger_agent.md) | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — |
| [marketing-agency](marketing_agency.md) | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | capable, 0 measured |
| [conversational-chatbot (archetype)](conversational_chatbot.md) | ✓ | ✓ | ✓ | ✓ (write) | — | — (BigQuery KB mocked) |
| [academic-research](academic_research.md) | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — |
| [memory_assistant](memory_assistant.md) | ✓ | ✓ | ✓ | ✓ (write+read) | — | — |
| [fomc-research](fomc_research.md) | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — (BigQuery + Cloud Storage intended) |
| [nexshift-agent](nexshift_agent.md) | ✓ | ✓ (CP-SAT compute) | ✓ | ✓ (write) | — | — |

**+ Firestore (operational DB):** the 4 archetype agents also exercise a real **Firestore** SKU (save_note/load_note → document writes/reads, scoped per authenticated user). Measured non-zero on all 4 (workflow_operator heaviest: ~1 read + ~1 write/interaction). Cost is negligible (~$3e-7/interaction) but the SKU is exercised + measured. Not in the calculator (it only models BigQuery + Vector Search for data). The sample agents (EXP-006/007) don't use it.

## 4. Secondary: derived cost per interaction (usage × catalog list price)

Reference only — list price, not actual billed. The usage tables above are the deliverable.

| Agent | Gemini $ | Runtime $ | Mem+Sess $ | Total $ (range) | Cost variability |
|---|---|---|---|---|---|
| [on-brand-genmedia](on_brand_genmedia.md) | 0.0434 | 0.0086 | 0.0015 | 0.0934 (0.0549–0.1254) | Medium |
| [autonomous-researcher (archetype)](autonomous_researcher.md) | 0.0352 | 0.0109 | 0.0063 | 0.0793 (0.0346–0.0773) | Medium |
| [multi-agent-orchestrator (archetype)](multi_agent_orchestrator.md) | 0.0462 | 0.0064 | 0.0098 | 0.0742 (0.0236–2.1228) | Very high |
| [blog-writer](blogger_agent.md) | 0.0158 | 0.0061 | 0.0045 | 0.0638 (0.0477–0.0690) | Medium |
| [financial-advisor](financial_advisor.md) | 0.0126 | 0.0094 | 0.0029 | 0.0280 (0.0160–0.0587) | Very high |
| [workflow-operator (archetype)](workflow_operator.md) | 0.0102 | 0.0033 | 0.0084 | 0.0242 (0.0148–0.0422) | High |
| [academic-research](academic_research.md) | 0.0034 | 0.0021 | 0.0023 | 0.0183 (0.0061–0.0131) | High |
| [memory_assistant](memory_assistant.md) | 0.0050 | 0.0035 | 0.0080 | 0.0165 (0.0144–0.0206) | High |
| [plumber-data-engineering-assistant](plumber_agent.md) | 0.0090 | 0.0028 | 0.0009 | 0.0143 (0.0099–0.0172) | Medium |
| [conversational-chatbot (archetype)](conversational_chatbot.md) | 0.0035 | 0.0019 | 0.0045 | 0.0139 (0.0074–0.0159) | High |
| [marketing-agency](marketing_agency.md) | 0.0044 | 0.0023 | 0.0029 | 0.0133 (0.0080–0.0174) | Medium |
| [fomc-research](fomc_research.md) | 0.0017 | 0.0009 | 0.0007 | 0.0035 (0.0025–0.0048) | Medium |
| [nexshift-agent](nexshift_agent.md) | 0.0000 | 0.0004 | 0.0007 | 0.0011 (0.0011–0.0011) | Low |

## 5. Usage-pattern observations

1. **Input-token usage is the biggest differentiator** — financial-advisor consumes ~106645 input tokens/interaction vs ~0 for the lightest, a 106645× spread driven by depth of multi-specialist analysis.
2. **vCPU-seconds track analysis depth**, not just call count — the heaviest agent burns far more compute per interaction.
3. **Output-token usage is the most variable SKU** run-to-run (the model varies how much it reasons), so token usage should be reported as a range, not a single number.
4. **Memory generation + session events are consumed even when memories are never read back** — a real SKU footprint for any session-persisted agent.
5. **Grounding and Imagen collectors are validated** (separate validation runs registered non-zero usage). For the 5 agents above the workloads simply didn't trigger them.

## 6. Experiment query volume (what we actually sent)

Each agent's test consists of N **interactions**, each = a 2-turn conversation + a memory-write (memory_assistant = 3-turn). Inside one interaction the user_id stays constant; across interactions we mint a fresh user_id so memory state doesn't carry over. Sample agents (EXP-006/007) repeat one 2-turn workload; **archetype agents (EXP-008) cycle multiple conversation scenarios of varying length** (2–5 turns).

| Agent | Interactions | Turns/interaction | Total user turns | Source |
|---|---|---|---|---|
| [conversational-chatbot (archetype)](conversational_chatbot.md) | 80 | 2–5 | **288** | EXP-008 (archetype) |
| [workflow-operator (archetype)](workflow_operator.md) | 80 | 2–5 | **288** | EXP-008 (archetype) |
| [multi-agent-orchestrator (archetype)](multi_agent_orchestrator.md) | 80 | 2–5 | **288** | EXP-008 (archetype) |
| [autonomous-researcher (archetype)](autonomous_researcher.md) | 40 | 2–4 | **128** | EXP-008 (archetype) |
| [financial-advisor](financial_advisor.md) | 40 | 2 | **80** | EXP-006 |
| [academic-research](academic_research.md) | 40 | 2 | **80** | EXP-006 |
| [blog-writer](blogger_agent.md) | 40 | 2 | **80** | EXP-006 |
| [marketing-agency](marketing_agency.md) | 40 | 2 | **80** | EXP-006 |
| [nexshift-agent](nexshift_agent.md) | 35 | 2 | **70** | EXP-007 |
| [fomc-research](fomc_research.md) | 35 | 2 | **70** | EXP-007 |
| [plumber-data-engineering-assistant](plumber_agent.md) | 35 | 2 | **70** | EXP-007 |
| [on-brand-genmedia](on_brand_genmedia.md) | 35 | 2 | **70** | EXP-007 |
| [memory_assistant](memory_assistant.md) | 4 | 3 | **12** | EXP-005 |
| grounded_news (validation) | 2 | 1 | **2** | collector-validation |
| **TOTAL** | — | — | **1606** | all experiments combined |

Full per-turn transcripts (input, output_text, tool calls/responses, per-step usage) live at `data/transcript_<agent>.jsonl` locally. **Not committed** — `data/` is gitignored as runtime artifact. Each per-agent doc's §7 shows the workload prompts + one sample interaction inline.

## Per-agent detail docs

- [multi-agent-orchestrator (archetype)](multi_agent_orchestrator.md) — Calculator archetype: Multi-Agent Orchestrator / Moderate.
- [on-brand-genmedia](on_brand_genmedia.md) — Brand-compliant iterative image generation.
- [autonomous-researcher (archetype)](autonomous_researcher.md) — Calculator archetype: Autonomous Researcher / Moderate.
- [financial-advisor](financial_advisor.md) — Stock analysis & trading-strategy advisor.
- [workflow-operator (archetype)](workflow_operator.md) — Calculator archetype: Workflow Operator / Moderate.
- [plumber-data-engineering-assistant](plumber_agent.md) — Build/deploy data pipelines.
- [blog-writer](blogger_agent.md) — Multi-agent technical blog authoring.
- [marketing-agency](marketing_agency.md) — End-to-end branding suite: domain, website, marketing, logo (Imagen) creators wrapped as AgentTools under one coordinator.
- [conversational-chatbot (archetype)](conversational_chatbot.md) — Calculator archetype: Conversational Chatbot / Moderate.
- [academic-research](academic_research.md) — Academic literature discovery & analysis.
- [memory_assistant](memory_assistant.md) — Personal assistant with long-term cross-session memory.
- [fomc-research](fomc_research.md) — FOMC meeting financial-analysis report.
- [nexshift-agent](nexshift_agent.md) — AI nurse rostering optimizer.

## Method & reproducibility

Per agent: `python scripts/exp_sample.py --package <pkg> --runs 40 --settle 300`. Token usage from model responses (exact); vCPU/GiB-seconds + Memory Bank usage from Cloud Monitoring (per-engine); grounding from event `grounding_metadata` (per-interaction); Imagen from Monitoring `model_invocation_count` (model_user_id contains 'imagen'). Prices from the live Cloud Billing Catalog. Master summary regenerated by `scripts/build_summaries.py`.

_See also: [COMBINED_SKU_USAGE_REPORT.md](../COMBINED_SKU_USAGE_REPORT.md) (repo-root version of §1–§5 above), [GEAP_COMPONENTS.md](../GEAP_COMPONENTS.md), [COST_DATA_COLLECTION_PROCESS.md](../COST_DATA_COLLECTION_PROCESS.md), [PROJECT_RUNBOOK.md](../PROJECT_RUNBOOK.md)._