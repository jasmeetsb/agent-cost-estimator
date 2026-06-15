# SKU Usage Summary — `conversational-chatbot (archetype)` (conversational_chatbot)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `7861427324493758464`
- **Use case:** Customer-support Q&A chatbot · **Complexity:** Archetype: Conversational Chatbot / Moderate
- **Unit:** 1 interaction = 2-turn conversation + memory-write (4.0 model calls avg). Deployed on Vertex AI Agent Engine (GEAP).
- **Focus:** measured **usage per SKU**; dollar cost is a secondary derived view (§6).

## 1. Architecture

```mermaid
graph TB
    User([User]) <--> Coord
    subgraph Engine["Agent Engine — conversational_chatbot"]
        direction TB
        Coord["chatbot_agent (Gemini 2.5 Flash)"]
        Coord -->|tool| FAQ[faq_lookup]
        Coord -->|tool| KB[kb_search]
        Coord -->|tool| PM[preload_memory]
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

Single user-facing support agent (archetype: Conversational Chatbot, Moderate). Light tool use — `faq_lookup` + `kb_search` (stand-ins for a BigQuery/KB lookup) — and `preload_memory` for returning-user personalization. Volume-driven archetype: cheap model, short turns. Measured ~4 model calls / ~8 session events per 2-turn interaction.

**Pattern:** Single agent + light tools + Memory Bank

## 2. SKUs (products) consumed

Gemini tokens; Agent Runtime (vCPU + memory); Sessions; Memory Bank. (BigQuery/KB lookup mocked locally — would bill BigQuery in production.)

(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised via add_session_to_memory. Search grounding / Imagen used by the agent but usage not yet metered here — see §7.)

## 3. How usage was measured

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; **35 runs** for variability; 300s Monitoring settle; token usage from the model response (`usage_metadata`, exact), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package conversational_chatbot --runs 35 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 35 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 1420 | 920–1751 | Low |
| Gemini output tokens (incl. thinking) | tokens | 363 | 208–617 | Medium |
| Model calls | calls | 4.0 | — | Low |
| Agent Runtime — vCPU | vCPU-seconds | 52.1 | — | — |
| Agent Runtime — memory | GiB-seconds | 109.8 | — | — |
| Sessions | events appended | 8.0 | — | Low |
| Memory Bank — generation | tokens | 2429 | — | — |
| Memory Bank — memories written | memories | 0.0 | — | — |
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
| Gemini tokens | 0.0013 |
| Agent Runtime | 0.0015 |
| Memory Bank + Sessions | 0.0008 |
| **Total (measured SKUs)** | **0.0036** (range 0.0032–0.0044) |

## 7. Test workload & sample interaction

Total user turns recorded: **70** (≈ 35 interactions × 2 turns each, fresh user_id per interaction; identical prompts repeat to isolate run-to-run variability).

**Repeated workload (turn-by-turn):**

| Turn | User query |
|---|---|
| 1 | Hi, how do I reset my password and what are your support hours? |
| 2 | Also, what are your pricing tiers and do you support SSO? |

**Sample interaction (the first run):**

- **Turn 1** (451 in / 231 out tokens) — user: *Hi, how do I reset my password and what are your support hours?*
  - reply preview: I can't find specific information on how to reset your password or our exact support hours at the moment. Generally, you can reset your password on the login page by clicking "Forgot password" or "Res…
- **Turn 2** (1044 in / 252 out tokens) — user: *Also, what are your pricing tiers and do you support SSO?*
  - reply preview: We offer SSO (SAML/OIDC) on our Enterprise plan. Please contact your account manager for more details.  I couldn't find specific information about our pricing tiers. Would you like me to connect you w…

Full transcripts: `data/transcript_conversational_chatbot.jsonl` (one JSON record per turn; contains full input, output_text, every tool call+response, and per-step usage). **Not committed** (data/ is gitignored — runtime artifact).