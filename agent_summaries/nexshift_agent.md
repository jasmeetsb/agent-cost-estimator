# SKU Usage Summary — `nexshift-agent` (nexshift_agent)

- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `6362665432486248448`
- **Use case:** AI nurse rostering & scheduling optimizer · **Complexity:** High
- **Unit:** 1 interaction = a 2-turn conversation in a single session, followed by a memory-write step (0.0 model calls on average). All numbers below are averaged over **35 interactions**. Deployed on Vertex AI Agent Engine.
- **Focus:** measured **usage per SKU**; dollar cost is a secondary derived view (§6).

## 1. Architecture

```mermaid
graph TB
    User([User]) <-->|HITL| Coord
    subgraph Engine["Vertex AI Agent Engine — nexshift-agent"]
        direction TB
        Coord[RosteringCoordinator]
        Coord --> CG[context_gatherer]
        Coord --> Cfg[config]
        Coord --> Cmp[compliance]
        Coord --> SV["solver_agent<br/>(OR-Tools CP-SAT)"]
        Coord --> Emp[empathy]
        Coord --> Prs[presenter]
    end
    subgraph Core["Always-on Agent Platform SKUs"]
        direction LR
        Gemini[("Gemini 2.5 Flash<br/>per-token")]
        Runtime[("Agent Runtime<br/>vCPU + memory-sec<br/>(heavy on hard solves)")]
        Sess[("Sessions<br/>per event appended")]
        MB[("Memory Bank<br/>per memory + gen tokens")]
    end
    Engine -.-> Core
```

`RosteringCoordinator` (root) orchestrates **7 specialist sub-agents** across the rostering flow:
- `context_gatherer` — collects shift requirements + constraints
- `config` — validates roster configuration
- `compliance` — checks labor-law & policy constraints
- `solver_agent` — runs the OR-Tools CP-SAT constraint solver (compute-heavy)
- `empathy` — surfaces employee concerns / exceptions
- `presenter` — formats the final roster for output

**31 tools** total across the sub-agents — a very broad tool surface. The OR-Tools constraint solve runs inside Agent Runtime, so vCPU cost can spike for harder rosters. The solver expects structured shift/constraint input; free-form natural-language prompts do not exercise the full solver pipeline.

**Pattern:** Hierarchical + Sequential + Parallel + HITL (4 patterns)

## 2. SKUs (products) consumed

Gemini tokens; Agent Runtime (vCPU/memory, **compute-heavy from CP-SAT solver**); Sessions; Memory Bank.

(Sessions and Agent Runtime are billed automatically by Agent Engine; Memory Bank generation is triggered by `add_session_to_memory`. Where the agent uses Google Search grounding or image generation, that usage is reported in §5.)

## 3. How usage was measured

Each interaction = a 2-turn conversation in one session, followed by `add_session_to_memory` (which triggers Memory Bank generation). We ran **35 interactions** to capture run-to-run variability, waited 300s for Cloud Monitoring metrics to settle, then read usage: token counts come from the model's per-response `usage_metadata` (exact — this agent makes no AgentTool-hidden sub-agent calls, so the response stream already sees every model call); runtime (vCPU / memory-seconds) and Memory Bank usage come from Cloud Monitoring (per-engine metrics).

## 4. SKU usage per interaction (PRIMARY)

Measured usage quantities per interaction (averaged over 35 interactions), with the min–max range and variability label across interactions.

| SKU dimension | Unit | Typical | Range | Variability |
|---|---|---|---|---|
| Gemini input tokens | tokens | 0 | 0–0 | Low |
| Gemini output tokens (incl. thinking) | tokens | 0 | 0–0 | Low |
| Model calls | calls | 0.0 | — | Low |
| Agent Runtime — vCPU | vCPU-seconds | 12.8 | — | — |
| Agent Runtime — memory | GiB-seconds | 37.1 | — | — |
| Sessions | events appended | 2.0 | — | Low |
| Memory Bank — generation | tokens | 2390 | — | — |
| Memory Bank — memories written | memories | 1.0 | — | — |
| Memory Bank — retrievals | reads | 0.0 | — | — |

_Memory retrievals = 0 for this workload. `load_memory` returns memories only when (a) the agent invokes it and (b) earlier sessions generated **user-centric** memories worth recalling. Here it is 0 — the agent has no retrieval tool, or doesn't call it (support-FAQ chatbot answers directly), or calls it but its sessions produce no user-centric memories to retrieve (e.g., academic-research: topic Q&A, not facts about the user). The retrieval SKU IS exercised by financial-advisor, marketing-agency, blog-writer, workflow-operator, autonomous-researcher, and multi-agent-orchestrator (returning-user runs) + `memory_assistant`._


## 5. Grounding & media usage

- **Google Search grounding:** none in this workload — the agent does not call `google_search`. (Would bill ~$14 / 1K grounded query-turns if used.)
- **Image generation (Imagen):** none in this workload. (Would bill ~$0.04 / image if used.)

## 5b. Caveats on usage capture

- **Agent Runtime (vCPU / GiB-seconds)** is the engine's allocated compute amortized over the measurement window, so it depends on utilization (queries per hour). Treat it as an upper bound, not actual billed instance-time.
- **Memory storage** (the number of stored memories accruing over time) is not captured here — it is only available from the billing export.
- **Grounding** is counted from the agent's tool calls (Cloud Monitoring's grounding metric is project-wide, with no per-engine label); **Imagen** image counts come from response events.
- **Not yet captured:** Cloud Trace, Cloud Logging, Cloud Storage.

## 6. Secondary: derived cost (usage × catalog list price)

Provided for reference only. List price, not actual billed; **usage above is the primary output.**

| SKU | $/interaction |
|---|---|
| Gemini tokens | 0.0000 |
| Agent Runtime | 0.0004 |
| Memory Bank + Sessions | 0.0007 |
| Model Armor (derived: 0 tok scanned @ $0.10/1M) | 0.000000 |
| **Total (measured SKUs)** | **0.0011** (range 0.0011–0.0011) |

## 7. Test workload & sample interactions

Each interaction repeated the same 2-turn workload shown below, to isolate run-to-run variability; each used a fresh user id.

**Workload (turn-by-turn):**

| Turn | User query |
|---|---|
| 1 | Generate a 1-week nurse roster for 5 nurses across 3 daily shifts; minimum 2 nurses per shift. |
| 2 | Now adjust the roster if 1 nurse is unavailable Tuesday morning and another wants Friday off. |

**Sample interaction (first run):**

- **Turn 1** (0 in / 0 out tokens) — user: *Generate a 1-week nurse roster for 5 nurses across 3 daily shifts; minimum 2 nurses per shift.*
  - reply preview: 
- **Turn 2** (0 in / 0 out tokens) — user: *Now adjust the roster if 1 nurse is unavailable Tuesday morning and another wants Friday off.*
  - reply preview: 

Full transcripts: `data/transcript_nexshift_agent.jsonl` (one JSON record per turn; full input, output_text, every tool call+response, per-step usage). **Not committed** (data/ is gitignored — runtime artifact).