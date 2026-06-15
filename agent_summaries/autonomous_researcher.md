# SKU Usage Summary — `autonomous-researcher (archetype)` (autonomous_researcher)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `1495589251205562368`
- **Use case:** Deep web research with synthesis · **Complexity:** Archetype: Autonomous Researcher / Moderate
- **Unit:** 1 interaction = 2-turn conversation + memory-write (2.2 model calls avg). Deployed on Vertex AI Agent Engine (GEAP).
- **Focus:** measured **usage per SKU**; dollar cost is a secondary derived view (§6).

## 1. Architecture

```mermaid
graph TB
    User([User]) --> Res
    subgraph Engine["Agent Engine — autonomous_researcher"]
        direction TB
        Res["researcher_agent (Gemini 2.5 Flash)<br/>plan → search → synthesize"]
        Res -->|tool| GSt[google_search]
    end
    subgraph Core["Always-on Agent Platform SKUs"]
        direction LR
        Gemini[("Gemini 2.5 Flash<br/>per-token (long outputs)")]
        Runtime[("Agent Runtime<br/>vCPU + memory-sec")]
        Sess[("Sessions<br/>per event appended")]
        MB[("Memory Bank<br/>per memory + gen tokens")]
    end
    subgraph Extras["Agent-specific SKUs"]
        GS[("Google Search grounding<br/>per grounded prompt")]
    end
    Engine -.-> Core
    GSt -.-> GS
```

Deep-research agent (archetype: Autonomous Researcher, Moderate). Plans, grounds on the web via ADK `google_search`, and synthesizes long reports. Token-depth-driven: premium model intent (Gemini Pro), long outputs (~6,000 output tokens/interaction measured), and Search grounding (~69 grounded searches across the run — the first SKU usage that actually exercises Search grounding in this project). Internal-corpus RAG (Vertex AI Search) deferred to the High variant, since google_search must be the sole tool.

**Pattern:** Single agent + Google Search grounding, long outputs

## 2. SKUs (products) consumed

Gemini tokens (long outputs); Agent Runtime (vCPU + memory); Sessions; Memory Bank; **Google Search grounding** (measured non-zero).

(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised via add_session_to_memory. Search grounding / Imagen used by the agent but usage not yet metered here — see §7.)

## 3. How usage was measured

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; **85 runs** for variability; 300s Monitoring settle; token usage from the model response (`usage_metadata`, exact), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package autonomous_researcher --runs 85 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 85 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 3591 | 283–7692 | High |
| Gemini output tokens (incl. thinking) | tokens | 6682 | 678–9506 | Medium |
| Model calls | calls | 2.2 | — | Medium |
| Agent Runtime — vCPU | vCPU-seconds | 164.0 | — | — |
| Agent Runtime — memory | GiB-seconds | 189.4 | — | — |
| Sessions | events appended | 4.4 | — | Medium |
| Memory Bank — generation | tokens | 2600 | — | — |
| Memory Bank — memories written | memories | 0.0 | — | — |
| Memory Bank — retrievals | reads | 0.0 | — | — |

_Memory retrievals = 0: this agent has no preload_memory tool — it writes memories from the session but doesn't read them back._

## 5. Grounding & media usage (now collected)

- **Google Search grounding:** 168 grounded web-search requests measured (Cloud Monitoring, project-wide). The agent *can* ground on Search but this workload did not trigger it; would bill ~$0.035/request if used.
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
| Gemini tokens | 0.0178 |
| Agent Runtime | 0.0068 |
| Memory Bank + Sessions | 0.0019 |
| Search grounding | 0.0692 |
| **Total (measured SKUs)** | **0.0957** (range 0.0796–0.1027) |

## 7. Test workload & sample interactions

**85 interactions** (187 total user turns), fresh user_id per interaction. Interactions cycle **3 distinct conversation scenarios** of varying length (2-turn×68, 3-turn×17) — real-world interactions differ in length and topic, so this spreads coverage rather than repeating one script.

**Scenario 1** (2 turns):

| Turn | User query |
|---|---|
| 1 | Research the current state of small modular nuclear reactors (SMRs) and their commercial outlook. |
| 2 | Now focus on the main regulatory and cost barriers, and which companies lead. |

**Scenario 2** (3 turns):

| Turn | User query |
|---|---|
| 1 | Research the state of solid-state EV batteries in 2026. |
| 2 | Which companies are closest to mass production, and what technical hurdles remain? |
| 3 | Summarize the investment outlook in a few sentences. |

**Scenario 3** (2 turns):

| Turn | User query |
|---|---|
| 1 | Research recent advances in direct-air carbon capture. |
| 2 | Compare it with point-source capture on cost and scalability. |

**Sample interaction (first run):**

- **Turn 1** (134 in / 4371 out tokens) — user: *Research the current state of small modular nuclear reactors (SMRs) and their commercial outlook.*
  - reply preview: Small Modular Reactors (SMRs) are emerging as a significant contender in the global energy landscape, promising a new era for nuclear power with their innovative design and deployment flexibility. The…
- **Turn 2** (3143 in / 2245 out tokens) — user: *Now focus on the main regulatory and cost barriers, and which companies lead.*
  - reply preview: Small Modular Reactors (SMRs) hold significant promise for the future of nuclear energy, but their widespread commercialization is currently hindered by substantial regulatory and cost barriers. Despi…

Full transcripts: `data/transcript_autonomous_researcher.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).