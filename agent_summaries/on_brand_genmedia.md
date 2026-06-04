# SKU Usage Summary — `on-brand-genmedia` (on_brand_genmedia)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `654352904794144768`
- **Use case:** Brand-compliant image generation with quality gate · **Complexity:** High
- **Unit:** 1 interaction = 2-turn conversation + memory-write (17.2 model calls avg). Deployed on Vertex AI Agent Engine (GEAP).
- **Focus:** measured **usage per SKU**; dollar cost is a secondary derived view (§6).

## 1. Architecture

```mermaid
graph TB
    User([User]) --> Prompt
    subgraph Engine["Vertex AI Agent Engine — on-brand-genmedia"]
        direction TB
        Prompt[prompt_agent]
        Img[image_agent]
        Score[scoring_agent]
        Check{"checker_agent<br/>score >= 45?"}
        Prompt --> Img --> Score --> Check
        Check -->|no, loop up to 2x| Prompt
        Check -->|yes| Out([final image])
    end
    subgraph Core["Always-on Agent Platform SKUs"]
        direction LR
        Gemini[("Gemini 2.5 Flash<br/>per-token (heavy fan-out)")]
        Runtime[("Agent Runtime<br/>vCPU + memory-sec")]
        Sess[("Sessions<br/>per event appended")]
        MB[("Memory Bank<br/>per memory + gen tokens")]
    end
    subgraph Extras["Agent-specific SKUs"]
        direction LR
        Imagen[("gemini-2.5-flash-image<br/>per image (~$0.04)")]
        GCS[("Cloud Storage<br/>image artifacts")]
    end
    Engine -.-> Core
    Img -.-> Imagen
    Img -.-> GCS
```

Iterative image generation with a scoring gate. Sub-agents:
- `prompt_agent` — refines the image-generation prompt from user intent
- `image_agent` — generates the image via `gemini-2.5-flash-image` (Imagen-family genmedia)
- `scoring_agent` — scores the image against brand guidelines (0–100)
- `checker_agent` — gate: if score < `SCORE_THRESHOLD` (default 45), loop back to prompt refinement; up to `MAX_ITERATIONS` (default 2)

Multiple Imagen calls per interaction make this the costliest agent in our corpus by image-gen SKU + model tokens combined.

**Pattern:** Loop + Hierarchical (iterate-until-on-brand)

## 2. SKUs (products) consumed

Gemini tokens (heavy fan-out across iterations); Agent Runtime (vCPU + memory); Sessions; Memory Bank; **Imagen / gemini-2.5-flash-image** (per-image SKU, multiple per interaction); Cloud Storage (image artifacts).

(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised via add_session_to_memory. Search grounding / Imagen used by the agent but usage not yet metered here — see §7.)

## 3. How usage was measured

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; **35 runs** for variability; 300s Monitoring settle; token usage from the model response (`usage_metadata`, exact), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package on_brand_genmedia --runs 35 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 35 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 83460 | 24021–198338 | High |
| Gemini output tokens (incl. thinking) | tokens | 7349 | 2732–13376 | Medium |
| Model calls | calls | 17.2 | — | Medium |
| Agent Runtime — vCPU | vCPU-seconds | 322.7 | — | — |
| Agent Runtime — memory | GiB-seconds | 328.9 | — | — |
| Sessions | events appended | 31.6 | — | Medium |
| Memory Bank — generation | tokens | 4191 | — | — |
| Memory Bank — memories written | memories | 0.5 | — | — |
| Memory Bank — retrievals | reads | 0.0 | — | — |

_Memory retrievals = 0: this agent has no preload_memory tool — it writes memories from the session but doesn't read them back._

## 5. Grounding & media usage (now collected)

- **Google Search grounding:** 0 grounded web-search requests measured (Cloud Monitoring, project-wide). The agent *can* ground on Search but this workload did not trigger it; would bill ~$0.035/request if used.
- **Image generation (Imagen):** 27 images measured (from response events). Would bill ~$0.04/image if used.

## 5b. Caveats on usage capture

- vCPU/GiB-seconds are amortized over the measurement window (utilization-dependent).
- Memory storage (stored-memory count over time) is export-only.
- Grounding count is project-wide (no per-engine label); image count is event-based.
- Still uncaptured: Cloud Trace, Logging, Storage.

## 6. Secondary: derived cost (usage × catalog list price)

Provided for reference only. List price, not actual billed; **usage above is the primary output.**

| SKU | $/interaction |
|---|---|
| Gemini tokens | 0.0434 |
| Agent Runtime | 0.0086 |
| Memory Bank + Sessions | 0.0015 |
| Imagen (image generation) | 0.0309 |
| **Total (measured SKUs)** | **0.0843** (range 0.0549–0.1254) |

## 7. Test workload & sample interaction

Total user turns recorded: **70** (≈ 35 interactions × 2 turns each, fresh user_id per interaction; identical prompts repeat to isolate run-to-run variability).

**Repeated workload (turn-by-turn):**

| Turn | User query |
|---|---|
| 1 | Generate a brand-aligned hero image for a coffee shop's grand opening promotion. |
| 2 | Now create a variation sized for an Instagram banner. |

**Sample interaction (the first run):**

- **Turn 1** (29318 in / 5592 out tokens) — user: *Generate a brand-aligned hero image for a coffee shop's grand opening promotion.*
  - reply preview: Checking for relevant digital assets...  Fetching guidelines and rules for media generation...  Generating the prompt... PROMPT: A premium, high-quality cinematic photograph of a modern and inviting c…
- **Turn 2** (51942 in / 1820 out tokens) — user: *Now create a variation sized for an Instagram banner.*
  - reply preview: Checking for relevant digital assets...  Fetching guidelines and rules for media generation...  Generating the prompt... PROMPT: A premium, high-quality cinematic photograph for an Instagram banner, d…

Full transcripts: `data/transcript_on_brand_genmedia.jsonl` (one JSON record per turn; contains full input, output_text, every tool call+response, and per-step usage). **Not committed** (data/ is gitignored — runtime artifact).