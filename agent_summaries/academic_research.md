# SKU Usage Summary — `academic-research` (academic_research)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `8722600015740010496`
- **Use case:** Academic literature analysis & discovery · **Complexity:** Medium-High
- **Unit:** 1 interaction = 2-turn conversation + memory-write (3.1 model calls avg), averaged over **40 interactions**. Deployed on Vertex AI Agent Engine (GEAP).
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

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; **40 runs** for variability; 300s Monitoring settle; token usage from the model response (`usage_metadata`, exact), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package academic_research --runs 40 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 40 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 4058 | 2367–8369 | Medium |
| Gemini output tokens (incl. thinking) | tokens | 890 | 393–3026 | High |
| Model calls | calls | 3.1 | — | Medium |
| Agent Runtime — vCPU | vCPU-seconds | 72.7 | — | — |
| Agent Runtime — memory | GiB-seconds | 125.1 | — | — |
| Sessions | events appended | 6.2 | — | Medium |
| Memory Bank — generation | tokens | 2555 | — | — |
| Memory Bank — memories written | memories | 0.1 | — | — |
| Memory Bank — retrievals | reads | 0.0 | — | — |
| Firestore — document writes | writes | 0.05 | — | — |
| Firestore — document reads | reads | 0.68 | — | — |
| Vertex AI Search (RAG) — queries | searches | 0.38 | — | — |
| Google Search grounding — query turns | grounded turns | 0.68 | — | — |

_Memory retrievals = 0 for this workload: the agent either has no retrieval tool (the adk-sample agents) or answers directly without invoking recall (the support-FAQ chatbot — it IS `load_memory`-capable and recalls when asked, but its FAQ turns don't trigger it). Retrieval IS exercised by the returning-user runs of workflow-operator, autonomous-researcher, and multi-agent-orchestrator, and by `memory_assistant`._

## 5. Grounding & media usage

- **Google Search grounding:** 0.68 grounded query-turns per interaction measured (web_researcher AgentTool invocations; each runs ≥1 native google_search generation). Bills ~$14/1K grounded turns. NOTE: native google_search grounding_metadata is encapsulated inside the AgentTool and the Monitoring web_search_requests metric does not track native ADK google_search — so the AgentTool call count is the measurable unit.
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
| Gemini tokens | 0.0034 |
| Agent Runtime | 0.0021 |
| Memory Bank + Sessions | 0.0023 |
| Firestore (2w/27r over 40 runs) | 0.0000000 |
| Vertex AI Search (RAG: 0.38 queries/intxn @ $1.50/1K) | 0.000563 |
| Google Search grounding (0.68 grounded turns/intxn @ $14/1K) | 0.009450 |
| Model Armor (derived: 4948 tok scanned @ $0.10/1M) | 0.000495 |
| **Total (measured SKUs)** | **0.0183** (range 0.0061–0.0131) |

## 7. Test workload & sample interactions

**40 interactions** (80 total user turns), fresh user_id per interaction. All interactions repeat the same 2-turn workload to isolate run-to-run variability.

**Workload (turn-by-turn):**

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