# SKU Usage Summary — `autonomous-researcher (archetype)` (autonomous_researcher)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `1217914186680500224`
- **Use case:** Deep web research with synthesis · **Complexity:** Archetype: Autonomous Researcher / Moderate
- **Unit:** 1 interaction = 2–4-turn (varying) conversation + memory-write (7.8 model calls avg), averaged over **79 interactions**. Deployed on Vertex AI Agent Engine (GEAP).
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

Deployed to Agent Engine; per run = 2–4-turn (varying) conversation in one session + add_session_to_memory; **79 runs** for variability; 300s Monitoring settle; token usage from Cloud Monitoring **`token_count`** (the complete total — captures AgentTool sub-agent tokens the stream misses; undercount factor **1.1156×** vs `usage_metadata`), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package autonomous_researcher --runs 79 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 79 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 32585 | 12516–122408 | High |
| Gemini output tokens (incl. thinking) | tokens | 10739 | 5728–18665 | Medium |
| Gemini tokens — master/coordinator | tokens | 39468 | 91% of I/O | — |
| Gemini tokens — sub-agents/tools | tokens | 3856 | 9% of I/O | — |
| Model calls | calls | 7.8 | — | Medium |
| Agent Runtime — vCPU | vCPU-seconds | 171.2 | — | — |
| Agent Runtime — memory | GiB-seconds | 200.6 | — | — |
| Sessions | events appended | 15.6 | — | Medium |
| Memory Bank — generation | tokens | 7999 | — | — |
| Memory Bank — memories written | memories | 0.6 | — | — |
| Memory Bank — retrievals | reads | 0.4 | — | — |
| Firestore — document writes | writes | 1.34 | — | — |
| Firestore — document reads | reads | 2.06 | — | — |
| Vertex AI Search (RAG) — queries | searches | 1.18 | — | — |
| Google Search grounding — query turns | grounded turns | 1.62 | — | — |


## 5. Grounding & media usage

- **Google Search grounding:** 1.62 grounded query-turns per interaction measured (web_researcher AgentTool invocations; each runs ≥1 native google_search generation). Bills ~$14/1K grounded turns. NOTE: native google_search grounding_metadata is encapsulated inside the AgentTool and the Monitoring web_search_requests metric does not track native ADK google_search — so the AgentTool call count is the measurable unit.
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
| Gemini tokens | 0.0366 |
| Agent Runtime | 0.0101 |
| Memory Bank + Sessions | 0.0065 |
| Firestore (106w/163r over 79 runs) | 0.0000005 |
| Vertex AI Search (RAG: 1.18 queries/intxn @ $1.50/1K) | 0.001766 |
| Google Search grounding (1.62 grounded turns/intxn @ $14/1K) | 0.022684 |
| Memory Bank retrieval (0.38 memories retrieved/intxn @ $0.5/1K) | 0.000190 |
| Model Armor (derived: 43324 tok scanned @ $0.10/1M) | 0.004332 |
| **Total (measured SKUs)** | **0.0822** (range 0.0347–0.1000) |

## 7. Test workload & sample interactions

**45 interactions** (253 total user turns), fresh user_id per interaction. Interactions cycle **10 distinct conversation scenarios** of varying length (2-turn×8, 3-turn×16, 4-turn×16, 16-turn×1, 21-turn×1, 24-turn×1, 32-turn×2) — real-world interactions differ in length and topic, so this spreads coverage rather than repeating one script.

**Scenario 1** (2 turns):

| Turn | User query |
|---|---|
| 1 | Research the current state of small modular reactors (SMRs) and their commercial outlook. |
| 2 | Now focus on the main regulatory and cost barriers, and which companies lead. |

**Scenario 2** (3 turns):

| Turn | User query |
|---|---|
| 1 | Research the state of solid-state EV batteries in 2026. |
| 2 | Which companies are closest to mass production, and what hurdles remain? |
| 3 | Summarize the investment outlook. |

**Scenario 3** (3 turns):

| Turn | User query |
|---|---|
| 1 | Research recent advances in direct-air carbon capture. |
| 2 | Compare it with point-source capture on cost and scalability. |
| 3 | Which approach is more likely to scale this decade, and why? |

**Scenario 4** (4 turns):

| Turn | User query |
|---|---|
| 1 | Research the latest in efficient transformer architectures. |
| 2 | Which techniques work best for edge deployment? |
| 3 | How do quantization and distillation compare there? |
| 4 | Summarize the practical recommendation. |

**Scenario 5** (4 turns):

| Turn | User query |
|---|---|
| 1 | Research the RAG vs long-context-window tradeoff for enterprise search. |
| 2 | What are the cost implications of each? |
| 3 | When does hybrid (keyword + vector) retrieval help? |
| 4 | Give a recommended architecture for a 10M-document corpus. |

**Scenario 6** (16 turns):

| Turn | User query |
|---|---|
| 1 | Research the current state of small modular reactors (SMRs) and their commercial outlook. |
| 2 | Now focus on the main regulatory and cost barriers, and which companies lead. |
| 3 | Research the current state of small modular reactors (SMRs) and their commercial outlook. |
| 4 | Now focus on the main regulatory and cost barriers, and which companies lead. |
| 5 | Research the current state of small modular reactors (SMRs) and their commercial outlook. |
| 6 | Now focus on the main regulatory and cost barriers, and which companies lead. |
| 7 | Research the current state of small modular reactors (SMRs) and their commercial outlook. |
| 8 | Now focus on the main regulatory and cost barriers, and which companies lead. |
| 9 | Research the current state of small modular reactors (SMRs) and their commercial outlook. |
| 10 | Now focus on the main regulatory and cost barriers, and which companies lead. |
| 11 | Research the current state of small modular reactors (SMRs) and their commercial outlook. |
| 12 | Now focus on the main regulatory and cost barriers, and which companies lead. |
| 13 | Research the current state of small modular reactors (SMRs) and their commercial outlook. |
| 14 | Now focus on the main regulatory and cost barriers, and which companies lead. |
| 15 | Research the current state of small modular reactors (SMRs) and their commercial outlook. |
| 16 | Now focus on the main regulatory and cost barriers, and which companies lead. |

**Scenario 7** (24 turns):

| Turn | User query |
|---|---|
| 1 | Research the state of solid-state EV batteries in 2026. |
| 2 | Which companies are closest to mass production, and what hurdles remain? |
| 3 | Summarize the investment outlook. |
| 4 | Research the state of solid-state EV batteries in 2026. |
| 5 | Which companies are closest to mass production, and what hurdles remain? |
| 6 | Summarize the investment outlook. |
| 7 | Research the state of solid-state EV batteries in 2026. |
| 8 | Which companies are closest to mass production, and what hurdles remain? |
| 9 | Summarize the investment outlook. |
| 10 | Research the state of solid-state EV batteries in 2026. |
| 11 | Which companies are closest to mass production, and what hurdles remain? |
| 12 | Summarize the investment outlook. |
| 13 | Research the state of solid-state EV batteries in 2026. |
| 14 | Which companies are closest to mass production, and what hurdles remain? |
| 15 | Summarize the investment outlook. |
| 16 | Research the state of solid-state EV batteries in 2026. |
| 17 | Which companies are closest to mass production, and what hurdles remain? |
| 18 | Summarize the investment outlook. |
| 19 | Research the state of solid-state EV batteries in 2026. |
| 20 | Which companies are closest to mass production, and what hurdles remain? |
| 21 | Summarize the investment outlook. |
| 22 | Research the state of solid-state EV batteries in 2026. |
| 23 | Which companies are closest to mass production, and what hurdles remain? |
| 24 | Summarize the investment outlook. |

**Scenario 8** (32 turns):

| Turn | User query |
|---|---|
| 1 | Research the latest in efficient transformer architectures. |
| 2 | Which techniques work best for edge deployment? |
| 3 | How do quantization and distillation compare there? |
| 4 | Summarize the practical recommendation. |
| 5 | Research the latest in efficient transformer architectures. |
| 6 | Which techniques work best for edge deployment? |
| 7 | How do quantization and distillation compare there? |
| 8 | Summarize the practical recommendation. |
| 9 | Research the latest in efficient transformer architectures. |
| 10 | Which techniques work best for edge deployment? |
| 11 | How do quantization and distillation compare there? |
| 12 | Summarize the practical recommendation. |
| 13 | Research the latest in efficient transformer architectures. |
| 14 | Which techniques work best for edge deployment? |
| 15 | How do quantization and distillation compare there? |
| 16 | Summarize the practical recommendation. |
| 17 | Research the latest in efficient transformer architectures. |
| 18 | Which techniques work best for edge deployment? |
| 19 | How do quantization and distillation compare there? |
| 20 | Summarize the practical recommendation. |
| 21 | Research the latest in efficient transformer architectures. |
| 22 | Which techniques work best for edge deployment? |
| 23 | How do quantization and distillation compare there? |
| 24 | Summarize the practical recommendation. |
| 25 | Research the latest in efficient transformer architectures. |
| 26 | Which techniques work best for edge deployment? |
| 27 | How do quantization and distillation compare there? |
| 28 | Summarize the practical recommendation. |
| 29 | Research the latest in efficient transformer architectures. |
| 30 | Which techniques work best for edge deployment? |
| 31 | How do quantization and distillation compare there? |
| 32 | Summarize the practical recommendation. |

**Scenario 9** (32 turns):

| Turn | User query |
|---|---|
| 1 | Research the RAG vs long-context-window tradeoff for enterprise search. |
| 2 | What are the cost implications of each? |
| 3 | When does hybrid (keyword + vector) retrieval help? |
| 4 | Give a recommended architecture for a 10M-document corpus. |
| 5 | Research the RAG vs long-context-window tradeoff for enterprise search. |
| 6 | What are the cost implications of each? |
| 7 | When does hybrid (keyword + vector) retrieval help? |
| 8 | Give a recommended architecture for a 10M-document corpus. |
| 9 | Research the RAG vs long-context-window tradeoff for enterprise search. |
| 10 | What are the cost implications of each? |
| 11 | When does hybrid (keyword + vector) retrieval help? |
| 12 | Give a recommended architecture for a 10M-document corpus. |
| 13 | Research the RAG vs long-context-window tradeoff for enterprise search. |
| 14 | What are the cost implications of each? |
| 15 | When does hybrid (keyword + vector) retrieval help? |
| 16 | Give a recommended architecture for a 10M-document corpus. |
| 17 | Research the RAG vs long-context-window tradeoff for enterprise search. |
| 18 | What are the cost implications of each? |
| 19 | When does hybrid (keyword + vector) retrieval help? |
| 20 | Give a recommended architecture for a 10M-document corpus. |
| 21 | Research the RAG vs long-context-window tradeoff for enterprise search. |
| 22 | What are the cost implications of each? |
| 23 | When does hybrid (keyword + vector) retrieval help? |
| 24 | Give a recommended architecture for a 10M-document corpus. |
| 25 | Research the RAG vs long-context-window tradeoff for enterprise search. |
| 26 | What are the cost implications of each? |
| 27 | When does hybrid (keyword + vector) retrieval help? |
| 28 | Give a recommended architecture for a 10M-document corpus. |
| 29 | Research the RAG vs long-context-window tradeoff for enterprise search. |
| 30 | What are the cost implications of each? |
| 31 | When does hybrid (keyword + vector) retrieval help? |
| 32 | Give a recommended architecture for a 10M-document corpus. |

**Scenario 10** (21 turns):

| Turn | User query |
|---|---|
| 1 | Research recent advances in direct-air carbon capture. |
| 2 | Compare it with point-source capture on cost and scalability. |
| 3 | Which approach is more likely to scale this decade, and why? |
| 4 | Research recent advances in direct-air carbon capture. |
| 5 | Compare it with point-source capture on cost and scalability. |
| 6 | Which approach is more likely to scale this decade, and why? |
| 7 | Research recent advances in direct-air carbon capture. |
| 8 | Compare it with point-source capture on cost and scalability. |
| 9 | Which approach is more likely to scale this decade, and why? |
| 10 | Research recent advances in direct-air carbon capture. |
| 11 | Compare it with point-source capture on cost and scalability. |
| 12 | Which approach is more likely to scale this decade, and why? |
| 13 | Research recent advances in direct-air carbon capture. |
| 14 | Compare it with point-source capture on cost and scalability. |
| 15 | Which approach is more likely to scale this decade, and why? |
| 16 | Research recent advances in direct-air carbon capture. |
| 17 | Compare it with point-source capture on cost and scalability. |
| 18 | Which approach is more likely to scale this decade, and why? |
| 19 | Research recent advances in direct-air carbon capture. |
| 20 | Compare it with point-source capture on cost and scalability. |
| 21 | Which approach is more likely to scale this decade, and why? |

**Sample interaction (first run):**

- **Turn 1** (11852 in / 7672 out tokens) — user: *Research the current state of small modular reactors (SMRs) and their commercial outlook.*
  - reply preview: ## Research Report: The Current State and Commercial Outlook of Small Modular Reactors (SMRs)  ### Executive Summary  Small Modular Reactors (SMRs) are emerging as a pivotal technology in the global c…
- **Turn 2** (21136 in / 4155 out tokens) — user: *Now focus on the main regulatory and cost barriers, and which companies lead.*
  - reply preview: ## Research Report: Regulatory and Cost Barriers, and Leading Companies in Small Modular Reactor (SMR) Development  ### Executive Summary  The advancement and commercial deployment of Small Modular Re…

Full transcripts: `data/transcript_autonomous_researcher.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).