# Combined SKU-Usage Report — ADK Agents on Gemini Enterprise Agent Platform

**Purpose:** estimate **usage per SKU** across different agent architectures deployed to Vertex AI Agent Engine. Usage quantities are the primary output; dollar cost is a secondary derived view (usage × catalog list price). This is **not** an expense report or a cost-optimization exercise — it characterizes what each agent *consumes*, by SKU.

Unit = one interaction (2-turn conversation + memory-write; memory_assistant = 3-turn). All gemini-2.5-flash. 3 runs/agent; usage from model responses + Cloud Monitoring (per-engine).

## 1. SKU usage per interaction — model & compute (PRIMARY)

| Agent | Input tokens (range) | Output tokens (range) | Model calls | vCPU-seconds | GiB-seconds |
|---|---|---|---|---|---|
| on-brand-genmedia | 83460 (24021–198338) | 7349 (2732–13376) | 17.2 | 322.7 | 329 |
| financial-advisor | 21679 (13333–34507) | 2410 (1430–2942) | 3.3 | 720.8 | 919 |
| plumber-data-engineering-assistant | 13800 (13475–14578) | 1958 (829–3695) | 4.0 | 104.1 | 127 |
| memory_assistant | 3398 (2552–4001) | 1605 (752–3150) | 5.8 | 39.0 | 560 |
| academic-research | 3367 (2233–5564) | 2699 (1158–5762) | 2.0 | 166.8 | 560 |
| blog-writer | 3027 (2543–3415) | 3039 (2527–3564) | 2.0 | 164.0 | 640 |
| marketing-agency | 2991 (1965–3609) | 1345 (1152–1638) | 2.7 | 164.0 | 640 |
| fomc-research | 1838 (1306–2800) | 479 (188–949) | 2.3 | 30.1 | 55 |
| nexshift-agent | 0 (0–0) | 0 (0–0) | 0.0 | 12.8 | 37 |

## 2. SKU usage per interaction — Agent Platform features (PRIMARY)

| Agent | Session events | Memory-gen tokens | Memories written | Memory retrievals |
|---|---|---|---|---|
| on-brand-genmedia | 31.6 | 4191 | 0.5 | 0.0 |
| financial-advisor | 6.7 | 3177 | 1.3 | 0.0 |
| plumber-data-engineering-assistant | 8.0 | 2853 | 0.6 | 0.0 |
| memory_assistant | 11.5 | 2493 | 3.2 | 2.5 |
| academic-research | 4.0 | 2732 | 0.0 | 0.0 |
| blog-writer | 4.0 | 3959 | 1.0 | 0.0 |
| marketing-agency | 5.3 | 2661 | 0.7 | 0.0 |
| fomc-research | 4.8 | 2358 | 0.0 | 0.0 |
| nexshift-agent | 2.0 | 2390 | 1.0 | 0.0 |

_Memory retrievals are ~0 for the sample agents (no preload_memory tool); memory_assistant retrieves because cross-session recall is its purpose._

## 2b. Grounding & media usage (now collected)

Collectors added for Google Search grounding (Cloud Monitoring) and image generation (response events). **Measured 0 for all agents in these runs** — the agents have the capability but the short 2-turn workloads did not trigger Search or image generation.

| Agent | Web-search grounded requests | Images generated |
|---|---|---|
| on-brand-genmedia | 0 | 27 |
| financial-advisor | 0 | 0 |
| plumber-data-engineering-assistant | 0 | 0 |
| memory_assistant | 0 | 0 |
| academic-research | 0 | 0 |
| blog-writer | 0 | 0 |
| marketing-agency | 0 | 0 |
| fomc-research | 0 | 0 |
| nexshift-agent | 0 | 0 |

_Would bill ~$0.035 per grounded request (Gemini 2.x) and ~$0.04 per image (Imagen) if triggered._

## 3. SKU presence matrix (which agents touch which SKUs)

| Agent | Gemini tokens | Agent Runtime | Sessions | Memory Bank | Search grounding | Image gen |
|---|---|---|---|---|---|---|
| on-brand-genmedia | ✓ | ✓ | ✓ | ✓ (write) | — | **27 images measured (gemini-2.5-flash-image)** |
| financial-advisor | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — |
| plumber-data-engineering-assistant | ✓ | ✓ | ✓ | ✓ (write) | — | — (+BQ/GCS/Dataflow/Dataproc/Dataform by intent) |
| memory_assistant | ✓ | ✓ | ✓ | ✓ (write+read) | — | — |
| academic-research | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — |
| blog-writer | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — |
| marketing-agency | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | capable, 0 measured |
| fomc-research | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — (BigQuery + Cloud Storage intended) |
| nexshift-agent | ✓ | ✓ (CP-SAT compute) | ✓ | ✓ (write) | — | — |

## 4. Secondary: derived cost per interaction (usage × catalog list price)

Reference only — list price, not actual billed. The usage tables above are the deliverable.

| Agent | Gemini $ | Runtime $ | Mem+Sess $ | Total $ (range) | Cost variability |
|---|---|---|---|---|---|
| on-brand-genmedia | 0.0434 | 0.0086 | 0.0015 | 0.0843 (0.0549–0.1254) | Medium |
| financial-advisor | 0.0125 | 0.0196 | 0.0015 | 0.0336 (0.0298–0.0385) | Medium |
| memory_assistant | 0.0050 | 0.0035 | 0.0080 | 0.0165 (0.0144–0.0206) | High |
| blog-writer | 0.0085 | 0.0055 | 0.0015 | 0.0156 (0.0141–0.0170) | Low |
| academic-research | 0.0078 | 0.0054 | 0.0012 | 0.0144 (0.0101–0.0226) | Very high |
| plumber-data-engineering-assistant | 0.0090 | 0.0028 | 0.0009 | 0.0127 (0.0099–0.0172) | Medium |
| marketing-agency | 0.0043 | 0.0055 | 0.0012 | 0.0111 (0.0102–0.0119) | Medium |
| fomc-research | 0.0017 | 0.0009 | 0.0007 | 0.0033 (0.0025–0.0048) | Medium |
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