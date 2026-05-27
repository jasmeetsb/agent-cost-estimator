# Agent Cost Summary — `financial-advisor` (financial_advisor)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `343270278970736640`
- **Use case:** Stock analysis & trading strategy advisor · **Complexity:** High
- **Cost unit:** 1 interaction = 2-turn conversation + memory generation (3 model calls avg). Deployed on Vertex AI Agent Engine (GEAP).

## 1. Architecture

financial_coordinator delegates to data_analyst, trading_analyst, execution_analyst, risk_analyst (each wrapped as an AgentTool).

**Pattern:** Hierarchical (coordinator + 4 AgentTool specialists)

## 2. Components / SKUs used

Gemini tokens, Agent Runtime (vCPU/mem), Sessions, Memory Bank, Google Search grounding

(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised via add_session_to_memory. Search grounding used by the agent but not yet metered here — see caveats.)

## 3. How the experiment was run

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; 3 runs for variability; 300s Monitoring settle; actual runtime + memory_bank usage pulled from Cloud Monitoring and priced at catalog list rate.
Reproduce: `python scripts/exp_sample.py --package financial_advisor --runs 3 --settle 300`

## 4. Typical usage & variability (3 runs)

Each row shows the **typical (average)** value, the **range** seen across runs (low to high), and how **variable** that is run-to-run (Low / Medium / High / Very high). Same task each run — differences come mostly from how much the model 'thinks'.

| Metric | Typical (avg) | Range (low–high) | Variability |
|---|---|---|---|
| Input tokens | 21679 | 13333–34507 | High |
| Output tokens | 2410 | 1430–2942 | Medium |
| Model calls | 3.3 | 3–4 | Low |
| Model cost ($) | 0.0125 | 0.0087–0.0175 | Medium |

## 5. Cost per interaction, by SKU (catalog list price)

| SKU | per-run $ | note |
|---|---|---|
| Conversation tokens | 0.0125 | input+output |
| Agent Runtime (vCPU+mem) | 0.0196 | amortized; utilization-dependent |
| Memory generation tokens | 0.0029 | 9531 tok @ input rate |
| Session events | 0.0015 | ~6 events |
| **Total per interaction** | **0.0336** | excl. Search grounding + Trace/Logging |

## 6. Caveats

- Catalog **list price**, not actual billed (internal project; true $ needs BigQuery export).
- **Google Search grounding** is used by this agent but NOT yet metered (per-grounded-prompt SKU); add via Monitoring web_search metrics or export.
- Memory *retrieval* = 0 (agent has no preload_memory tool); only memory *generation* is exercised.
- Runtime cost is utilization-dependent; idle memory allocation dominates at low QPS.
- Cloud Trace (enable_tracing), Logging, Storage, and (marketing) Imagen not captured.