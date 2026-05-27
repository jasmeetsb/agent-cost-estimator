# Agent Cost Summary — `marketing-agency` (marketing_agency)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `6855475340148473856`
- **Use case:** End-to-end website/branding launch suite · **Complexity:** Medium-High
- **Cost unit:** 1 interaction = 2-turn conversation + memory generation (2 model calls avg). Deployed on Vertex AI Agent Engine (GEAP).

## 1. Architecture

marketing_coordinator delegates to domain, website, marketing & logo creators; logo creation uses Imagen (genmedia).

**Pattern:** Hierarchical (coordinator + AgentTool creators)

## 2. Components / SKUs used

Gemini tokens, Agent Runtime, Sessions, Memory Bank, Imagen (genmedia), Google Search grounding

(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised via add_session_to_memory. Search grounding used by the agent but not yet metered here — see caveats.)

## 3. How the experiment was run

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; 3 runs for variability; 300s Monitoring settle; actual runtime + memory_bank usage pulled from Cloud Monitoring and priced at catalog list rate.
Reproduce: `python scripts/exp_sample.py --package marketing_agency --runs 3 --settle 300`

## 4. Typical usage & variance (3 runs)

| Metric | mean | min–max | CV% |
|---|---|---|---|
| input tokens | 2991 | 1965–3609 | 24.4% |
| output tokens | 1345 | 1152–1638 | 15.7% |
| model calls | 2.7 | 2–3 | 17.7% |
| model cost ($) | 0.0043 | 0.0035–0.0052 | 16.5% |

## 5. Cost per interaction, by SKU (catalog list price)

| SKU | per-run $ | note |
|---|---|---|
| Conversation tokens | 0.0043 | input+output |
| Agent Runtime (vCPU+mem) | 0.0055 | amortized; utilization-dependent |
| Memory generation tokens | 0.0024 | 7982 tok @ input rate |
| Session events | 0.0013 | ~5 events |
| **Total per interaction** | **0.0111** | excl. Search grounding + Trace/Logging |

## 6. Caveats

- Catalog **list price**, not actual billed (internal project; true $ needs BigQuery export).
- **Google Search grounding** is used by this agent but NOT yet metered (per-grounded-prompt SKU); add via Monitoring web_search metrics or export.
- Memory *retrieval* = 0 (agent has no preload_memory tool); only memory *generation* is exercised.
- Runtime cost is utilization-dependent; idle memory allocation dominates at low QPS.
- Cloud Trace (enable_tracing), Logging, Storage, and (marketing) Imagen not captured.