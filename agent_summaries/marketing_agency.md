# SKU Usage Summary — `marketing-agency` (marketing_agency)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `6855475340148473856`
- **Use case:** End-to-end website/branding launch suite · **Complexity:** Medium-High
- **Unit:** 1 interaction = 2-turn conversation + memory-write (3.0 model calls avg), averaged over **35 interactions**. Deployed on Vertex AI Agent Engine (GEAP).
- **Focus:** measured **usage per SKU**; dollar cost is a secondary derived view (§6).

## 1. Architecture

```mermaid
graph TB
    User([User]) --> Coord
    subgraph Engine["Vertex AI Agent Engine — marketing-agency"]
        direction TB
        Coord[marketing_coordinator]
        Coord -->|AgentTool| DC[domain_create_agent]
        Coord -->|AgentTool| WC[website_create_agent]
        Coord -->|AgentTool| MC[marketing_create_agent]
        Coord -->|AgentTool| LC[logo_create_agent]
    end
    subgraph Core["Always-on Agent Platform SKUs"]
        direction LR
        Gemini[("Gemini 2.5 Flash<br/>per-token")]
        Runtime[("Agent Runtime<br/>vCPU + memory-sec")]
        Sess[("Sessions<br/>per event appended")]
        MB[("Memory Bank<br/>per memory + gen tokens")]
    end
    subgraph Extras["Agent-specific SKUs"]
        direction LR
        Imagen[("gemini-2.5-flash-image<br/>per image")]
        GCS[("Cloud Storage<br/>image artifacts")]
    end
    Engine -.-> Core
    LC -.-> Imagen
    LC -.-> GCS
```

`marketing_coordinator` (root) delegates to 4 specialist creators wrapped as AgentTools:
- `domain_create_agent` — suggests/validates domain names
- `website_create_agent` — drafts website hero + content
- `marketing_create_agent` — develops the marketing plan
- `logo_create_agent` — generates the brand logo via Imagen (gemini-2.5-flash-image)

Logo generation is the only sub-agent that exercises the genmedia SKU surface.

**Pattern:** Hierarchical (coordinator + AgentTool creators)

## 2. SKUs (products) consumed

Gemini tokens; Agent Runtime (vCPU + memory); Sessions; Memory Bank; Imagen / gemini-2.5-flash-image (genmedia, billed per image); Google Search grounding (capable, not triggered in our 2-turn workloads).

(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised via add_session_to_memory. Search grounding / Imagen used by the agent but usage not yet metered here — see §7.)

## 3. How usage was measured

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; **35 runs** for variability; 300s Monitoring settle; token usage from the model response (`usage_metadata`, exact), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package marketing_agency --runs 35 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 35 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 3914 | 1816–9947 | High |
| Gemini output tokens (incl. thinking) | tokens | 3487 | 846–63892 | Very high |
| Model calls | calls | 3.0 | — | Medium |
| Agent Runtime — vCPU | vCPU-seconds | 204.0 | — | — |
| Agent Runtime — memory | GiB-seconds | 253.8 | — | — |
| Sessions | events appended | 6.0 | — | Medium |
| Memory Bank — generation | tokens | 2671 | — | — |
| Memory Bank — memories written | memories | 0.5 | — | — |
| Memory Bank — retrievals | reads | 0.0 | — | — |

_Memory retrievals = 0 by design: the harness mints a fresh user_id per interaction and writes memories only at session end, so no user ever has prior memories to retrieve. (Only the chatbot even has a `preload_memory` tool; the others write memories but have no retrieval tool.) The retrieval SKU is exercised by `memory_assistant`, whose workload reuses a user across sessions._

## 5. Grounding & media usage

- **Google Search grounding:** 0 measured. The agent does not use google_search in this workload; would bill ~$14/1K grounded turns if used.
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
| Gemini tokens | 0.0099 |
| Agent Runtime | 0.0055 |
| Memory Bank + Sessions | 0.0008 |
| Model Armor (derived: 7402 tok scanned @ $0.10/1M) | 0.000740 |
| **Total (measured SKUs)** | **0.0170** (range 0.0090–0.1671) |

## 7. Test workload & sample interactions

**35 interactions** (70 total user turns), fresh user_id per interaction. All interactions repeat the same 2-turn workload to isolate run-to-run variability.

**Workload (turn-by-turn):**

| Turn | User query |
|---|---|
| 1 | Create a brand concept for a new oat-milk startup called OatJoy. |
| 2 | Suggest a tagline and a simple landing-page hero section. |

**Sample interaction (first run):**

- **Turn 1** (2090 in / 984 out tokens) — user: *Create a brand concept for a new oat-milk startup called OatJoy.*
  - reply preview: Of course! Let's start by securing the perfect domain name for your oat-milk startup, OatJoy.  I've used a specialized tool to find some creative and available options for you.  domain_create_agent to…
- **Turn 2** (1832 in / 696 out tokens) — user: *Suggest a tagline and a simple landing-page hero section.*
  - reply preview: Excellent ideas! We'll definitely get to crafting the perfect tagline and hero section for your landing page.  However, before we dive into the creative details of your website, we first need to secur…

Full transcripts: `data/transcript_marketing_agency.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).