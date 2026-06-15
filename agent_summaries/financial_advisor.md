# SKU Usage Summary — `financial-advisor` (financial_advisor)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `343270278970736640`
- **Use case:** Stock analysis & trading-strategy advisor · **Complexity:** High
- **Unit:** 1 interaction = 2-turn conversation + memory-write (3.5 model calls avg). Deployed on Vertex AI Agent Engine (GEAP).
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

A single user query fans out to multiple model calls; in EXP-006 it consumed 17k–34k input tokens per interaction (heaviest input-token consumer in the corpus).

**Pattern:** Hierarchical (coordinator + 4 AgentTool specialists)

## 2. SKUs (products) consumed

Gemini tokens (input/output/cached); Agent Runtime (vCPU + memory); Sessions; Memory Bank (generation + writes); Google Search grounding (capable but not triggered).

(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised via add_session_to_memory. Search grounding / Imagen used by the agent but usage not yet metered here — see §7.)

## 3. How usage was measured

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; **35 runs** for variability; 300s Monitoring settle; token usage from the model response (`usage_metadata`, exact), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package financial_advisor --runs 35 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 35 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 21786 | 7979–81100 | High |
| Gemini output tokens (incl. thinking) | tokens | 2753 | 1072–12463 | Very high |
| Model calls | calls | 3.5 | — | Medium |
| Agent Runtime — vCPU | vCPU-seconds | 543.0 | — | — |
| Agent Runtime — memory | GiB-seconds | 589.9 | — | — |
| Sessions | events appended | 7.1 | — | Medium |
| Memory Bank — generation | tokens | 3087 | — | — |
| Memory Bank — memories written | memories | 0.9 | — | — |
| Memory Bank — retrievals | reads | 0.0 | — | — |

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
| Gemini tokens | 0.0134 |
| Agent Runtime | 0.0145 |
| Memory Bank + Sessions | 0.0010 |
| **Total (measured SKUs)** | **0.0289** (range 0.0215–0.0710) |

## 7. Test workload & sample interactions

**35 interactions** (70 total user turns), fresh user_id per interaction. All interactions repeat the same 2-turn workload to isolate run-to-run variability.

**Workload (turn-by-turn):**

| Turn | User query |
|---|---|
| 1 | I'm a moderate-risk investor. Analyze the outlook for NVDA. |
| 2 | Based on that, suggest a simple trading strategy and key risks. |

**Sample interaction (first run):**

- **Turn 1** (7295 in / 1563 out tokens) — user: *I'm a moderate-risk investor. Analyze the outlook for NVDA.*
  - reply preview: Hello! I'm here to help you navigate the world of financial decision-making. My main goal is to provide you with comprehensive financial advice by guiding you through a step-by-step process. We'll wor…
- **Turn 2** (16737 in / 2853 out tokens) — user: *Based on that, suggest a simple trading strategy and key risks.*
  - reply preview: Of course. To provide a trading strategy, I will assume a **medium-term** investment period, as this typically aligns with a moderate-risk profile.  I will now call the `trading_analyst` subagent to g…

Full transcripts: `data/transcript_financial_advisor.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).