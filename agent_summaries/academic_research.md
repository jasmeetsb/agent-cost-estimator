# SKU Usage Summary — `academic-research` (academic_research)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `4269102934224011264`
- **Use case:** Academic literature analysis & discovery · **Complexity:** Medium-High
- **Unit:** 1 interaction = a 2-turn conversation in a single session, followed by a memory-write step (3.0 model calls on average). All numbers below are averaged over **80 interactions**. Deployed on Vertex AI Agent Engine.
- **Focus:** measured **usage per SKU**; dollar cost is a secondary derived view (§6).

## 1. Architecture

```mermaid
graph TB
    User([User]) --> Coord
    subgraph Engine["Vertex AI Agent Engine — academic_research"]
        direction TB
        Coord[academic_coordinator]
        Coord -->|AgentTool| WS[academic_websearch]
        Coord -->|AgentTool| NR[academic_newresearch]
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
    WS -.-> Search
```

`academic_coordinator` (root) routes between 2 specialist AgentTools:
- `academic_websearch_agent` — searches the web for relevant papers
- `academic_newresearch_agent` — proposes new research directions from findings

Sequential flow: search → analyze → synthesize. Lightweight architecture; cost variability is high (model decides how much to reason).

**Pattern:** Hierarchical (coordinator + AgentTool sub-agents)

## 2. SKUs (products) consumed

Gemini tokens; Agent Runtime (vCPU + memory); Sessions; Memory Bank; Google Search grounding (capable but not triggered in our workloads).

(Sessions and Agent Runtime are billed automatically by Agent Engine; Memory Bank generation is triggered by `add_session_to_memory`. Where the agent uses Google Search grounding or image generation, that usage is reported in §5.)

## 3. How usage was measured

Each interaction = a 2-turn conversation in one session, followed by `add_session_to_memory` (which triggers Memory Bank generation). We ran **80 interactions** to capture run-to-run variability, waited 300s for Cloud Monitoring metrics to settle, then read usage: token counts come from Cloud Monitoring **`token_count`** — the **complete** total. This agent delegates to sub-agents invoked as callable tools (ADK `AgentTool`), and those sub-agent model calls do not appear in the parent agent's response stream, so a stream-based count undercounts this agent by **1.0×**; `token_count` captures every model call and corrects it; runtime (vCPU / memory-seconds) and Memory Bank usage come from Cloud Monitoring (per-engine metrics).

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (averaged over 80 interactions), with the min–max range and variability label across interactions.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 4507 | 2631–9301 | Medium |
| Gemini output tokens (incl. thinking) | tokens | 1120 | 399–3734 | High |
| Gemini tokens — coordinator agent (input) | tokens | 3694 | — | — |
| Gemini tokens — coordinator agent (output) | tokens | 560 | — | — |
| Gemini tokens — sub-agents (input) | tokens | 813 | — | — |
| Gemini tokens — sub-agents (output) | tokens | 560 | — | — |
| Model calls | calls | 3.0 | — | Medium |
| Agent Runtime — vCPU | vCPU-seconds | 66.5 | — | — |
| Agent Runtime — memory | GiB-seconds | 85.2 | — | — |
| Sessions | events appended | 6.0 | — | Medium |
| Memory Bank — generation | tokens | 2480 | — | — |
| Memory Bank — memories written | memories | 0.0 | — | — |
| Memory Bank — retrievals | reads | 0.0 | — | — |
| Firestore — document writes | writes | 0.04 | — | — |
| Firestore — document reads | reads | 0.56 | — | — |
| Vertex AI Search (RAG) — queries | searches | 0.34 | — | — |
| Google Search grounding | grounded query-turns | 0.70 | — | — |

_Memory retrievals = 0 for this workload. `load_memory` returns memories only when (a) the agent invokes it and (b) earlier sessions generated **user-centric** memories worth recalling. Here it is 0 — the agent has no retrieval tool, or doesn't call it (support-FAQ chatbot answers directly), or calls it but its sessions produce no user-centric memories to retrieve (e.g., academic-research: topic Q&A, not facts about the user). The retrieval SKU IS exercised by financial-advisor, marketing-agency, blog-writer, workflow-operator, autonomous-researcher, and multi-agent-orchestrator (returning-user runs) + `memory_assistant`._

_**Coordinator vs sub-agent token split** — the share of total Gemini tokens processed by the root coordinator agent versus the sub-agents it delegates to. Measured directly by running the coordinator and the sub-agents on two different model versions (coordinator on gemini-3.5-flash, sub-agents on gemini-3.1-flash-lite) and separating their token counts by model in Cloud Monitoring — this is the **master/sub** split in the two-model measurement. The input-vs-output breakdown within each role is allocated by the measured per-role input:output ratio (coordinator ≈ 88:12, sub-agents ≈ 61:39). Single-agent agents have no sub-agents, so they are 100% coordinator._

## 5. Grounding & media usage

- **Google Search grounding:** 0.70 grounded query-turns per interaction. Grounding runs inside a dedicated web-research sub-agent that the coordinator invokes as a tool (ADK `AgentTool`); each call issues one or more native `google_search` requests and returns grounded results. We count each web-research call as one grounded query-turn — the billable unit (~$14 / 1K grounded query-turns). Native `google_search` grounding is encapsulated inside the AgentTool and is not tracked by Cloud Monitoring's `web_search_requests` metric, so the AgentTool call count is the reliable measure.
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
| Gemini tokens | 0.0042 |
| Agent Runtime | 0.0028 |
| Memory Bank + Sessions | 0.0023 |
| Firestore (3 writes / 45 reads over 80 interactions) | 0.0000000 |
| Vertex AI Search (RAG: 0.34 queries/interaction @ $1.50/1K) | 0.000506 |
| Google Search grounding (0.70 grounded query-turns/interaction @ $14/1K) | 0.009800 |
| Model Armor (derived: 5627 tok scanned @ $0.10/1M) | 0.000563 |
| **Total (measured SKUs)** | **0.0201** (range 0.0069–0.0172) |

## 7. Test workload & sample interactions

Each interaction used a fresh user id. The workload draws from **1 distinct conversation scenarios** of varying length (2–16 turns); real-world conversations differ in length and topic, so cycling several scenarios spreads coverage rather than repeating a single script. Longer interactions repeat these same base scenarios to exercise multi-turn cost scaling.

**Scenario 1** (2 turns):

| Turn | User query |
|---|---|
| 1 | Summarize recent research directions in efficient transformer architectures. |
| 2 | Which of those directions looks most promising for edge deployment, and why? |

**Sample interaction (first run):**

- **Turn 1** (2338 in / 278 out tokens) — user: *Summarize recent research directions in efficient transformer architectures.*
  - reply preview: 
- **Turn 2** (1388 in / 302 out tokens) — user: *Which of those directions looks most promising for edge deployment, and why?*
  - reply preview: I'm still processing your request for recent research on efficient transformer architectures. Once I have that information, I'll be able to analyze which directions seem most promising for edge deploy…

Full transcripts: `data/transcript_academic_research.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).