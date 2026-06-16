# SKU Usage Summary — `marketing-agency` (marketing_agency)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `5911509423330689024`
- **Use case:** End-to-end website/branding launch suite · **Complexity:** Medium-High
- **Unit:** 1 interaction = 2-turn conversation + memory-write (3.7 model calls avg), averaged over **80 interactions**. Deployed on Vertex AI Agent Engine (GEAP).
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

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; **80 runs** for variability; 300s Monitoring settle; token usage from the model response (`usage_metadata`, exact), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package marketing_agency --runs 80 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 80 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 7027 | 2621–18972 | High |
| Gemini output tokens (incl. thinking) | tokens | 1184 | 535–3126 | High |
| Model calls | calls | 3.7 | — | Medium |
| Agent Runtime — vCPU | vCPU-seconds | 187.9 | — | — |
| Agent Runtime — memory | GiB-seconds | 231.3 | — | — |
| Sessions | events appended | 7.6 | — | Medium |
| Memory Bank — generation | tokens | 2762 | — | — |
| Memory Bank — memories written | memories | 0.6 | — | — |
| Memory Bank — retrievals | reads | 0.4 | — | — |
| Firestore — document writes | writes | 0.05 | — | — |
| Firestore — document reads | reads | 1.01 | — | — |
| Vertex AI Search (RAG) — queries | searches | 1.70 | — | — |
| Google Search grounding — query turns | grounded turns | 0.53 | — | — |


## 5. Grounding & media usage

- **Google Search grounding:** 0.53 grounded query-turns per interaction measured (web_researcher AgentTool invocations; each runs ≥1 native google_search generation). Bills ~$14/1K grounded turns. NOTE: native google_search grounding_metadata is encapsulated inside the AgentTool and the Monitoring web_search_requests metric does not track native ADK google_search — so the AgentTool call count is the measurable unit.
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
| Gemini tokens | 0.0051 |
| Agent Runtime | 0.0062 |
| Memory Bank + Sessions | 0.0030 |
| Firestore (4w/81r over 80 runs) | 0.0000001 |
| Vertex AI Search (RAG: 1.70 queries/intxn @ $1.50/1K) | 0.002550 |
| Google Search grounding (0.53 grounded turns/intxn @ $14/1K) | 0.007350 |
| Memory Bank retrieval (0.40 memories retrieved/intxn @ $0.5/1K) | 0.000200 |
| Model Armor (derived: 8211 tok scanned @ $0.10/1M) | 0.000821 |
| **Total (measured SKUs)** | **0.0252** (range 0.0120–0.0214) |

## 7. Test workload & sample interactions

**45 interactions** (160 total user turns), fresh user_id per interaction. Interactions cycle **2 distinct conversation scenarios** of varying length (2-turn×40, 16-turn×5) — real-world interactions differ in length and topic, so this spreads coverage rather than repeating one script.

**Scenario 1** (2 turns):

| Turn | User query |
|---|---|
| 1 | Create a brand concept for a new oat-milk startup called OatJoy. |
| 2 | Suggest a tagline and a simple landing-page hero section. |

**Scenario 2** (16 turns):

| Turn | User query |
|---|---|
| 1 | Create a brand concept for a new oat-milk startup called OatJoy. |
| 2 | Suggest a tagline and a simple landing-page hero section. |
| 3 | Create a brand concept for a new oat-milk startup called OatJoy. |
| 4 | Suggest a tagline and a simple landing-page hero section. |
| 5 | Create a brand concept for a new oat-milk startup called OatJoy. |
| 6 | Suggest a tagline and a simple landing-page hero section. |
| 7 | Create a brand concept for a new oat-milk startup called OatJoy. |
| 8 | Suggest a tagline and a simple landing-page hero section. |
| 9 | Create a brand concept for a new oat-milk startup called OatJoy. |
| 10 | Suggest a tagline and a simple landing-page hero section. |
| 11 | Create a brand concept for a new oat-milk startup called OatJoy. |
| 12 | Suggest a tagline and a simple landing-page hero section. |
| 13 | Create a brand concept for a new oat-milk startup called OatJoy. |
| 14 | Suggest a tagline and a simple landing-page hero section. |
| 15 | Create a brand concept for a new oat-milk startup called OatJoy. |
| 16 | Suggest a tagline and a simple landing-page hero section. |

**Sample interaction (first run):**

- **Turn 1** (3703 in / 667 out tokens) — user: *Create a brand concept for a new oat-milk startup called OatJoy.*
  - reply preview: Welcome to establishing OatJoy's powerful online presence! I'm here to guide you through defining your digital identity.  First, let's talk about choosing the perfect domain name for OatJoy. To help m…
- **Turn 2** (1863 in / 282 out tokens) — user: *Suggest a tagline and a simple landing-page hero section.*
  - reply preview: That's a great idea, and we'll definitely get to crafting a compelling tagline and a captivating landing page hero section for OatJoy! Those elements are crucial for engaging your audience.  However, …

Full transcripts: `data/transcript_marketing_agency.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).