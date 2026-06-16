# SKU Usage Summary — `fomc-research` (fomc_research)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `4056822423272554496`
- **Use case:** FOMC meeting financial-analysis report · **Complexity:** High
- **Unit:** 1 interaction = 2-turn conversation + memory-write (2.3 model calls avg), averaged over **35 interactions**. Deployed on Vertex AI Agent Engine (GEAP).
- **Focus:** measured **usage per SKU**; dollar cost is a secondary derived view (§6).

## 1. Architecture

```mermaid
graph TB
    User([User]) --> Root
    subgraph Engine["Vertex AI Agent Engine — fomc-research"]
        direction TB
        Root[root_agent]
        Root -->|1| R1[retrieve_meeting_data]
        Root -->|2| R2["extract_page_data<br/>(multimodal Gemini)"]
        Root -->|3| R3[research_agent]
        Root -->|4| R4[analysis_agent]
    end
    subgraph Core["Always-on Agent Platform SKUs"]
        direction LR
        Gemini[("Gemini 2.5 Flash<br/>per-token (text + multimodal)")]
        Runtime[("Agent Runtime<br/>vCPU + memory-sec")]
        Sess[("Sessions<br/>per event appended")]
        MB[("Memory Bank<br/>per memory + gen tokens")]
    end
    subgraph Extras["Agent-specific SKUs"]
        direction LR
        BQ[("BigQuery<br/>FOMC dataset queries")]
        GCS[("Cloud Storage<br/>PDF transcripts")]
        Search[("Google Search grounding<br/>capable, 0 measured")]
    end
    Engine -.-> Core
    R1 -.-> BQ
    R2 -.-> GCS
    R3 -.-> Search
```

Hierarchical multi-stage research pipeline. Root agent coordinates 4 sub-agents in sequence:
- `retrieve_meeting_data_agent` — fetches FOMC meeting metadata from **BigQuery**
- `extract_page_data_agent` — downloads + parses official PDF transcripts (pdfplumber + Cloud Storage), then runs **multimodal Gemini** on the PDFs
- `research_agent` — gathers contextual web background
- `analysis_agent` — synthesizes the final report on rates / inflation outlook

Multimodal: passes raw PDF documents to Gemini as inputs (not just text).

**Pattern:** Hierarchical + Sequential, multimodal pipeline

## 2. SKUs (products) consumed

Gemini tokens (text + multimodal); Agent Runtime (vCPU + memory); Sessions; Memory Bank; **BigQuery** (FOMC dataset queries); **Cloud Storage** (PDF downloads); Google Search grounding (research_agent, capable but didn't trigger in our prompts).

(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised via add_session_to_memory. Search grounding / Imagen used by the agent but usage not yet metered here — see §7.)

## 3. How usage was measured

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; **35 runs** for variability; 300s Monitoring settle; token usage from the model response (`usage_metadata`, exact), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package fomc_research --runs 35 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 35 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 1838 | 1306–2800 | Medium |
| Gemini output tokens (incl. thinking) | tokens | 479 | 188–949 | Medium |
| Model calls | calls | 2.3 | — | Medium |
| Agent Runtime — vCPU | vCPU-seconds | 30.1 | — | — |
| Agent Runtime — memory | GiB-seconds | 54.6 | — | — |
| Sessions | events appended | 4.8 | — | Medium |
| Memory Bank — generation | tokens | 2358 | — | — |
| Memory Bank — memories written | memories | 0.0 | — | — |
| Memory Bank — retrievals | reads | 0.0 | — | — |

_Memory retrievals = 0 for this workload: the agent either has no retrieval tool (the adk-sample agents) or answers directly without invoking recall (the support-FAQ chatbot — it IS `load_memory`-capable and recalls when asked, but its FAQ turns don't trigger it). Retrieval IS exercised by the returning-user runs of workflow-operator, autonomous-researcher, and multi-agent-orchestrator, and by `memory_assistant`._

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
| Gemini tokens | 0.0017 |
| Agent Runtime | 0.0009 |
| Memory Bank + Sessions | 0.0007 |
| Model Armor (derived: 2317 tok scanned @ $0.10/1M) | 0.000232 |
| **Total (measured SKUs)** | **0.0035** (range 0.0025–0.0048) |

## 7. Test workload & sample interactions

**35 interactions** (70 total user turns), fresh user_id per interaction. All interactions repeat the same 2-turn workload to isolate run-to-run variability.

**Workload (turn-by-turn):**

| Turn | User query |
|---|---|
| 1 | Summarize the key economic themes from the most recent FOMC meeting. |
| 2 | What was the FOMC's stance on inflation outlook and interest-rate trajectory? |

**Sample interaction (first run):**

- **Turn 1** (594 in / 319 out tokens) — user: *Summarize the key economic themes from the most recent FOMC meeting.*
  - reply preview: Please provide the date of the FOMC meeting you would like me to analyze.
- **Turn 2** (930 in / 241 out tokens) — user: *What was the FOMC's stance on inflation outlook and interest-rate trajectory?*
  - reply preview: Please provide the date of the FOMC meeting you would like me to analyze.

Full transcripts: `data/transcript_fomc_research.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).