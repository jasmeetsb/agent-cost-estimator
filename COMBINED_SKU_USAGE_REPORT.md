# Combined SKU-Usage Report — ADK Agents on Gemini Enterprise Agent Platform

**Purpose:** estimate **usage per SKU** across different agent architectures deployed to Vertex AI Agent Engine. Usage quantities are the primary output; dollar cost is a secondary derived view (usage × catalog list price). This is **not** an expense report or a cost-optimization exercise — it characterizes what each agent *consumes*, by SKU.

Unit = one interaction = a conversation + a memory-write. The 4 archetype agents use **multi-turn** workloads (2–5 turns, ~80% of interactions >2 turns); the adk-sample agents use a 2-turn workload. All gemini-2.5-flash. Runs per agent vary (archetypes 40–80; samples 40 — see each agent's summary). Usage from model responses + Cloud Monitoring (per-engine).

## 1. SKU usage per interaction — model & compute (PRIMARY)

| Agent | Input tokens (range) | Output tokens (range) | Model calls | vCPU-seconds | GiB-seconds |
|---|---|---|---|---|---|
| conversational-chatbot (archetype) | 6369 (2030–17874) | 693 (185–1876) | 7.5 | 20.9 | 39 |
| workflow-operator (archetype) | 20107 (3343–74345) | 1485 (419–3502) | 14.0 | 25.3 | 47 |
| autonomous-researcher (archetype) | 44234 (16990–166168) | 8482 (4524–14742) | 7.8 | 171.2 | 201 |
| multi-agent-orchestrator (archetype) | 149080 (6076–8349717) | 6080 (1140–106637) | 18.9 | 90.6 | 100 |
| financial-advisor | 27586 (3667–139557) | 1724 (780–8097) | 3.6 | 347.5 | 420 |
| academic-research | 4058 (2367–8369) | 890 (393–3026) | 3.1 | 72.7 | 125 |
| marketing-agency | 6206 (3386–18972) | 1031 (578–2626) | 4.2 | 79.7 | 138 |
| blog-writer | 8121 (3278–13401) | 5334 (451–8595) | 5.0 | 225.9 | 259 |
| on-brand-genmedia | 83460 (24021–198338) | 7349 (2732–13376) | 17.2 | 322.7 | 329 |
| plumber-data-engineering-assistant | 13800 (13475–14578) | 1958 (829–3695) | 4.0 | 104.1 | 127 |
| memory_assistant | 3398 (2552–4001) | 1605 (752–3150) | 5.8 | 39.0 | 560 |
| fomc-research | 1838 (1306–2800) | 479 (188–949) | 2.3 | 30.1 | 55 |
| nexshift-agent | 0 (0–0) | 0 (0–0) | 0.0 | 12.8 | 37 |

## 2. SKU usage per interaction — Agent Platform features (PRIMARY)

| Agent | Session events | Memory-gen tokens | Memories written | Memory retrievals |
|---|---|---|---|---|
| conversational-chatbot (archetype) | 15.0 | 2486 | 0.0 | 0.0 |
| workflow-operator (archetype) | 27.9 | 2549 | 1.1 | 0.7 |
| autonomous-researcher (archetype) | 15.6 | 7999 | 0.6 | 0.4 |
| multi-agent-orchestrator (archetype) | 37.9 | 2793 | 1.2 | 0.2 |
| financial-advisor | 7.3 | 3377 | 0.8 | 0.0 |
| academic-research | 6.2 | 2555 | 0.1 | 0.0 |
| marketing-agency | 8.3 | 2753 | 0.7 | 0.0 |
| blog-writer | 11.5 | 5386 | 0.2 | 0.0 |
| on-brand-genmedia | 31.6 | 4191 | 0.5 | 0.0 |
| plumber-data-engineering-assistant | 8.0 | 2853 | 0.6 | 0.0 |
| memory_assistant | 11.5 | 2493 | 3.2 | 2.5 |
| fomc-research | 4.8 | 2358 | 0.0 | 0.0 |
| nexshift-agent | 2.0 | 2390 | 1.0 | 0.0 |

_Memory retrievals are ~0 for the sample agents (no preload_memory tool); memory_assistant retrieves because cross-session recall is its purpose._

## 2b. Grounding & media usage (now collected)

Collectors added for Google Search grounding (Cloud Monitoring) and image generation (response events). **Measured 0 for all agents in these runs** — the agents have the capability but the short 2-turn workloads did not trigger Search or image generation.

| Agent | Web-search grounded requests | Images generated |
|---|---|---|
| conversational-chatbot (archetype) | 0 | 0 |
| workflow-operator (archetype) | 0 | 0 |
| autonomous-researcher (archetype) | 0 | 0 |
| multi-agent-orchestrator (archetype) | 0 | 0 |
| financial-advisor | 0 | 0 |
| academic-research | 0 | 0 |
| marketing-agency | 0 | 0 |
| blog-writer | 40 | 0 |
| on-brand-genmedia | 0 | 27 |
| plumber-data-engineering-assistant | 0 | 0 |
| memory_assistant | 0 | 0 |
| fomc-research | 0 | 0 |
| nexshift-agent | 0 | 0 |

_Would bill ~$0.035 per grounded request (Gemini 2.x) and ~$0.04 per image (Imagen) if triggered._

## 2c. State & retrieval usage — Firestore + Vertex AI Search/RAG (PRIMARY)

Per-interaction quantities for the archetype agents (Firestore document ops via ADK note tools; RAG queries via VertexAiSearchTool against the synthetic corpus). Measured from the event stream / transcript.

| Agent | Firestore writes | Firestore reads | Vertex AI Search (RAG) queries | Google Search grounded turns |
|---|---|---|---|---|
| conversational-chatbot (archetype) | 0.03 | 0.00 | 2.15 | 0.00 |
| workflow-operator (archetype) | 1.42 | 1.23 | 0.00 | 0.00 |
| autonomous-researcher (archetype) | 1.34 | 2.06 | 1.18 | 1.62 |
| multi-agent-orchestrator (archetype) | 0.29 | 0.63 | 0.42 | 0.00 |
| financial-advisor | 0.00 | 0.93 | 0.17 | 0.95 |
| academic-research | 0.05 | 0.68 | 0.38 | 0.68 |
| marketing-agency | 0.00 | 1.00 | 2.00 | 0.00 |
| blog-writer | 0.00 | 1.00 | 0.72 | 0.00 |

_RAG priced at $1.50/1K queries, Google Search grounding at $14/1K grounded turns, Firestore at catalog read/write rates (GE AP calculator). Usage counts are the deliverable; cost is the secondary view in §4. Google Search grounding = web_researcher AgentTool invocations (native google_search grounding_metadata is encapsulated by the tool; Monitoring does not track native ADK google_search)._

## 3. SKU presence matrix (which agents touch which SKUs)

| Agent | Gemini tokens | Agent Runtime | Sessions | Memory Bank | Search grounding | Image gen |
|---|---|---|---|---|---|---|
| financial-advisor | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — |
| academic-research | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — |
| marketing-agency | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | capable, 0 measured |
| blog-writer | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — |
| on-brand-genmedia | ✓ | ✓ | ✓ | ✓ (write) | — | **27 images measured (gemini-2.5-flash-image)** |
| plumber-data-engineering-assistant | ✓ | ✓ | ✓ | ✓ (write) | — | — (+BQ/GCS/Dataflow/Dataproc/Dataform by intent) |
| memory_assistant | ✓ | ✓ | ✓ | ✓ (write+read) | — | — |
| fomc-research | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — (BigQuery + Cloud Storage intended) |
| nexshift-agent | ✓ | ✓ (CP-SAT compute) | ✓ | ✓ (write) | — | — |

## 4. Secondary: derived cost per interaction (usage × catalog list price)

Reference only — list price, not actual billed. The usage tables above are the deliverable.

| Agent | Gemini $ | Runtime $ | Mem+Sess $ | Total $ (range) | Cost variability |
|---|---|---|---|---|---|
| on-brand-genmedia | 0.0434 | 0.0086 | 0.0015 | 0.0934 (0.0549–0.1254) | Medium |
| multi-agent-orchestrator (archetype) | 0.0599 | 0.0067 | 0.0104 | 0.0932 (0.0225–2.7886) | Very high |
| autonomous-researcher (archetype) | 0.0345 | 0.0101 | 0.0065 | 0.0810 (0.0340–0.1005) | Medium |
| blog-writer | 0.0158 | 0.0061 | 0.0045 | 0.0638 (0.0477–0.0690) | Medium |
| financial-advisor | 0.0126 | 0.0094 | 0.0029 | 0.0413 (0.0160–0.0587) | Very high |
| workflow-operator (archetype) | 0.0097 | 0.0029 | 0.0081 | 0.0232 (0.0132–0.0416) | High |
| academic-research | 0.0034 | 0.0021 | 0.0023 | 0.0183 (0.0061–0.0131) | High |
| memory_assistant | 0.0050 | 0.0035 | 0.0080 | 0.0165 (0.0144–0.0206) | High |
| plumber-data-engineering-assistant | 0.0090 | 0.0028 | 0.0009 | 0.0143 (0.0099–0.0172) | Medium |
| conversational-chatbot (archetype) | 0.0036 | 0.0019 | 0.0045 | 0.0139 (0.0074–0.0160) | High |
| marketing-agency | 0.0044 | 0.0023 | 0.0029 | 0.0133 (0.0080–0.0174) | Medium |
| fomc-research | 0.0017 | 0.0009 | 0.0007 | 0.0035 (0.0025–0.0048) | Medium |
| nexshift-agent | 0.0000 | 0.0004 | 0.0007 | 0.0011 (0.0011–0.0011) | Low |

## 5. Usage-pattern observations

1. **Input-token usage is the biggest differentiator** — financial-advisor consumes ~149080 input tokens/interaction vs ~0 for the lightest, a 149080× spread driven by depth of multi-specialist analysis.
2. **vCPU-seconds track analysis depth**, not just call count — the heaviest agent burns far more compute per interaction.
3. **Output-token usage is the most variable SKU** run-to-run (the model varies how much it reasons), so token usage should be reported as a range, not a single number.
4. **Memory generation + session events are consumed even when memories are never read back** — a real SKU footprint for any session-persisted agent.
5. **Search-grounding and image-generation collectors are now in place** (grounding from Cloud Monitoring, images from response events). They measured **0** for these workloads — the agents are capable but the short 2-turn tasks didn't trigger them. Remaining uncaptured SKUs: Cloud Trace, Logging, Storage.

## Method & reproducibility

Per agent: `python scripts/exp_sample.py --package <pkg> --runs 40 --settle 300`. Token usage from model responses (exact); vCPU/GiB-seconds + Memory Bank usage from Cloud Monitoring (per-engine), back-derived to quantities. Per-agent detail in `agent_summaries/`.

_Engines: financial_advisor, academic_research, blogger_agent, marketing_agency (+ memory_assistant)._