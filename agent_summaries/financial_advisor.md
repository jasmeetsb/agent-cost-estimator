# SKU Usage Summary — `financial-advisor` (financial_advisor)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `7070341902448459776`
- **Use case:** Stock analysis & trading-strategy advisor · **Complexity:** High
- **Unit:** 1 interaction = a 2-turn conversation in a single session, followed by a memory-write step (3.5 model calls on average). All numbers below are averaged over **80 interactions**. Deployed on Vertex AI Agent Engine.
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

A single user query fans out to multiple model calls, and the agent is input-heavy (~23k input / ~10k output tokens per interaction): each specialist sub-agent re-ingests the analysis context, so input tokens dominate.

**Pattern:** Hierarchical (coordinator + 4 AgentTool specialists)

## 2. SKUs (products) consumed

Gemini tokens (input/output/cached); Agent Runtime (vCPU + memory); Sessions; Memory Bank (generation + writes); Google Search grounding (capable but not triggered).

(Sessions and Agent Runtime are billed automatically by Agent Engine; Memory Bank generation is triggered by `add_session_to_memory`. Where the agent uses Google Search grounding or image generation, that usage is reported in §5.)

## 3. How usage was measured

Each interaction = a 2-turn conversation in one session, followed by `add_session_to_memory` (which triggers Memory Bank generation). We ran **80 interactions** to capture run-to-run variability, waited 300s for Cloud Monitoring metrics to settle, then read usage: token counts come from Cloud Monitoring **`token_count`** — the **complete** total. This agent delegates to sub-agents invoked as callable tools (ADK `AgentTool`), and those sub-agent model calls do not appear in the parent agent's response stream, so a stream-based count undercounts this agent by **1.4117×**; `token_count` captures every model call and corrects it; runtime (vCPU / memory-seconds) and Memory Bank usage come from Cloud Monitoring (per-engine metrics).

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (averaged over 80 interactions), with the min–max range and variability label across interactions.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 23206 | 3928–149479 | Very high |
| Gemini output tokens (incl. thinking) | tokens | 9812 | 3888–93198 | Very high |
| Gemini tokens — coordinator agent (input) | tokens | 20770 | — | — |
| Gemini tokens — coordinator agent (output) | tokens | 6404 | — | — |
| Gemini tokens — sub-agents (input) | tokens | 2436 | — | — |
| Gemini tokens — sub-agents (output) | tokens | 3409 | — | — |
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
| Google Search grounding | grounded query-turns | 0.90 | — | — |


_**Coordinator vs sub-agent token split** — the share of total Gemini tokens processed by the root coordinator agent versus the sub-agents it delegates to. Measured directly by running the coordinator and the sub-agents on two different model versions (coordinator on gemini-3.5-flash, sub-agents on gemini-3.1-flash-lite) and separating their token counts by model in Cloud Monitoring — this is the **master/sub** split in the two-model measurement. The input-vs-output breakdown within each role is allocated by the measured per-role input:output ratio (coordinator ≈ 88:12, sub-agents ≈ 61:39). Single-agent agents have no sub-agents, so they are 100% coordinator._

## 5. Grounding & media usage

- **Google Search grounding:** 0.90 grounded query-turns per interaction. Grounding runs inside a dedicated web-research sub-agent that the coordinator invokes as a tool (ADK `AgentTool`); each call issues one or more native `google_search` requests and returns grounded results. We count each web-research call as one grounded query-turn — the billable unit (~$14 / 1K grounded query-turns). Native `google_search` grounding is encapsulated inside the AgentTool and is not tracked by Cloud Monitoring's `web_search_requests` metric, so the AgentTool call count is the reliable measure.
- **Image generation (Imagen):** none in this workload. (Would bill ~$0.04 / image if used.)

## 5b. Caveats on usage capture

- **Agent Runtime (vCPU / GiB-seconds)** is the engine's allocated compute amortized over the measurement window, so it depends on utilization (queries per hour). Treat it as an upper bound, not actual billed instance-time.
- **Memory storage** (the number of stored memories accruing over time) is not captured here — it is only available from the billing export.
- **Grounding** is counted from the agent's tool calls (Cloud Monitoring's grounding metric is project-wide, with no per-engine label); **Imagen** image counts come from response events.
- **Not yet captured:** Cloud Trace, Cloud Logging, Cloud Storage.

## 6. Secondary: derived cost (usage × catalog list price)

Provided for reference only. List price, not actual billed; **usage above is the primary output.**

| SKU | $/interaction |
|---|---|
| Gemini tokens | 0.0315 |
| Agent Runtime | 0.0084 |
| Memory Bank + Sessions | 0.0030 |
| Firestore (2 writes / 76 reads over 80 interactions) | 0.0000001 |
| Vertex AI Search (RAG: 0.26 queries/interaction @ $1.50/1K) | 0.000394 |
| Google Search grounding (0.90 grounded query-turns/interaction @ $14/1K) | 0.012600 |
| Memory Bank retrieval (0.55 memories retrieved/interaction @ $0.5/1K) | 0.000275 |
| Model Armor (derived: 33018 tok scanned @ $0.10/1M) | 0.003302 |
| **Total (measured SKUs)** | **0.0595** (range 0.0223–0.2893) |

## 7. Test workload & sample interactions

Each interaction used a fresh user id. The workload draws from **1 distinct conversation scenarios** of varying length (2–16 turns); real-world conversations differ in length and topic, so cycling several scenarios spreads coverage rather than repeating a single script. Longer interactions repeat these same base scenarios to exercise multi-turn cost scaling.

**Scenario 1** (2 turns):

| Turn | User query |
|---|---|
| 1 | I'm a moderate-risk investor. Analyze the outlook for NVDA. |
| 2 | Based on that, suggest a simple trading strategy and key risks. |

**Sample interaction (first run):**

- **Turn 1** (3717 in / 801 out tokens) — user: *I'm a moderate-risk investor. Analyze the outlook for NVDA.*
  - reply preview: Hello! I'm here to help you navigate the world of financial decision-making. My main goal is to provide you with comprehensive financial advice by guiding you through a step-by-step process. We'll wor…
- **Turn 2** (2386 in / 199 out tokens) — user: *Based on that, suggest a simple trading strategy and key risks.*
  - reply preview: I understand you're eager to get to the strategies and risks! However, to provide you with the most accurate and relevant advice, we need to follow a structured process.  We are currently on the first…

Full transcripts: `data/transcript_financial_advisor.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).