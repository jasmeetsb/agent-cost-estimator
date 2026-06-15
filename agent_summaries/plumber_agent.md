# SKU Usage Summary — `plumber-data-engineering-assistant` (plumber_agent)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `2123652283223769088`
- **Use case:** Build/deploy data pipelines (Dataflow / Dataproc / dbt / GCS) · **Complexity:** High
- **Unit:** 1 interaction = 2-turn conversation + memory-write (4.0 model calls avg). Deployed on Vertex AI Agent Engine (GEAP).
- **Focus:** measured **usage per SKU**; dollar cost is a secondary derived view (§6).

## 1. Architecture

```mermaid
graph TB
    User([User]) --> Coord
    subgraph Engine["Vertex AI Agent Engine — plumber-agent"]
        direction TB
        Coord[plumber_agent]
        Coord --> DA[dataflow_agent]
        Coord --> DPA[dataproc_agent]
        Coord --> DPT[dataproc_template_agent]
        Coord --> DBT[dbt_agent]
        Coord --> GH[github_agent]
        Coord --> Mon[monitoring_agent]
    end
    subgraph Core["Always-on Agent Platform SKUs"]
        direction LR
        Gemini[("Gemini 2.5 Flash<br/>per-token")]
        Runtime[("Agent Runtime<br/>vCPU + memory-sec")]
        Sess[("Sessions<br/>per event appended")]
        MB[("Memory Bank<br/>per memory + gen tokens")]
    end
    subgraph Extras["Agent-specific SKUs (~6 GCP data products by intent)"]
        direction LR
        BQ[("BigQuery<br/>dbt execution")]
        GCS[("Cloud Storage<br/>SQL artifacts")]
        DF[("Dataflow<br/>pipeline jobs")]
        DP[("Dataproc<br/>cluster ops")]
        DFT[("Dataform<br/>templates")]
        CM[("Cloud Monitoring<br/>metric reads")]
        GHE[GitHub repo<br/>external]
    end
    Engine -.-> Core
    DBT -.-> BQ
    DBT -.-> GCS
    DA -.-> DF
    DPA -.-> DP
    DPT -.-> DFT
    Mon -.-> CM
    GH -.-> GHE
```

`plumber_agent` (root) routes data-engineering requests to **6 specialist sub-agents** — the deepest hierarchy in this corpus. Each sub-agent owns a distinct GCP data product:
- `dataflow_agent` — Dataflow pipeline design + job submission
- `dataproc_agent` — Dataproc cluster operations
- `dataproc_template_agent` — Dataproc template management
- `dbt_agent` — dbt model generation; writes SQL to **GCS** + executes against **BigQuery**
- `github_agent` — repo operations via GitPython (clone, branch, commit)
- `monitoring_agent` — reads Cloud Monitoring metrics for pipeline observability

By **intent**, this agent touches ~10–11 distinct GCP product SKUs (the broadest in our corpus). In practice, whether each SKU bills depends on whether the user prompt invokes that sub-agent against real resources.

**Pattern:** Hierarchical (deepest in corpus: coordinator + 6 specialists)

## 2. SKUs (products) consumed

Gemini tokens; Agent Runtime (vCPU + memory); Sessions; Memory Bank; **BigQuery** (dbt execution); **Cloud Storage** (SQL artifacts, GCS data IO); **Dataflow**, **Dataproc**, **Dataform** (sub-agent intent, only billed when actually invoked); **Cloud Monitoring** API reads.

(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised via add_session_to_memory. Search grounding / Imagen used by the agent but usage not yet metered here — see §7.)

## 3. How usage was measured

Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; **35 runs** for variability; 300s Monitoring settle; token usage from the model response (`usage_metadata`, exact), runtime + Memory Bank usage from Cloud Monitoring (per-engine).
Reproduce: `python scripts/exp_sample.py --package plumber_agent --runs 35 --settle 300`

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (avg over 35 runs), with run-to-run range and variability.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 13800 | 13475–14578 | Low |
| Gemini output tokens (incl. thinking) | tokens | 1958 | 829–3695 | Medium |
| Model calls | calls | 4.0 | — | Low |
| Agent Runtime — vCPU | vCPU-seconds | 104.1 | — | — |
| Agent Runtime — memory | GiB-seconds | 127.2 | — | — |
| Sessions | events appended | 8.0 | — | Low |
| Memory Bank — generation | tokens | 2853 | — | — |
| Memory Bank — memories written | memories | 0.6 | — | — |
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
| Gemini tokens | 0.0090 |
| Agent Runtime | 0.0028 |
| Memory Bank + Sessions | 0.0009 |
| **Total (measured SKUs)** | **0.0127** (range 0.0099–0.0172) |

## 7. Test workload & sample interactions

**35 interactions** (70 total user turns), fresh user_id per interaction. All interactions repeat the same 2-turn workload to isolate run-to-run variability.

**Workload (turn-by-turn):**

| Turn | User query |
|---|---|
| 1 | Design a Dataflow pipeline that reads daily CSV uploads from GCS and writes cleaned rows to BigQuery. |
| 2 | What would the dbt model look like to aggregate the daily data into weekly summaries? |

**Sample interaction (first run):**

- **Turn 1** (6759 in / 999 out tokens) — user: *Design a Dataflow pipeline that reads daily CSV uploads from GCS and writes cleaned rows to BigQuery.*
  - reply preview: Of course, I can help with that. To get started, I need a bit more information about your pipeline.  First, could you describe the data processing logic you'd like to implement? For example, what are …
- **Turn 2** (7309 in / 547 out tokens) — user: *What would the dbt model look like to aggregate the daily data into weekly summaries?*
  - reply preview: Of course. I can help with that. In order for me to generate the dbt model, I will need the source to target mapping file. You can provide it as a csv file or an image file with source and target colu…

Full transcripts: `data/transcript_plumber_agent.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).