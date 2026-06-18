# SKU Usage Summary — `financial-advisor` (financial_advisor)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `7070341902448459776`
- **Use case:** Stock analysis & trading-strategy advisor · **Complexity:** High
- **Unit:** 1 interaction = 2-turn conversation + memory-write (3.5 model calls avg), averaged over **80 interactions**. Deployed on Vertex AI Agent Engine (GEAP).
- **Focus:** measured **usage per SKU**; dollar cost is a secondary derived view (§6).

## 1. Architecture

```mermaid
graph TB
    User([User]) --> Coord
    subgraph Engine["Vertex AI Agent Engine — financial_advisor"]
        direction TB
        Coord[financial_coordinator]
        Coord -->|AgentTool| DA[data_analyst]
        Coord -->|AgentTool| TA[trading_analyst]
        Coord -->|AgentTool| EA[execution_analyst]
        Coord -->|AgentTool| RA[risk_analyst]
    end
    subgraph Core["Always-on Agent Platform SKUs"]
        direction LR
        Gemini[("Gemini 2.5 Flash<br/>per-token")]
        Runtime[("Agent Runtime<br/>vCPU + memory-sec")]
        Sess[("Sessions<br/>per event appended")]
        MB[("Memory Bank<br/>per memory + gen tokens")]
    end
    subgraph Extras["Agent-specific SKUs"]
        Search[("Google Search grounding<br/>capable, 0 measured")]
    end
    Engine -.-> Core
    DA -.-> Search
```

`financial_coordinator` (root) delegates to 4 specialist sub-agents wrapped as AgentTools, each its own LlmAgent:
- `data_analyst` — fetches and analyzes market/ticker data
- `trading_analyst` — proposes a trading strategy from the data
- `execution_analyst` — defines an execution plan (timing, sizing)
- `risk_analyst` — assesses risks of the proposed strategy

A single user query fans out to multiple model calls; it is input-heavy (~23k input / ~10k output tokens per interaction, complete token_count) — the heaviest input consumer among the four use-case agents.

**Pattern:** Hierarchical (coordinator + 4 AgentTool specialists)

## 2. SKUs (products) consumed

Gemini tokens (input/output/cached); Agent Runtime (vCPU + memory); Sessions; Memory Bank (generation + writes); Google Search grounding (capable but not triggered).

(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised via add_session_to_memory. Search grounding / Imagen used by the agent but usage not yet metered here — see §7.)

## 3. How usage was measured

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; **80 runs** for variability; 300s Monitoring settle; token usage from Cloud Monitoring **`token_count`** (the complete total — captures AgentTool sub-agent tokens the stream misses; undercount factor **1.4117×** vs `usage_metadata`), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package financial_advisor --runs 80 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 80 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 23206 | 3928–149479 | Very high |
| Gemini output tokens (incl. thinking) | tokens | 9812 | 3888–93198 | Very high |
| Gemini tokens — master/coordinator (input) | tokens | 20770 | — | — |
| Gemini tokens — master/coordinator (output) | tokens | 6404 | — | — |
| Gemini tokens — sub-agents/tools (input) | tokens | 2436 | — | — |
| Gemini tokens — sub-agents/tools (output) | tokens | 3409 | — | — |
| Model calls | calls | 3.5 | — | Medium |
| Agent Runtime — vCPU | vCPU-seconds | 135.6 | — | — |
| Agent Runtime — memory | GiB-seconds | 174.1 | — | — |
| Sessions | events appended | 7.2 | — | Medium |
| Memory Bank — generation | tokens | 3151 | — | — |
| Memory Bank — memories written | memories | 0.9 | — | — |
| Memory Bank — retrievals | reads | 0.6 | — | — |
| Firestore — document writes | writes | 0.03 | — | — |
| Firestore — document reads | reads | 0.95 | — | — |
| Vertex AI Search (RAG) — queries | searches | 0.26 | — | — |
| Google Search grounding — query turns | grounded turns | 0.90 | — | — |


_Master vs sub-agent split: each agent's master/sub token share is measured directly (two-model validation — coordinator on gemini-3.5-flash, sub-agents/tools on gemini-3.1-flash-lite, separated via Cloud Monitoring `token_count` by model). The four input/output × master/sub values reconcile both the master/sub totals and the input/output totals (seeded by the measured per-role in:out ratio — master 88:12, sub 61:39). Single-agent agents are 100% master._

## 5. Grounding & media usage

- **Google Search grounding:** 0.90 grounded query-turns per interaction measured (web_researcher AgentTool invocations; each runs ≥1 native google_search generation). Bills ~$14/1K grounded turns. NOTE: native google_search grounding_metadata is encapsulated inside the AgentTool and the Monitoring web_search_requests metric does not track native ADK google_search — so the AgentTool call count is the measurable unit.
- **Image generation (Imagen):** 0 images measured (from response events). Would bill ~$0.04/image if used.

## 5b. Caveats on usage capture

- vCPU/GiB-seconds are amortized over the measurement window (utilization-dependent).
- Memory storage (stored-memory count over time) is export-only.
- Grounding count is project-wide (no per-engine label); image count is event-based.
- Still uncaptured: Cloud Trace, Logging, Storage.

## 6. Secondary: derived cost (usage × catalog list price)

Provided for reference only. List price, not actual billed; **usage above is the primary output.**

| SKU | $/interaction |
|---|---|
| Gemini tokens | 0.0315 |
| Agent Runtime | 0.0084 |
| Memory Bank + Sessions | 0.0030 |
| Firestore (2w/76r over 80 runs) | 0.0000001 |
| Vertex AI Search (RAG: 0.26 queries/intxn @ $1.50/1K) | 0.000394 |
| Google Search grounding (0.90 grounded turns/intxn @ $14/1K) | 0.012600 |
| Memory Bank retrieval (0.55 memories retrieved/intxn @ $0.5/1K) | 0.000275 |
| Model Armor (derived: 33018 tok scanned @ $0.10/1M) | 0.003302 |
| **Total (measured SKUs)** | **0.0595** (range 0.0223–0.2893) |

## 7. Test workload & sample interactions

**45 interactions** (160 total user turns), fresh user_id per interaction. Interactions cycle **2 distinct conversation scenarios** of varying length (2-turn×40, 16-turn×5) — real-world interactions differ in length and topic, so this spreads coverage rather than repeating one script.

**Scenario 1** (2 turns):

| Turn | User query |
|---|---|
| 1 | I'm a moderate-risk investor. Analyze the outlook for NVDA. |
| 2 | Based on that, suggest a simple trading strategy and key risks. |

**Scenario 2** (16 turns):

| Turn | User query |
|---|---|
| 1 | I'm a moderate-risk investor. Analyze the outlook for NVDA. |
| 2 | Based on that, suggest a simple trading strategy and key risks. |
| 3 | I'm a moderate-risk investor. Analyze the outlook for NVDA. |
| 4 | Based on that, suggest a simple trading strategy and key risks. |
| 5 | I'm a moderate-risk investor. Analyze the outlook for NVDA. |
| 6 | Based on that, suggest a simple trading strategy and key risks. |
| 7 | I'm a moderate-risk investor. Analyze the outlook for NVDA. |
| 8 | Based on that, suggest a simple trading strategy and key risks. |
| 9 | I'm a moderate-risk investor. Analyze the outlook for NVDA. |
| 10 | Based on that, suggest a simple trading strategy and key risks. |
| 11 | I'm a moderate-risk investor. Analyze the outlook for NVDA. |
| 12 | Based on that, suggest a simple trading strategy and key risks. |
| 13 | I'm a moderate-risk investor. Analyze the outlook for NVDA. |
| 14 | Based on that, suggest a simple trading strategy and key risks. |
| 15 | I'm a moderate-risk investor. Analyze the outlook for NVDA. |
| 16 | Based on that, suggest a simple trading strategy and key risks. |

**Sample interaction (first run):**

- **Turn 1** (3717 in / 801 out tokens) — user: *I'm a moderate-risk investor. Analyze the outlook for NVDA.*
  - reply preview: Hello! I'm here to help you navigate the world of financial decision-making. My main goal is to provide you with comprehensive financial advice by guiding you through a step-by-step process. We'll wor…
- **Turn 2** (2386 in / 199 out tokens) — user: *Based on that, suggest a simple trading strategy and key risks.*
  - reply preview: I understand you're eager to get to the strategies and risks! However, to provide you with the most accurate and relevant advice, we need to follow a structured process.  We are currently on the first…

Full transcripts: `data/transcript_financial_advisor.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).