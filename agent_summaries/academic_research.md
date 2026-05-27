# Agent Cost Summary — `academic-research` (academic_research)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `4540625131680038912`
- **Use case:** Academic literature analysis & discovery · **Complexity:** Medium-High
- **Cost unit:** 1 interaction = 2-turn conversation + memory generation (2 model calls avg). Deployed on Vertex AI Agent Engine (GEAP).

## 1. Architecture

academic_coordinator routes to websearch + new-research specialists.

**Pattern:** Hierarchical (coordinator + AgentTool sub-agents)

## 2. Components / SKUs used

Gemini tokens, Agent Runtime, Sessions, Memory Bank, Google Search grounding

(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised via add_session_to_memory. Search grounding used by the agent but not yet metered here — see caveats.)

## 3. How the experiment was run

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; 3 runs for variability; 300s Monitoring settle; actual runtime + memory_bank usage pulled from Cloud Monitoring and priced at catalog list rate.
Reproduce: `python scripts/exp_sample.py --package academic_research --runs 3 --settle 300`

## 4. Typical usage & variability (3 runs)

Each row shows the **typical (average)** value, the **range** seen across runs (low to high), and how **variable** that is run-to-run (Low / Medium / High / Very high). Same task each run — differences come mostly from how much the model 'thinks'.

| Metric | Typical (avg) | Range (low–high) | Variability |
|---|---|---|---|
| Input tokens | 3367 | 2233–5564 | High |
| Output tokens | 2699 | 1158–5762 | Very high |
| Model calls | 2.0 | 2–2 | Low |
| Model cost ($) | 0.0078 | 0.0036–0.0161 | Very high |

## 5. Cost per interaction, by SKU (catalog list price)

| SKU | per-run $ | note |
|---|---|---|
| Conversation tokens | 0.0078 | input+output |
| Agent Runtime (vCPU+mem) | 0.0054 | amortized; utilization-dependent |
| Memory generation tokens | 0.0025 | 8197 tok @ input rate |
| Session events | 0.0010 | ~4 events |
| **Total per interaction** | **0.0144** | excl. Search grounding + Trace/Logging |

## 6. Caveats

- Catalog **list price**, not actual billed (internal project; true $ needs BigQuery export).
- **Google Search grounding** is used by this agent but NOT yet metered (per-grounded-prompt SKU); add via Monitoring web_search metrics or export.
- Memory *retrieval* = 0 (agent has no preload_memory tool); only memory *generation* is exercised.
- Runtime cost is utilization-dependent; idle memory allocation dominates at low QPS.
- Cloud Trace (enable_tracing), Logging, Storage, and (marketing) Imagen not captured.