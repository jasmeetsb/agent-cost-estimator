# SKU Usage Summary — `blog-writer` (blogger_agent)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `3729977198753349632`
- **Use case:** Multi-agent technical blog authoring · **Complexity:** High
- **Unit:** 1 interaction = 2-turn conversation + memory-write (2.0 model calls avg). Deployed on Vertex AI Agent Engine (GEAP).
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

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; **35 runs** for variability; 300s Monitoring settle; token usage from the model response (`usage_metadata`, exact), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package blogger_agent --runs 35 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 35 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 2856 | 1803–3618 | Medium |
| Gemini output tokens (incl. thinking) | tokens | 2538 | 733–4087 | Medium |
| Model calls | calls | 2.0 | — | Low |
| Agent Runtime — vCPU | vCPU-seconds | 118.5 | — | — |
| Agent Runtime — memory | GiB-seconds | 178.4 | — | — |
| Sessions | events appended | 4.0 | — | Low |
| Memory Bank — generation | tokens | 3540 | — | — |
| Memory Bank — memories written | memories | 0.4 | — | — |
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
| Gemini tokens | 0.0072 |
| Agent Runtime | 0.0033 |
| Memory Bank + Sessions | 0.0011 |
| Model Armor (derived: 5394 tok scanned @ $0.10/1M) | 0.000539 |
| **Total (measured SKUs)** | **0.0121** (range 0.0068–0.0156) |

## 7. Test workload & sample interactions

**35 interactions** (70 total user turns), fresh user_id per interaction. All interactions repeat the same 2-turn workload to isolate run-to-run variability.

**Workload (turn-by-turn):**

| Turn | User query |
|---|---|
| 1 | Write a short technical blog post about why vector databases matter for RAG. |
| 2 | Make the intro punchier and add a one-line takeaway at the end. |

**Sample interaction (first run):**

- **Turn 1** (742 in / 1756 out tokens) — user: *Write a short technical blog post about why vector databases matter for RAG.*
  - reply preview: Of course. Here is a short technical blog post about why vector databases matter for RAG:  ***  ### Vector Databases: The Backbone of Retrieval-Augmented Generation (RAG)  If you've been following the…
- **Turn 2** (2514 in / 1704 out tokens) — user: *Make the intro punchier and add a one-line takeaway at the end.*
  - reply preview: Of course. Here is the revised version with a punchier intro and a one-line takeaway.  ***  ### Vector Databases: The Backbone of Retrieval-Augmented Generation (RAG)  Retrieval-Augmented Generation (…

Full transcripts: `data/transcript_blogger_agent.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).