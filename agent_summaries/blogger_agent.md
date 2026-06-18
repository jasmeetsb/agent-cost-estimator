# SKU Usage Summary — `blog-writer` (blogger_agent)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `5724610038794813440`
- **Use case:** Multi-agent technical blog authoring · **Complexity:** High
- **Unit:** 1 interaction = 2-turn conversation + memory-write (4.8 model calls avg), averaged over **80 interactions**. Deployed on Vertex AI Agent Engine (GEAP).
- **Focus:** measured **usage per SKU**; dollar cost is a secondary derived view (§6).

## 1. Architecture

```mermaid
graph TB
    User([User]) <-->|HITL refine| Coord
    subgraph Engine["Vertex AI Agent Engine — blog-writer"]
        direction TB
        Coord[interactive_blogger_agent]
        Coord --> P1[blog_planner]
        P1 --> P2[blog_writer]
        P2 --> P3[blog_editor]
        P3 --> P4[social_media_writer]
    end
    subgraph Core["Always-on Agent Platform SKUs"]
        direction LR
        Gemini[("Gemini 2.5 Flash<br/>per-token")]
        Runtime[("Agent Runtime<br/>vCPU + memory-sec")]
        Sess[("Sessions<br/>per event appended")]
        MB[("Memory Bank<br/>per memory + gen tokens")]
    end
    Engine -.-> Core
```

`interactive_blogger_agent` orchestrates a 4-stage pipeline of sub-agents:
1. `blog_planner` — outlines structure from the topic
2. `blog_writer` — drafts the post
3. `blog_editor` — refines tone, clarity, structure
4. `social_media_writer` — creates social posts from the blog

Human-in-the-loop: the user can request changes mid-flow and the root re-invokes the relevant sub-agent.

**Pattern:** Hierarchical + Sequential (4 sub-agents) + HITL

## 2. SKUs (products) consumed

Gemini tokens; Agent Runtime (vCPU + memory); Sessions; Memory Bank; Google Search grounding (capable, not triggered).

(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised via add_session_to_memory. Search grounding / Imagen used by the agent but usage not yet metered here — see §7.)

## 3. How usage was measured

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; **80 runs** for variability; 300s Monitoring settle; token usage from Cloud Monitoring **`token_count`** (the complete total — captures AgentTool sub-agent tokens the stream misses; undercount factor **1.1075×** vs `usage_metadata`), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package blogger_agent --runs 80 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 80 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 11345 | 4187–22789 | Medium |
| Gemini output tokens (incl. thinking) | tokens | 5425 | 337–11277 | High |
| Gemini tokens — master/coordinator (input) | tokens | 9268 | — | — |
| Gemini tokens — master/coordinator (output) | tokens | 2689 | — | — |
| Gemini tokens — sub-agents/tools (input) | tokens | 2077 | — | — |
| Gemini tokens — sub-agents/tools (output) | tokens | 2736 | — | — |
| Model calls | calls | 4.8 | — | Medium |
| Agent Runtime — vCPU | vCPU-seconds | 101.3 | — | — |
| Agent Runtime — memory | GiB-seconds | 137.8 | — | — |
| Sessions | events appended | 11.1 | — | Medium |
| Memory Bank — generation | tokens | 4603 | — | — |
| Memory Bank — memories written | memories | 0.3 | — | — |
| Memory Bank — retrievals | reads | 0.3 | — | — |
| Firestore — document writes | writes | 0.00 | — | — |
| Firestore — document reads | reads | 0.95 | — | — |
| Vertex AI Search (RAG) — queries | searches | 0.80 | — | — |
| Google Search grounding — query turns | grounded turns | 0.50 | — | — |


_Master vs sub-agent split: each agent's master/sub token share is measured directly (two-model validation — coordinator on gemini-3.5-flash, sub-agents/tools on gemini-3.1-flash-lite, separated via Cloud Monitoring `token_count` by model). The four input/output × master/sub values reconcile both the master/sub totals and the input/output totals (seeded by the measured per-role in:out ratio — master 88:12, sub 61:39). Single-agent agents are 100% master._

## 5. Grounding & media usage

- **Google Search grounding:** 0.50 grounded query-turns per interaction measured (web_researcher AgentTool invocations; each runs ≥1 native google_search generation). Bills ~$14/1K grounded turns. NOTE: native google_search grounding_metadata is encapsulated inside the AgentTool and the Monitoring web_search_requests metric does not track native ADK google_search — so the AgentTool call count is the measurable unit.
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
| Gemini tokens | 0.0170 |
| Agent Runtime | 0.0058 |
| Memory Bank + Sessions | 0.0043 |
| Firestore (0w/76r over 80 runs) | 0.0000000 |
| Vertex AI Search (RAG: 0.80 queries/intxn @ $1.50/1K) | 0.001200 |
| Google Search grounding (0.50 grounded turns/intxn @ $14/1K) | 0.007000 |
| Memory Bank retrieval (0.31 memories retrieved/intxn @ $0.5/1K) | 0.000156 |
| Model Armor (derived: 16770 tok scanned @ $0.10/1M) | 0.001677 |
| Search grounding | 0.0267 |
| **Total (measured SKUs)** | **0.0638** (range 0.0389–0.0719) |

## 7. Test workload & sample interactions

**45 interactions** (160 total user turns), fresh user_id per interaction. Interactions cycle **2 distinct conversation scenarios** of varying length (2-turn×40, 16-turn×5) — real-world interactions differ in length and topic, so this spreads coverage rather than repeating one script.

**Scenario 1** (2 turns):

| Turn | User query |
|---|---|
| 1 | Write a short technical blog post about why vector databases matter for RAG. |
| 2 | Make the intro punchier and add a one-line takeaway at the end. |

**Scenario 2** (16 turns):

| Turn | User query |
|---|---|
| 1 | Write a short technical blog post about why vector databases matter for RAG. |
| 2 | Make the intro punchier and add a one-line takeaway at the end. |
| 3 | Write a short technical blog post about why vector databases matter for RAG. |
| 4 | Make the intro punchier and add a one-line takeaway at the end. |
| 5 | Write a short technical blog post about why vector databases matter for RAG. |
| 6 | Make the intro punchier and add a one-line takeaway at the end. |
| 7 | Write a short technical blog post about why vector databases matter for RAG. |
| 8 | Make the intro punchier and add a one-line takeaway at the end. |
| 9 | Write a short technical blog post about why vector databases matter for RAG. |
| 10 | Make the intro punchier and add a one-line takeaway at the end. |
| 11 | Write a short technical blog post about why vector databases matter for RAG. |
| 12 | Make the intro punchier and add a one-line takeaway at the end. |
| 13 | Write a short technical blog post about why vector databases matter for RAG. |
| 14 | Make the intro punchier and add a one-line takeaway at the end. |
| 15 | Write a short technical blog post about why vector databases matter for RAG. |
| 16 | Make the intro punchier and add a one-line takeaway at the end. |

**Sample interaction (first run):**

- **Turn 1** (2567 in / 247 out tokens) — user: *Write a short technical blog post about why vector databases matter for RAG.*
  - reply preview: 
- **Turn 2** (2051 in / 3073 out tokens) — user: *Make the intro punchier and add a one-line takeaway at the end.*
  - reply preview: ## Blog Post Outline: Unlocking Smarter LLMs: Why Vector Databases Are Indispensable for RAG  ### I. Introduction: The LLM's Double-Edged Sword  *   **The Promise and Peril of LLMs:** Large Language M…

Full transcripts: `data/transcript_blogger_agent.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).