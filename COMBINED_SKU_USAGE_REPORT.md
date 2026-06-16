# Combined SKU-Usage Report — ADK Agents on Gemini Enterprise Agent Platform

**Purpose:** estimate **usage per SKU** across different agent architectures deployed to Vertex AI Agent Engine. Usage quantities are the primary output; dollar cost is a secondary derived view (usage × catalog list price). This is **not** an expense report or a cost-optimization exercise — it characterizes what each agent *consumes*, by SKU.

Unit = one interaction (2-turn conversation + memory-write; memory_assistant = 3-turn). All gemini-2.5-flash. 3 runs/agent; usage from model responses + Cloud Monitoring (per-engine).

## 1. SKU usage per interaction — model & compute (PRIMARY)

| Agent | Input tokens (range) | Output tokens (range) | Model calls | vCPU-seconds | GiB-seconds |
|---|---|---|---|---|---|
| on-brand-genmedia | 83460 (24021–198338) | 7349 (2732–13376) | 17.2 | 322.7 | 329 |
| multi-agent-orchestrator (archetype) | 22783 (8224–75848) | 4320 (1576–9662) | 13.1 | 180.1 | 234 |
| financial-advisor | 21786 (7979–81100) | 2753 (1072–12463) | 3.5 | 543.0 | 590 |
| workflow-operator (archetype) | 21467 (4416–74345) | 1489 (583–3333) | 15.5 | 129.9 | 192 |
| plumber-data-engineering-assistant | 13800 (13475–14578) | 1958 (829–3695) | 4.0 | 104.1 | 127 |
| autonomous-researcher (archetype) | 7853 (1577–32145) | 2436 (557–11690) | 5.0 | 91.4 | 153 |
| conversational-chatbot (archetype) | 6232 (2505–17874) | 665 (195–1860) | 7.5 | 73.4 | 132 |
| marketing-agency | 3914 (1816–9947) | 3487 (846–63892) | 3.0 | 204.0 | 254 |
| memory_assistant | 3398 (2552–4001) | 1605 (752–3150) | 5.8 | 39.0 | 560 |
| blog-writer | 2856 (1803–3618) | 2538 (733–4087) | 2.0 | 118.5 | 178 |
| academic-research | 2577 (1813–14570) | 1384 (423–6130) | 2.1 | 86.9 | 137 |
| fomc-research | 1838 (1306–2800) | 479 (188–949) | 2.3 | 30.1 | 55 |
| nexshift-agent | 0 (0–0) | 0 (0–0) | 0.0 | 12.8 | 37 |

## 2. SKU usage per interaction — Agent Platform features (PRIMARY)

| Agent | Session events | Memory-gen tokens | Memories written | Memory retrievals |
|---|---|---|---|---|
| on-brand-genmedia | 31.6 | 4191 | 0.5 | 0.0 |
| multi-agent-orchestrator (archetype) | 26.2 | 0 | 0.0 | 0.0 |
| financial-advisor | 7.1 | 3087 | 0.9 | 0.0 |
| workflow-operator (archetype) | 31.1 | 0 | 0.0 | 0.0 |
| plumber-data-engineering-assistant | 8.0 | 2853 | 0.6 | 0.0 |
| autonomous-researcher (archetype) | 12.4 | 0 | 0.0 | 0.0 |
| conversational-chatbot (archetype) | 15.1 | 0 | 0.0 | 0.0 |
| marketing-agency | 6.0 | 2671 | 0.5 | 0.0 |
| memory_assistant | 11.5 | 2493 | 3.2 | 2.5 |
| blog-writer | 4.0 | 3540 | 0.4 | 0.0 |
| academic-research | 4.1 | 2627 | 0.1 | 0.0 |
| fomc-research | 4.8 | 2358 | 0.0 | 0.0 |
| nexshift-agent | 2.0 | 2390 | 1.0 | 0.0 |

_Memory retrievals are ~0 for the sample agents (no preload_memory tool); memory_assistant retrieves because cross-session recall is its purpose._

## 2b. Grounding & media usage (now collected)

Collectors added for Google Search grounding (Cloud Monitoring) and image generation (response events). **Measured 0 for all agents in these runs** — the agents have the capability but the short 2-turn workloads did not trigger Search or image generation.

| Agent | Web-search grounded requests | Images generated |
|---|---|---|
| on-brand-genmedia | 0 | 27 |
| multi-agent-orchestrator (archetype) | 0 | 0 |
| financial-advisor | 0 | 0 |
| workflow-operator (archetype) | 0 | 0 |
| plumber-data-engineering-assistant | 0 | 0 |
| autonomous-researcher (archetype) | 0 | 0 |
| conversational-chatbot (archetype) | 0 | 0 |
| marketing-agency | 0 | 0 |
| memory_assistant | 0 | 0 |
| blog-writer | 0 | 0 |
| academic-research | 0 | 0 |
| fomc-research | 0 | 0 |
| nexshift-agent | 0 | 0 |

_Would bill ~$0.035 per grounded request (Gemini 2.x) and ~$0.04 per image (Imagen) if triggered._

## 2c. State & retrieval usage — Firestore + Vertex AI Search/RAG (PRIMARY)

Per-interaction quantities for the archetype agents (Firestore document ops via ADK note tools; RAG queries via VertexAiSearchTool against the synthetic corpus). Measured from the event stream / transcript.

| Agent | Firestore writes | Firestore reads | Vertex AI Search (RAG) queries |
|---|---|---|---|
| multi-agent-orchestrator (archetype) | 0.15 | 0.35 | 0.45 |
| workflow-operator (archetype) | 1.48 | 1.10 | 0.00 |
| autonomous-researcher (archetype) | 0.12 | 1.57 | 1.32 |
| conversational-chatbot (archetype) | 0.03 | 0.00 | 2.20 |

_RAG priced at $1.50/1K queries, Firestore at catalog read/write rates (GE AP calculator). Usage counts are the deliverable; cost is the secondary view in §4._

## 3. SKU presence matrix (which agents touch which SKUs)

| Agent | Gemini tokens | Agent Runtime | Sessions | Memory Bank | Search grounding | Image gen |
|---|---|---|---|---|---|---|
| on-brand-genmedia | ✓ | ✓ | ✓ | ✓ (write) | — | **27 images measured (gemini-2.5-flash-image)** |
| financial-advisor | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — |
| plumber-data-engineering-assistant | ✓ | ✓ | ✓ | ✓ (write) | — | — (+BQ/GCS/Dataflow/Dataproc/Dataform by intent) |
| marketing-agency | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | capable, 0 measured |
| memory_assistant | ✓ | ✓ | ✓ | ✓ (write+read) | — | — |
| blog-writer | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — |
| academic-research | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — |
| fomc-research | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — (BigQuery + Cloud Storage intended) |
| nexshift-agent | ✓ | ✓ (CP-SAT compute) | ✓ | ✓ (write) | — | — |

## 4. Secondary: derived cost per interaction (usage × catalog list price)

Reference only — list price, not actual billed. The usage tables above are the deliverable.

| Agent | Gemini $ | Runtime $ | Mem+Sess $ | Total $ (range) | Cost variability |
|---|---|---|---|---|---|
| on-brand-genmedia | 0.0434 | 0.0086 | 0.0015 | 0.0934 (0.0549–0.1254) | Medium |
| multi-agent-orchestrator (archetype) | 0.0176 | 0.0049 | 0.0066 | 0.0324 (0.0189–0.0584) | High |
| financial-advisor | 0.0134 | 0.0145 | 0.0010 | 0.0313 (0.0215–0.0710) | High |
| workflow-operator (archetype) | 0.0102 | 0.0036 | 0.0078 | 0.0239 (0.0145–0.0419) | High |
| autonomous-researcher (archetype) | 0.0084 | 0.0026 | 0.0031 | 0.0171 (0.0077–0.0445) | Very high |
| marketing-agency | 0.0099 | 0.0055 | 0.0008 | 0.0170 (0.0090–0.1671) | Very high |
| memory_assistant | 0.0050 | 0.0035 | 0.0080 | 0.0165 (0.0144–0.0206) | High |
| plumber-data-engineering-assistant | 0.0090 | 0.0028 | 0.0009 | 0.0143 (0.0099–0.0172) | Medium |
| conversational-chatbot (archetype) | 0.0035 | 0.0021 | 0.0038 | 0.0133 (0.0072–0.0155) | High |
| blog-writer | 0.0072 | 0.0033 | 0.0011 | 0.0121 (0.0068–0.0156) | Medium |
| academic-research | 0.0042 | 0.0024 | 0.0008 | 0.0078 (0.0049–0.0203) | Very high |
| fomc-research | 0.0017 | 0.0009 | 0.0007 | 0.0035 (0.0025–0.0048) | Medium |
| nexshift-agent | 0.0000 | 0.0004 | 0.0007 | 0.0011 (0.0011–0.0011) | Low |

## 5. Usage-pattern observations

1. **Input-token usage is the biggest differentiator** — financial-advisor consumes ~83460 input tokens/interaction vs ~0 for the lightest, a 83460× spread driven by depth of multi-specialist analysis.
2. **vCPU-seconds track analysis depth**, not just call count — the heaviest agent burns far more compute per interaction.
3. **Output-token usage is the most variable SKU** run-to-run (the model varies how much it reasons), so token usage should be reported as a range, not a single number.
4. **Memory generation + session events are consumed even when memories are never read back** — a real SKU footprint for any session-persisted agent.
5. **Search-grounding and image-generation collectors are now in place** (grounding from Cloud Monitoring, images from response events). They measured **0** for these workloads — the agents are capable but the short 2-turn tasks didn't trigger them. Remaining uncaptured SKUs: Cloud Trace, Logging, Storage.

## Method & reproducibility

Per agent: `python scripts/exp_sample.py --package <pkg> --runs 3 --settle 300`. Token usage from model responses (exact); vCPU/GiB-seconds + Memory Bank usage from Cloud Monitoring (per-engine), back-derived to quantities. Per-agent detail in `agent_summaries/`.

_Engines: financial_advisor, academic_research, blogger_agent, marketing_agency (+ memory_assistant)._