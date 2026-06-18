# SKU Usage Summary — `multi-agent-orchestrator (archetype)` (multi_agent_orchestrator)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `2074724015787737088`
- **Use case:** Decompose-and-delegate orchestration · **Complexity:** Archetype: Multi-Agent Orchestrator / Moderate
- **Unit:** 1 interaction = 2–5-turn (varying) conversation + memory-write (18.9 model calls avg), averaged over **120 interactions**. Deployed on Vertex AI Agent Engine (GEAP).
- **Focus:** measured **usage per SKU**; dollar cost is a secondary derived view (§6).

## 1. Architecture

```mermaid
graph TB
    User([User]) --> Orch
    subgraph Engine["Agent Engine — multi_agent_orchestrator"]
        direction TB
        Orch["orchestrator_agent (Gemini 2.5 Flash)"]
        Orch -->|sub-agent| DS["data_specialist<br/>(query_metrics, fetch_records, corpus_search)"]
        Orch -->|sub-agent| AS["analysis_specialist<br/>(compute_stats, detect_trends)"]
        Orch -->|sub-agent| ACT["action_specialist<br/>(draft_summary, create_ticket, send_update)"]
    end
    subgraph Core["Always-on Agent Platform SKUs"]
        direction LR
        Gemini[("Gemini 2.5 Flash<br/>per-token (coordinator + 3 sub-agents)")]
        Runtime[("Agent Runtime<br/>vCPU + memory-sec")]
        Sess[("Sessions<br/>per event appended")]
        MB[("Memory Bank<br/>per memory + gen tokens")]
    end
    Engine -.-> Core
    DS -.->|prod| BQ[(BigQuery / RAG)]
```

Coordinator that decomposes a request and delegates to 3 specialist sub-agents — data_specialist (metrics / records / corpus), analysis_specialist (stats / trends), action_specialist (summary / ticket / notify) (archetype: Multi-Agent Orchestrator, Moderate). Fan-out-driven and the most expensive of the four: measured ~20,000 input tokens, ~12.5 model calls, ~25 session events per 2-turn interaction (coordinator + sub-agent token multiplication). Specialist tools are local stand-ins for BigQuery / RAG.

**Pattern:** Coordinator + 3 specialist sub-agents (agent-call fan-out)

## 2. SKUs (products) consumed

Gemini tokens (coordinator + sub-agents); Agent Runtime (vCPU + memory); Sessions; Memory Bank. (Specialist BigQuery/RAG calls mocked — would bill in production.)

(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised via add_session_to_memory. Search grounding / Imagen used by the agent but usage not yet metered here — see §7.)

## 3. How usage was measured

Deployed to Agent Engine; per run = 2–5-turn (varying) conversation in one session + add_session_to_memory; **120 runs** for variability; 300s Monitoring settle; token usage from the model response (`usage_metadata`, exact), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package multi_agent_orchestrator --runs 120 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 120 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 149080 | 6076–8349717 | Very high |
| Gemini output tokens (incl. thinking) | tokens | 6080 | 1140–106637 | Very high |
| Gemini tokens — master/coordinator | tokens | 26067 | 17% of I/O | — |
| Gemini tokens — sub-agents/tools | tokens | 129093 | 83% of I/O | — |
| Model calls | calls | 18.9 | — | Very high |
| Agent Runtime — vCPU | vCPU-seconds | 90.6 | — | — |
| Agent Runtime — memory | GiB-seconds | 100.3 | — | — |
| Sessions | events appended | 37.9 | — | Very high |
| Memory Bank — generation | tokens | 2793 | — | — |
| Memory Bank — memories written | memories | 1.2 | — | — |
| Memory Bank — retrievals | reads | 0.2 | — | — |
| Firestore — document writes | writes | 0.29 | — | — |
| Firestore — document reads | reads | 0.63 | — | — |
| Vertex AI Search (RAG) — queries | searches | 0.42 | — | — |


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
| Gemini tokens | 0.0599 |
| Agent Runtime | 0.0067 |
| Memory Bank + Sessions | 0.0104 |
| Firestore (35w/76r over 120 runs) | 0.0000001 |
| Vertex AI Search (RAG: 0.42 queries/intxn @ $1.50/1K) | 0.000625 |
| Memory Bank retrieval (0.20 memories retrieved/intxn @ $0.5/1K) | 0.000100 |
| Model Armor (derived: 155159 tok scanned @ $0.10/1M) | 0.015516 |
| **Total (measured SKUs)** | **0.0932** (range 0.0225–2.7886) |

## 7. Test workload & sample interactions

**85 interactions** (432 total user turns), fresh user_id per interaction. Interactions cycle **10 distinct conversation scenarios** of varying length (2-turn×16, 3-turn×16, 4-turn×32, 5-turn×16, 16-turn×1, 24-turn×1, 32-turn×2, 40-turn×1) — real-world interactions differ in length and topic, so this spreads coverage rather than repeating one script.

**Scenario 1** (2 turns):

| Turn | User query |
|---|---|
| 1 | Analyze last quarter's support-ticket volume trend and recommend actions. |
| 2 | Now draft an executive summary, open a follow-up ticket, and send an update to the ops channel. |

**Scenario 2** (3 turns):

| Turn | User query |
|---|---|
| 1 | Pull our key product metrics for the last 30 days and analyze the trend. |
| 2 | Fetch the related customer records. |
| 3 | Summarize the findings, create a ticket for the biggest issue, and notify the team. |

**Scenario 3** (5 turns):

| Turn | User query |
|---|---|
| 1 | Gather sales metrics and the internal playbook on churn. |
| 2 | Analyze the churn trend. |
| 3 | Cross-reference it with recent support tickets. |
| 4 | Draft an executive summary of what's driving churn. |
| 5 | Open a remediation ticket and send an update to the ops channel. |

**Scenario 4** (4 turns):

| Turn | User query |
|---|---|
| 1 | Look at activation-rate metrics for the last 30 days. |
| 2 | Compare against the prior period and detect the trend. |
| 3 | Check the onboarding playbook for known friction points. |
| 4 | Draft recommendations and open a ticket. |

**Scenario 5** (4 turns):

| Turn | User query |
|---|---|
| 1 | Pull weekly active accounts and ticket volume per 100 accounts. |
| 2 | Analyze whether support load is tracking growth. |
| 3 | Summarize the finding with the key numbers. |
| 4 | Notify the ops channel with the summary. |

**Scenario 6** (16 turns):

| Turn | User query |
|---|---|
| 1 | Analyze last quarter's support-ticket volume trend and recommend actions. |
| 2 | Now draft an executive summary, open a follow-up ticket, and send an update to the ops channel. |
| 3 | Analyze last quarter's support-ticket volume trend and recommend actions. |
| 4 | Now draft an executive summary, open a follow-up ticket, and send an update to the ops channel. |
| 5 | Analyze last quarter's support-ticket volume trend and recommend actions. |
| 6 | Now draft an executive summary, open a follow-up ticket, and send an update to the ops channel. |
| 7 | Analyze last quarter's support-ticket volume trend and recommend actions. |
| 8 | Now draft an executive summary, open a follow-up ticket, and send an update to the ops channel. |
| 9 | Analyze last quarter's support-ticket volume trend and recommend actions. |
| 10 | Now draft an executive summary, open a follow-up ticket, and send an update to the ops channel. |
| 11 | Analyze last quarter's support-ticket volume trend and recommend actions. |
| 12 | Now draft an executive summary, open a follow-up ticket, and send an update to the ops channel. |
| 13 | Analyze last quarter's support-ticket volume trend and recommend actions. |
| 14 | Now draft an executive summary, open a follow-up ticket, and send an update to the ops channel. |
| 15 | Analyze last quarter's support-ticket volume trend and recommend actions. |
| 16 | Now draft an executive summary, open a follow-up ticket, and send an update to the ops channel. |

**Scenario 7** (24 turns):

| Turn | User query |
|---|---|
| 1 | Pull our key product metrics for the last 30 days and analyze the trend. |
| 2 | Fetch the related customer records. |
| 3 | Summarize the findings, create a ticket for the biggest issue, and notify the team. |
| 4 | Pull our key product metrics for the last 30 days and analyze the trend. |
| 5 | Fetch the related customer records. |
| 6 | Summarize the findings, create a ticket for the biggest issue, and notify the team. |
| 7 | Pull our key product metrics for the last 30 days and analyze the trend. |
| 8 | Fetch the related customer records. |
| 9 | Summarize the findings, create a ticket for the biggest issue, and notify the team. |
| 10 | Pull our key product metrics for the last 30 days and analyze the trend. |
| 11 | Fetch the related customer records. |
| 12 | Summarize the findings, create a ticket for the biggest issue, and notify the team. |
| 13 | Pull our key product metrics for the last 30 days and analyze the trend. |
| 14 | Fetch the related customer records. |
| 15 | Summarize the findings, create a ticket for the biggest issue, and notify the team. |
| 16 | Pull our key product metrics for the last 30 days and analyze the trend. |
| 17 | Fetch the related customer records. |
| 18 | Summarize the findings, create a ticket for the biggest issue, and notify the team. |
| 19 | Pull our key product metrics for the last 30 days and analyze the trend. |
| 20 | Fetch the related customer records. |
| 21 | Summarize the findings, create a ticket for the biggest issue, and notify the team. |
| 22 | Pull our key product metrics for the last 30 days and analyze the trend. |
| 23 | Fetch the related customer records. |
| 24 | Summarize the findings, create a ticket for the biggest issue, and notify the team. |

**Scenario 8** (40 turns):

| Turn | User query |
|---|---|
| 1 | Gather sales metrics and the internal playbook on churn. |
| 2 | Analyze the churn trend. |
| 3 | Cross-reference it with recent support tickets. |
| 4 | Draft an executive summary of what's driving churn. |
| 5 | Open a remediation ticket and send an update to the ops channel. |
| 6 | Gather sales metrics and the internal playbook on churn. |
| 7 | Analyze the churn trend. |
| 8 | Cross-reference it with recent support tickets. |
| 9 | Draft an executive summary of what's driving churn. |
| 10 | Open a remediation ticket and send an update to the ops channel. |
| 11 | Gather sales metrics and the internal playbook on churn. |
| 12 | Analyze the churn trend. |
| 13 | Cross-reference it with recent support tickets. |
| 14 | Draft an executive summary of what's driving churn. |
| 15 | Open a remediation ticket and send an update to the ops channel. |
| 16 | Gather sales metrics and the internal playbook on churn. |
| 17 | Analyze the churn trend. |
| 18 | Cross-reference it with recent support tickets. |
| 19 | Draft an executive summary of what's driving churn. |
| 20 | Open a remediation ticket and send an update to the ops channel. |
| 21 | Gather sales metrics and the internal playbook on churn. |
| 22 | Analyze the churn trend. |
| 23 | Cross-reference it with recent support tickets. |
| 24 | Draft an executive summary of what's driving churn. |
| 25 | Open a remediation ticket and send an update to the ops channel. |
| 26 | Gather sales metrics and the internal playbook on churn. |
| 27 | Analyze the churn trend. |
| 28 | Cross-reference it with recent support tickets. |
| 29 | Draft an executive summary of what's driving churn. |
| 30 | Open a remediation ticket and send an update to the ops channel. |
| 31 | Gather sales metrics and the internal playbook on churn. |
| 32 | Analyze the churn trend. |
| 33 | Cross-reference it with recent support tickets. |
| 34 | Draft an executive summary of what's driving churn. |
| 35 | Open a remediation ticket and send an update to the ops channel. |
| 36 | Gather sales metrics and the internal playbook on churn. |
| 37 | Analyze the churn trend. |
| 38 | Cross-reference it with recent support tickets. |
| 39 | Draft an executive summary of what's driving churn. |
| 40 | Open a remediation ticket and send an update to the ops channel. |

**Scenario 9** (32 turns):

| Turn | User query |
|---|---|
| 1 | Look at activation-rate metrics for the last 30 days. |
| 2 | Compare against the prior period and detect the trend. |
| 3 | Check the onboarding playbook for known friction points. |
| 4 | Draft recommendations and open a ticket. |
| 5 | Look at activation-rate metrics for the last 30 days. |
| 6 | Compare against the prior period and detect the trend. |
| 7 | Check the onboarding playbook for known friction points. |
| 8 | Draft recommendations and open a ticket. |
| 9 | Look at activation-rate metrics for the last 30 days. |
| 10 | Compare against the prior period and detect the trend. |
| 11 | Check the onboarding playbook for known friction points. |
| 12 | Draft recommendations and open a ticket. |
| 13 | Look at activation-rate metrics for the last 30 days. |
| 14 | Compare against the prior period and detect the trend. |
| 15 | Check the onboarding playbook for known friction points. |
| 16 | Draft recommendations and open a ticket. |
| 17 | Look at activation-rate metrics for the last 30 days. |
| 18 | Compare against the prior period and detect the trend. |
| 19 | Check the onboarding playbook for known friction points. |
| 20 | Draft recommendations and open a ticket. |
| 21 | Look at activation-rate metrics for the last 30 days. |
| 22 | Compare against the prior period and detect the trend. |
| 23 | Check the onboarding playbook for known friction points. |
| 24 | Draft recommendations and open a ticket. |
| 25 | Look at activation-rate metrics for the last 30 days. |
| 26 | Compare against the prior period and detect the trend. |
| 27 | Check the onboarding playbook for known friction points. |
| 28 | Draft recommendations and open a ticket. |
| 29 | Look at activation-rate metrics for the last 30 days. |
| 30 | Compare against the prior period and detect the trend. |
| 31 | Check the onboarding playbook for known friction points. |
| 32 | Draft recommendations and open a ticket. |

**Scenario 10** (32 turns):

| Turn | User query |
|---|---|
| 1 | Pull weekly active accounts and ticket volume per 100 accounts. |
| 2 | Analyze whether support load is tracking growth. |
| 3 | Summarize the finding with the key numbers. |
| 4 | Notify the ops channel with the summary. |
| 5 | Pull weekly active accounts and ticket volume per 100 accounts. |
| 6 | Analyze whether support load is tracking growth. |
| 7 | Summarize the finding with the key numbers. |
| 8 | Notify the ops channel with the summary. |
| 9 | Pull weekly active accounts and ticket volume per 100 accounts. |
| 10 | Analyze whether support load is tracking growth. |
| 11 | Summarize the finding with the key numbers. |
| 12 | Notify the ops channel with the summary. |
| 13 | Pull weekly active accounts and ticket volume per 100 accounts. |
| 14 | Analyze whether support load is tracking growth. |
| 15 | Summarize the finding with the key numbers. |
| 16 | Notify the ops channel with the summary. |
| 17 | Pull weekly active accounts and ticket volume per 100 accounts. |
| 18 | Analyze whether support load is tracking growth. |
| 19 | Summarize the finding with the key numbers. |
| 20 | Notify the ops channel with the summary. |
| 21 | Pull weekly active accounts and ticket volume per 100 accounts. |
| 22 | Analyze whether support load is tracking growth. |
| 23 | Summarize the finding with the key numbers. |
| 24 | Notify the ops channel with the summary. |
| 25 | Pull weekly active accounts and ticket volume per 100 accounts. |
| 26 | Analyze whether support load is tracking growth. |
| 27 | Summarize the finding with the key numbers. |
| 28 | Notify the ops channel with the summary. |
| 29 | Pull weekly active accounts and ticket volume per 100 accounts. |
| 30 | Analyze whether support load is tracking growth. |
| 31 | Summarize the finding with the key numbers. |
| 32 | Notify the ops channel with the summary. |

**Sample interaction (first run):**

- **Turn 1** (11967 in / 6341 out tokens) — user: *Analyze last quarter's support-ticket volume trend and recommend actions.*
  - reply preview: I am unable to provide a consolidated answer with the findings, analysis, and recommended actions at this time. The data_specialist and analysis_specialist agents did not return specific content for m…
- **Turn 2** (11282 in / 1341 out tokens) — user: *Now draft an executive summary, open a follow-up ticket, and send an update to the ops channel.*
  - reply preview: I have drafted an executive summary, created a follow-up ticket, and sent an update to the ops channel regarding the failure to analyze the support-ticket volume trend.  **Executive Summary:** Executi…

Full transcripts: `data/transcript_multi_agent_orchestrator.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).