# Combined Cost Estimation Report — ADK Agents on Gemini Enterprise Agent Platform

Estimated **cost per interaction** for 5 agents deployed to Vertex AI Agent Engine. Measured from real usage (model token counts + Cloud Monitoring) and priced at Google's public list rates. **These are list-price estimates of actual measured usage — not the final invoice.** One *interaction* = a 2-turn conversation plus a memory-write (memory_assistant = 3-turn). All run on gemini-2.5-flash.

**How to read variability:** we ran each agent 3 times on the *same* task. **Typical** is the average cost; **Range** is the cheapest-to-most-expensive run. A wide range means cost is hard to predict run-to-run (the model decides how much to "think" each time).

## 1. Cost comparison (per interaction)

| Agent | Complexity | Architecture | Typical cost | Range (low–high) | Predictability |
|---|---|---|---|---|---|
| financial-advisor | High | Hierarchical (coordinator + 4 AgentTool specialists) | **$0.0336** | $0.0298 – $0.0385 | Fairly predictable |
| memory_assistant (EXP-004/5) | High | Hierarchical + Memory Bank | **$0.0165** | $0.0144 – $0.0206 | Variable |
| blog-writer | High | Hierarchical + Sequential (4 sub-agents) + HITL | **$0.0156** | $0.0141 – $0.0170 | Very predictable |
| academic-research | Medium-High | Hierarchical (coordinator + AgentTool sub-agents) | **$0.0144** | $0.0101 – $0.0226 | Highly variable |
| marketing-agency | Medium-High | Hierarchical (coordinator + AgentTool creators) | **$0.0111** | $0.0102 – $0.0119 | Fairly predictable |

- **Cheapest vs priciest agent:** $0.0111 → $0.0336 per interaction — about a **3× difference**, driven by the agent's design.
- **Same agent, run to run:** cost can swing by up to **123%** (e.g. academic-research: $0.0101–$0.0226) on the identical task.
- **Planning guidance:** budget with the **high end of the range**, then multiply by your expected interactions per month.

## 2. Usage per interaction (what drives the cost)

The raw work each agent does per interaction (averaged over 3 runs). Token counts are the main cost driver; input-token ranges show how much this varies run-to-run.

| Agent | Input tokens (range) | Output tokens (range) | Model calls | Session events | Memories written |
|---|---|---|---|---|---|
| financial-advisor | 21679 (13333–34507) | 2410 (1430–2942) | 3.3 | 6.7 | ~1.3 |
| memory_assistant (EXP-004/5) | 3398 (2552–4001) | 1605 (752–3150) | 5.8 | 11.5 | ~3.2 |
| blog-writer | 3027 (2543–3415) | 3039 (2527–3564) | 2.0 | 4.0 | ~1.0 |
| academic-research | 3367 (2233–5564) | 2699 (1158–5762) | 2.0 | 4.0 | ~0.0 |
| marketing-agency | 2991 (1965–3609) | 1345 (1152–1638) | 2.7 | 5.3 | ~0.7 |

**financial-advisor stands out** — it processes 4–10× more input tokens than the others (deep multi-specialist analysis), which is why its compute cost is so high.

## 3. Which products (SKUs) each agent uses

Dollar value = measured cost per interaction for that product. "Used¹" = the agent uses the product but we don't yet meter it (it would add to the total). "—" = not used.

| Agent | Gemini model | Compute (Agent Runtime) | Sessions | Memory Bank | Web Search grounding | Image generation |
|---|---|---|---|---|---|---|
| financial-advisor | $0.0125 | $0.0196 | $0.0015 | $0.0029 | Used¹ | — |
| memory_assistant (EXP-004/5) | $0.0050 | $0.0035 | $0.0029 | $0.0050 | — | — |
| blog-writer | $0.0085 | $0.0055 | $0.0010 | $0.0036 | Used¹ | — |
| academic-research | $0.0078 | $0.0054 | $0.0010 | $0.0025 | Used¹ | — |
| marketing-agency | $0.0043 | $0.0055 | $0.0013 | $0.0024 | Used¹ | Used¹ |

¹ *Web Search grounding bills $14–45 per 1,000 grounded prompts; image generation (Imagen) bills per image. Both are used above but not yet metered here, so real totals run somewhat higher.*

## 4. Detailed SKU breakdown — the two most elaborate agents

### financial-advisor — most expensive, compute-heavy

Coordinator + 4 specialist sub-agents (data, trading, execution, risk). It pulls 17,000–34,000 input tokens per run, so **server compute is the biggest cost, not the AI model**.

| Product | Cost per interaction | Share |
|---|---|---|
| Compute (Agent Runtime) | $0.0196 | 58% |
| Gemini model (tokens) | $0.0125 | 37% |
| Memory Bank + Sessions | $0.0015 | 5% |
| **Total (measured)** | **~$0.0336** | 100% |
| Web Search grounding | not yet metered | would add |

### memory_assistant — most Agent Platform features

Coordinator + 2 sub-agents + long-term Memory Bank. **Memory + session operations are the single biggest slice — larger than the AI model itself.**

| Product | Cost per interaction | Share |
|---|---|---|
| Memory Bank + Sessions | $0.0080 | 48% |
| Gemini model (tokens) | $0.0050 | 30% |
| Compute (Agent Runtime) | $0.0035 | 21% |
| **Total (measured)** | **~$0.0165** | |

## 5. Key takeaways for leadership

1. **A simple agent and a complex one differ ~3× in cost** for the same kind of request — the agent's design (number of specialist sub-agents, depth of analysis) is the main cost lever.
2. **The most expensive agent is dominated by compute, not the AI model** — financial-advisor does heavy multi-step analysis, so server time costs more than the words generated.
3. **Cost is not fixed per request** — the same task can cost up to ~2× more on one run than another because the model varies how much it reasons. Budget for the high end of the range.
4. **The newer Agent Platform features (Memory Bank, Sessions) carry real cost** — for a memory-enabled agent they were the single biggest line item, bigger than the AI model.
5. **A few costs aren't counted yet** (web Search grounding, image generation, logging/tracing), so real bills will run somewhat higher than the figures here.

## Method & reproducibility

Per agent: `python scripts/exp_sample.py --package <pkg> --runs 3 --settle 300`. Token usage from the model response (exact); compute + Memory Bank usage from Cloud Monitoring (per-agent); prices from Google's live Billing Catalog. Per-agent detail in `agent_summaries/`.

_Engines deployed: financial_advisor, academic_research, blogger_agent, marketing_agency (+ memory_assistant). Each accrues idle compute (~$25/mo) until torn down._