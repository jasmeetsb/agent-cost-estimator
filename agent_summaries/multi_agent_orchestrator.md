# SKU Usage Summary — `multi-agent-orchestrator (archetype)` (multi_agent_orchestrator)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `8613387724776275968`
- **Use case:** Decompose-and-delegate orchestration · **Complexity:** Archetype: Multi-Agent Orchestrator / Moderate
- **Unit:** 1 interaction = 2-turn conversation + memory-write (12.1 model calls avg). Deployed on Vertex AI Agent Engine (GEAP).
- **Focus:** measured **usage per SKU**; dollar cost is a secondary derived view (§6).

## 1. Architecture

```mermaid
graph TB
    User([User]) --> Orch
    subgraph Engine["Agent Engine — multi_agent_orchestrator"]
        direction TB
        Orch["orchestrator_agent (Gemini 2.5 Flash)"]
        Orch -->|sub-agent| DS["data_specialist<br/>(query_metrics, fetch_records, corpus_search)"]
        Orch -->|sub-agent| AS["analysis_specialist<br/>(compute_stats, detect_trends)"]
        Orch -->|sub-agent| ACT["action_specialist<br/>(draft_summary, create_ticket, send_update)"]
    end
    subgraph Core["Always-on Agent Platform SKUs"]
        direction LR
        Gemini[("Gemini 2.5 Flash<br/>per-token (coordinator + 3 sub-agents)")]
        Runtime[("Agent Runtime<br/>vCPU + memory-sec")]
        Sess[("Sessions<br/>per event appended")]
        MB[("Memory Bank<br/>per memory + gen tokens")]
    end
    Engine -.-> Core
    DS -.->|prod| BQ[(BigQuery / RAG)]
```

Coordinator that decomposes a request and delegates to 3 specialist sub-agents — data_specialist (metrics / records / corpus), analysis_specialist (stats / trends), action_specialist (summary / ticket / notify) (archetype: Multi-Agent Orchestrator, Moderate). Fan-out-driven and the most expensive of the four: measured ~20,000 input tokens, ~12.5 model calls, ~25 session events per 2-turn interaction (coordinator + sub-agent token multiplication). Specialist tools are local stand-ins for BigQuery / RAG.

**Pattern:** Coordinator + 3 specialist sub-agents (agent-call fan-out)

## 2. SKUs (products) consumed

Gemini tokens (coordinator + sub-agents); Agent Runtime (vCPU + memory); Sessions; Memory Bank. (Specialist BigQuery/RAG calls mocked — would bill in production.)

(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised via add_session_to_memory. Search grounding / Imagen used by the agent but usage not yet metered here — see §7.)

## 3. How usage was measured

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; **40 runs** for variability; 300s Monitoring settle; token usage from the model response (`usage_metadata`, exact), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package multi_agent_orchestrator --runs 40 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 40 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 19450 | 2704–76351 | Very high |
| Gemini output tokens (incl. thinking) | tokens | 4294 | 941–9015 | High |
| Model calls | calls | 12.1 | — | High |
| Agent Runtime — vCPU | vCPU-seconds | 155.4 | — | — |
| Agent Runtime — memory | GiB-seconds | 216.5 | — | — |
| Sessions | events appended | 24.1 | — | High |
| Memory Bank — generation | tokens | 0 | — | — |
| Memory Bank — memories written | memories | 0.0 | — | — |
| Memory Bank — retrievals | reads | 0.0 | — | — |
| Firestore — document writes | writes | 0.20 | — | — |
| Firestore — document reads | reads | 0.78 | — | — |

_Memory retrievals = 0: this agent has no preload_memory tool — it writes memories from the session but doesn't read them back._

## 5. Grounding & media usage (now collected)

- **Google Search grounding:** 0 grounded web-search requests measured (Cloud Monitoring, project-wide). The agent *can* ground on Search but this workload did not trigger it; would bill ~$0.035/request if used.
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
| Gemini tokens | 0.0166 |
| Agent Runtime | 0.0043 |
| Memory Bank + Sessions | 0.0060 |
| Firestore (8w/31r over 40 runs) | 0.0000001 |
| **Total (measured SKUs)** | **0.0269** (range 0.0136–0.0541) |

## 7. Test workload & sample interactions

**40 interactions** (132 total user turns), fresh user_id per interaction. Interactions cycle **3 distinct conversation scenarios** of varying length (2-turn×14, 3-turn×13, 5-turn×13) — real-world interactions differ in length and topic, so this spreads coverage rather than repeating one script.

**Scenario 1** (2 turns):

| Turn | User query |
|---|---|
| 1 | Analyze last quarter's support-ticket volume trend and recommend actions. |
| 2 | Now draft an executive summary, open a follow-up ticket, and send an update to the ops channel. |

**Scenario 2** (3 turns):

| Turn | User query |
|---|---|
| 1 | Pull our key product metrics for the last 30 days and analyze the trend. |
| 2 | Fetch the related customer records. |
| 3 | Summarize the findings, create a ticket for the biggest issue, and notify the team. |

**Scenario 3** (5 turns):

| Turn | User query |
|---|---|
| 1 | Gather sales metrics and the internal playbook on churn. |
| 2 | Analyze the churn trend. |
| 3 | Cross-reference it with recent support tickets. |
| 4 | Draft an executive summary of what's driving churn. |
| 5 | Open a remediation ticket and send an update to the ops channel. |

**Sample interaction (first run):**

- **Turn 1** (619 in / 193 out tokens) — user: *Analyze last quarter's support-ticket volume trend and recommend actions.*
  - reply preview: 
- **Turn 2** (2085 in / 1064 out tokens) — user: *Now draft an executive summary, open a follow-up ticket, and send an update to the ops channel.*
  - reply preview: Please provide the support-ticket volume data for the last quarter so I can analyze the trend.

Full transcripts: `data/transcript_multi_agent_orchestrator.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).