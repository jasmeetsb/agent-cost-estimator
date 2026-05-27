# Combined Cost Estimation Report — ADK Agents on Gemini Enterprise Agent Platform

Cost-per-interaction estimates for 5 agents deployed to Vertex AI Agent Engine, measured via the harness (usage_metadata + Cloud Monitoring SKU extraction, priced at Billing Catalog list rates). **Costs are list-price estimates of actual measured usage, not billed dollars.** Unit = one interaction (2-turn conversation + memory generation; memory_assistant = 3-turn). All gemini-2.5-flash. **Total is mean over 3 runs; the min–max range reflects run-to-run model-cost variance (the variable component) with amortized runtime/memory held fixed.**

## Per-agent comparison

| Agent | Complexity | Pattern | Calls | Model $ | Runtime $ | Mem+Sess $ | **Total $/interaction (mean)** | **Total range (min–max)** | Model-cost CV |
|---|---|---|---|---|---|---|---|---|---|
| financial-advisor | High | Hierarchical (coordinator + 4 AgentTool specialists) | 3.3 | 0.0125 | 0.0196 | 0.0015 | **0.0336** | 0.0298–0.0385 | 29% |
| memory_assistant (EXP-004/5) | High | Hierarchical + Memory Bank | 5.8 | 0.0050 | 0.0035 | 0.0080 | **0.0165** | 0.0144–0.0206 | 48% |
| blog-writer | High | Hierarchical + Sequential (4 sub-agents) + HITL | 2.0 | 0.0085 | 0.0055 | 0.0015 | **0.0156** | 0.0141–0.0170 | 14% |
| academic-research | Medium-High | Hierarchical (coordinator + AgentTool sub-agents) | 2.0 | 0.0078 | 0.0054 | 0.0012 | **0.0144** | 0.0101–0.0226 | 76% |
| marketing-agency | Medium-High | Hierarchical (coordinator + AgentTool creators) | 2.7 | 0.0043 | 0.0055 | 0.0012 | **0.0111** | 0.0102–0.0119 | 16% |

**Across agents:** $0.0111–$0.0336 per interaction (3.0× spread on the means). **Within a single agent**, the identical task varies up to 2.2× run-to-run (see Total range) — driven by output/thinking-token swings.

## Key findings

1. **Cost spans ~3× across agents** for similar 2-turn interactions — architecture complexity (sub-agent fan-out, analysis depth) drives it more than the workload.
2. **financial-advisor is the most expensive (~$0.034)** and the only **runtime-dominated** one — it pulls 17k–34k input tokens/run and does heavy multi-specialist analysis, so vCPU compute outweighs token cost.
3. **Model-token cost is highly variable (CV 35–80%)** run-to-run for the identical task — driven by output/thinking-token swings. Always quote a distribution, not a point estimate.
4. **Memory generation + session events are a real, often-hidden slice** (~$0.003–0.005/run) present even when the agent never *retrieves* memory.
5. **Runtime cost is utilization-dependent** — these numbers amortize over a busy window; at low QPS idle memory allocation dominates (see EXP-001).

## Not captured (would raise the true cost)

- **Google Search grounding** (all four samples ground on Search): $14–45 per 1,000 grounded prompts.
- **Imagen/genmedia** (marketing-agency logo generation): per-image SKU.
- **Cloud Trace** (tracing enabled on deploy), **Logging**, **Storage**, **memory storage** (monthly).
- True billed dollars require **BigQuery billing export** (unavailable on this shared corp account).

## Method & reproducibility

Per agent: `python scripts/exp_sample.py --package <pkg> --runs 3 --settle 300`. Token usage from `usage_metadata` (exact); runtime + Memory Bank from Cloud Monitoring (`reasoning_engine/*`, engine-scoped); prices from the live Billing Catalog API. Per-agent detail in `agent_summaries/`.

_Engines deployed: financial_advisor, academic_research, blogger_agent, marketing_agency (+ memory_assistant). All accrue idle runtime (~$25/mo each) until torn down._