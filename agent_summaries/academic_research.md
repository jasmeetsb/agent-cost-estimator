# SKU Usage Summary — `academic-research` (academic_research)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `4269102934224011264`
- **Use case:** Academic literature analysis & discovery · **Complexity:** Medium-High
- **Unit:** 1 interaction = 2-turn conversation + memory-write (3.0 model calls avg), averaged over **80 interactions**. Deployed on Vertex AI Agent Engine (GEAP).
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

(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised via add_session_to_memory. Search grounding / Imagen used by the agent but usage not yet metered here — see §7.)

## 3. How usage was measured

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; **80 runs** for variability; 300s Monitoring settle; token usage from the model response (`usage_metadata`, exact), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package academic_research --runs 80 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 80 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 4055 | 2367–8369 | Medium |
| Gemini output tokens (incl. thinking) | tokens | 958 | 341–3193 | High |
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
| Google Search grounding — query turns | grounded turns | 0.70 | — | — |

_Memory retrievals = 0 for this workload: the agent either has no retrieval tool (the adk-sample agents) or answers directly without invoking recall (the support-FAQ chatbot — it IS `load_memory`-capable and recalls when asked, but its FAQ turns don't trigger it). Retrieval IS exercised by the returning-user runs of workflow-operator, autonomous-researcher, and multi-agent-orchestrator, and by `memory_assistant`._

## 5. Grounding & media usage

- **Google Search grounding:** 0.70 grounded query-turns per interaction measured (web_researcher AgentTool invocations; each runs ≥1 native google_search generation). Bills ~$14/1K grounded turns. NOTE: native google_search grounding_metadata is encapsulated inside the AgentTool and the Monitoring web_search_requests metric does not track native ADK google_search — so the AgentTool call count is the measurable unit.
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
| Gemini tokens | 0.0036 |
| Agent Runtime | 0.0028 |
| Memory Bank + Sessions | 0.0023 |
| Firestore (3w/45r over 80 runs) | 0.0000000 |
| Vertex AI Search (RAG: 0.34 queries/intxn @ $1.50/1K) | 0.000506 |
| Google Search grounding (0.70 grounded turns/intxn @ $14/1K) | 0.009800 |
| Model Armor (derived: 5013 tok scanned @ $0.10/1M) | 0.000501 |
| **Total (measured SKUs)** | **0.0195** (range 0.0067–0.0143) |

## 7. Test workload & sample interactions

**45 interactions** (160 total user turns), fresh user_id per interaction. Interactions cycle **2 distinct conversation scenarios** of varying length (2-turn×40, 16-turn×5) — real-world interactions differ in length and topic, so this spreads coverage rather than repeating one script.

**Scenario 1** (2 turns):

| Turn | User query |
|---|---|
| 1 | Summarize recent research directions in efficient transformer architectures. |
| 2 | Which of those directions looks most promising for edge deployment, and why? |

**Scenario 2** (16 turns):

| Turn | User query |
|---|---|
| 1 | Summarize recent research directions in efficient transformer architectures. |
| 2 | Which of those directions looks most promising for edge deployment, and why? |
| 3 | Summarize recent research directions in efficient transformer architectures. |
| 4 | Which of those directions looks most promising for edge deployment, and why? |
| 5 | Summarize recent research directions in efficient transformer architectures. |
| 6 | Which of those directions looks most promising for edge deployment, and why? |
| 7 | Summarize recent research directions in efficient transformer architectures. |
| 8 | Which of those directions looks most promising for edge deployment, and why? |
| 9 | Summarize recent research directions in efficient transformer architectures. |
| 10 | Which of those directions looks most promising for edge deployment, and why? |
| 11 | Summarize recent research directions in efficient transformer architectures. |
| 12 | Which of those directions looks most promising for edge deployment, and why? |
| 13 | Summarize recent research directions in efficient transformer architectures. |
| 14 | Which of those directions looks most promising for edge deployment, and why? |
| 15 | Summarize recent research directions in efficient transformer architectures. |
| 16 | Which of those directions looks most promising for edge deployment, and why? |

**Sample interaction (first run):**

- **Turn 1** (2338 in / 278 out tokens) — user: *Summarize recent research directions in efficient transformer architectures.*
  - reply preview: 
- **Turn 2** (1388 in / 302 out tokens) — user: *Which of those directions looks most promising for edge deployment, and why?*
  - reply preview: I'm still processing your request for recent research on efficient transformer architectures. Once I have that information, I'll be able to analyze which directions seem most promising for edge deploy…

Full transcripts: `data/transcript_academic_research.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).