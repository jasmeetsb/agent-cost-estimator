# SKU Usage Summary — `conversational-chatbot (archetype)` (conversational_chatbot)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `6054217236522991616`
- **Use case:** Customer-support Q&A chatbot · **Complexity:** Archetype: Conversational Chatbot / Moderate
- **Unit:** 1 interaction = 2–5-turn (varying) conversation + memory-write (7.5 model calls avg), averaged over **80 interactions**. Deployed on Vertex AI Agent Engine (GEAP).
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

Deployed to Agent Engine; per run = 2–5-turn (varying) conversation in one session + add_session_to_memory; **80 runs** for variability; 300s Monitoring settle; token usage from the model response (`usage_metadata`, exact), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package conversational_chatbot --runs 80 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 80 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 6034 | 2030–17874 | High |
| Gemini output tokens (incl. thinking) | tokens | 669 | 188–1860 | High |
| Model calls | calls | 7.5 | — | Medium |
| Agent Runtime — vCPU | vCPU-seconds | 28.9 | — | — |
| Agent Runtime — memory | GiB-seconds | 57.1 | — | — |
| Sessions | events appended | 14.9 | — | Medium |
| Memory Bank — generation | tokens | 0 | — | — |
| Memory Bank — memories written | memories | 0.0 | — | — |
| Memory Bank — retrievals | reads | 0.0 | — | — |
| Firestore — document writes | writes | 0.03 | — | — |
| Firestore — document reads | reads | 0.00 | — | — |
| Vertex AI Search (RAG) — queries | searches | 2.24 | — | — |

_Memory retrievals = 0: this agent has no preload_memory tool — it writes memories from the session but doesn't read them back._

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
| Gemini tokens | 0.0035 |
| Agent Runtime | 0.0019 |
| Memory Bank + Sessions | 0.0037 |
| Firestore (2w/0r over 80 runs) | 0.0000000 |
| Vertex AI Search (RAG: 2.24 queries/intxn @ $1.50/1K) | 0.003356 |
| Model Armor (derived: 6703 tok scanned @ $0.10/1M) | 0.000670 |
| **Total (measured SKUs)** | **0.0131** (range 0.0067–0.0152) |

## 7. Test workload & sample interactions

**80 interactions** (288 total user turns), fresh user_id per interaction. Interactions cycle **5 distinct conversation scenarios** of varying length (2-turn×16, 3-turn×16, 4-turn×32, 5-turn×16) — real-world interactions differ in length and topic, so this spreads coverage rather than repeating one script.

**Scenario 1** (2 turns):

| Turn | User query |
|---|---|
| 1 | How do I reset my password, and what are your support hours? |
| 2 | Also, what are your pricing tiers and do you support SSO? |

**Scenario 2** (3 turns):

| Turn | User query |
|---|---|
| 1 | I'd like a refund on my last order. |
| 2 | How long does that take to process? |
| 3 | Can it go to a different card than I paid with? |

**Scenario 3** (4 turns):

| Turn | User query |
|---|---|
| 1 | Do you integrate with Slack? |
| 2 | What about exporting my data? |
| 3 | Is data export on the Pro tier or Enterprise only? |
| 4 | Okay — how do I upgrade my plan? |

**Scenario 4** (4 turns):

| Turn | User query |
|---|---|
| 1 | My shipment hasn't arrived yet. |
| 2 | It's order ORD-1002. What's the ETA? |
| 3 | Can you switch it to express shipping? |
| 4 | Will I be charged extra for that? |

**Scenario 5** (5 turns):

| Turn | User query |
|---|---|
| 1 | I'm new — can you walk me through setting up my account? |
| 2 | How do I invite my team? |
| 3 | What roles can I assign them? |
| 4 | Do you support SSO for the team? |
| 5 | And what does all that cost on the Pro tier? |

**Sample interaction (first run):**

- **Turn 1** (963 in / 231 out tokens) — user: *How do I reset my password, and what are your support hours?*
  - reply preview: I don't have information on how to reset your password or our support hours in my frequently asked questions. Would you like me to try and find this information elsewhere, or escalate your request to …
- **Turn 2** (1743 in / 525 out tokens) — user: *Also, what are your pricing tiers and do you support SSO?*
  - reply preview: We have a free Starter tier (1 user, community support). Our Pro tier is $29/user/month and includes API access but not SSO. The Enterprise tier is custom-priced and includes SSO, SLA, and dedicated s…

Full transcripts: `data/transcript_conversational_chatbot.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).