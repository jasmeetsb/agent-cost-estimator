# Agent Cost Summary — `blog-writer` (blogger_agent)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `3729977198753349632`
- **Use case:** Multi-agent technical blog authoring · **Complexity:** High
- **Cost unit:** 1 interaction = 2-turn conversation + memory generation (2 model calls avg). Deployed on Vertex AI Agent Engine (GEAP).

## 1. Architecture

interactive_blogger_agent orchestrates 4 sub-agents (outline, draft, edit, social) + tools; human-in-the-loop refinement.

**Pattern:** Hierarchical + Sequential (4 sub-agents) + HITL

## 2. Components / SKUs used

Gemini tokens, Agent Runtime, Sessions, Memory Bank, Google Search grounding

(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised via add_session_to_memory. Search grounding used by the agent but not yet metered here — see caveats.)

## 3. How the experiment was run

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; 3 runs for variability; 300s Monitoring settle; actual runtime + memory_bank usage pulled from Cloud Monitoring and priced at catalog list rate.
Reproduce: `python scripts/exp_sample.py --package blogger_agent --runs 3 --settle 300`

## 4. Typical usage & variance (3 runs)

| Metric | mean | min–max | CV% |
|---|---|---|---|
| input tokens | 3027 | 2543–3415 | 12.0% |
| output tokens | 3039 | 2527–3564 | 13.9% |
| model calls | 2.0 | 2–2 | 0.0% |
| model cost ($) | 0.0085 | 0.0071–0.0099 | 13.7% |

## 5. Cost per interaction, by SKU (catalog list price)

| SKU | per-run $ | note |
|---|---|---|
| Conversation tokens | 0.0085 | input+output |
| Agent Runtime (vCPU+mem) | 0.0055 | amortized; utilization-dependent |
| Memory generation tokens | 0.0036 | 11878 tok @ input rate |
| Session events | 0.0010 | ~4 events |
| **Total per interaction** | **0.0156** | excl. Search grounding + Trace/Logging |

## 6. Caveats

- Catalog **list price**, not actual billed (internal project; true $ needs BigQuery export).
- **Google Search grounding** is used by this agent but NOT yet metered (per-grounded-prompt SKU); add via Monitoring web_search metrics or export.
- Memory *retrieval* = 0 (agent has no preload_memory tool); only memory *generation* is exercised.
- Runtime cost is utilization-dependent; idle memory allocation dominates at low QPS.
- Cloud Trace (enable_tracing), Logging, Storage, and (marketing) Imagen not captured.