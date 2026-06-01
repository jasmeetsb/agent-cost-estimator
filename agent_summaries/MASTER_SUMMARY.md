# Master Summary — Implemented Agent Architectures

**Living index** of every agent architecture deployed in this project, the SKUs each consumes, measured per-interaction usage, and derived list-price cost. Update this doc whenever a new agent is added. Per-agent details (architecture, methodology, full usage distribution + variability) live in linked files below.

## Executive summary

- **5 agents deployed** on Vertex AI Agent Engine (Gemini Enterprise Agent Platform).
- **Cost spans $0.0111–$0.0336 per interaction** at catalog list price (3× spread), driven by architecture (sub-agent fan-out, analysis depth) more than the prompt.
- **Architecture matters more than prompt:** financial-advisor consumes ~7× more input tokens than the lightest agent and is the only **runtime-dominated** one.
- **Run-to-run variability is real:** identical task can swing total cost ~2× (output/thinking tokens are the noisy SKU).
- **Memory + session SKUs are a meaningful slice** even when memories are never read back — always present for any session-persisted agent.
- **Collectors built and validated** for tokens, vCPU/memory, sessions, Memory Bank, Search grounding, and Imagen. Still uncaptured: Cloud Trace, Logging, Storage.

## Agents at a glance

- **financial-advisor** — Stock analysis & trading-strategy advisor. Hierarchical: coordinator + 4 AgentTool specialists (data, trading, execution, risk). Heaviest input-token consumer; runtime-dominated. → [details](financial_advisor.md)
- **memory_assistant** — Personal assistant with long-term cross-session memory. Coordinator + 2 sub-agents + Memory Bank (write+read). Exercises the most Agent Platform features in this corpus. → [details](memory_assistant.md)
- **academic-research** — Academic literature discovery & analysis. Coordinator + AgentTool websearch + new-research specialists. → [details](academic_research.md)
- **blog-writer** — Multi-agent technical blog authoring. Coordinator + 4 sub-agents (outline, draft, edit, social) + HITL refinement. → [details](blogger_agent.md)
- **marketing-agency** — End-to-end branding suite: domain, website, marketing, logo (Imagen) creators wrapped as AgentTools under one coordinator. → [details](marketing_agency.md)

## 1. SKU usage per interaction — model & compute (PRIMARY)

| Agent | Input tokens (range) | Output tokens (range) | Model calls | vCPU-seconds | GiB-seconds |
|---|---|---|---|---|---|
| [financial-advisor](financial_advisor.md) | 21679 (13333–34507) | 2410 (1430–2942) | 3.3 | 720.8 | 919 |
| [memory_assistant](memory_assistant.md) | 3398 (2552–4001) | 1605 (752–3150) | 5.8 | 39.0 | 560 |
| [academic-research](academic_research.md) | 3367 (2233–5564) | 2699 (1158–5762) | 2.0 | 166.8 | 560 |
| [blog-writer](blogger_agent.md) | 3027 (2543–3415) | 3039 (2527–3564) | 2.0 | 164.0 | 640 |
| [marketing-agency](marketing_agency.md) | 2991 (1965–3609) | 1345 (1152–1638) | 2.7 | 164.0 | 640 |

## 2. SKU usage per interaction — Agent Platform features (PRIMARY)

| Agent | Session events | Memory-gen tokens | Memories written | Memory retrievals |
|---|---|---|---|---|
| [financial-advisor](financial_advisor.md) | 6.7 | 3177 | 1.3 | 0.0 |
| [memory_assistant](memory_assistant.md) | 11.5 | 2493 | 3.2 | 2.5 |
| [academic-research](academic_research.md) | 4.0 | 2732 | 0.0 | 0.0 |
| [blog-writer](blogger_agent.md) | 4.0 | 3959 | 1.0 | 0.0 |
| [marketing-agency](marketing_agency.md) | 5.3 | 2661 | 0.7 | 0.0 |

_Memory retrievals are ~0 for the sample agents (no preload_memory tool); memory_assistant retrieves because cross-session recall is its purpose._

## 2b. Grounding & image generation

Collectors: **`extract_grounding_from_events`** (per-interaction, attributable — validated with a separate `grounded_news` agent) and **`collect_imagen_usage`** (Cloud Monitoring `model_invocation_count` for imagen models — validated with 7 captured invocations). Measured 0 for the agents below: their 2-turn workloads did not trigger Search or image generation; the collectors themselves are validated working.

| Agent | Grounded prompts | Images generated |
|---|---|---|
| [financial-advisor](financial_advisor.md) | 0 | 0 |
| [memory_assistant](memory_assistant.md) | 0 | 0 |
| [academic-research](academic_research.md) | 0 | 0 |
| [blog-writer](blogger_agent.md) | 0 | 0 |
| [marketing-agency](marketing_agency.md) | 0 | 0 |

_Would bill ~$0.035 per grounded prompt (Gemini 2.x) and ~$0.04 per image (Imagen) if triggered._

## 3. SKU presence matrix (which agents touch which SKUs)

| Agent | Gemini tokens | Agent Runtime | Sessions | Memory Bank | Search grounding | Image gen |
|---|---|---|---|---|---|---|
| [financial-advisor](financial_advisor.md) | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — |
| [memory_assistant](memory_assistant.md) | ✓ | ✓ | ✓ | ✓ (write+read) | — | — |
| [academic-research](academic_research.md) | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — |
| [blog-writer](blogger_agent.md) | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — |
| [marketing-agency](marketing_agency.md) | ✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | capable, 0 measured |

## 4. Secondary: derived cost per interaction (usage × catalog list price)

Reference only — list price, not actual billed. The usage tables above are the deliverable.

| Agent | Gemini $ | Runtime $ | Mem+Sess $ | Total $ (range) | Cost variability |
|---|---|---|---|---|---|
| [financial-advisor](financial_advisor.md) | 0.0125 | 0.0196 | 0.0015 | 0.0336 (0.0298–0.0385) | Medium |
| [memory_assistant](memory_assistant.md) | 0.0050 | 0.0035 | 0.0080 | 0.0165 (0.0144–0.0206) | High |
| [blog-writer](blogger_agent.md) | 0.0085 | 0.0055 | 0.0015 | 0.0156 (0.0141–0.0170) | Low |
| [academic-research](academic_research.md) | 0.0078 | 0.0054 | 0.0012 | 0.0144 (0.0101–0.0226) | Very high |
| [marketing-agency](marketing_agency.md) | 0.0043 | 0.0055 | 0.0012 | 0.0111 (0.0102–0.0119) | Medium |

## 5. Usage-pattern observations

1. **Input-token usage is the biggest differentiator** — financial-advisor consumes ~21679 input tokens/interaction vs ~2991 for the lightest, a 7× spread driven by depth of multi-specialist analysis.
2. **vCPU-seconds track analysis depth**, not just call count — the heaviest agent burns far more compute per interaction.
3. **Output-token usage is the most variable SKU** run-to-run (the model varies how much it reasons), so token usage should be reported as a range, not a single number.
4. **Memory generation + session events are consumed even when memories are never read back** — a real SKU footprint for any session-persisted agent.
5. **Grounding and Imagen collectors are validated** (separate validation runs registered non-zero usage). For the 5 agents above the workloads simply didn't trigger them.

## Per-agent detail docs

- [financial-advisor](financial_advisor.md) — Stock analysis & trading-strategy advisor.
- [memory_assistant](memory_assistant.md) — Personal assistant with long-term cross-session memory.
- [academic-research](academic_research.md) — Academic literature discovery & analysis.
- [blog-writer](blogger_agent.md) — Multi-agent technical blog authoring.
- [marketing-agency](marketing_agency.md) — End-to-end branding suite: domain, website, marketing, logo (Imagen) creators wrapped as AgentTools under one coordinator.

## Method & reproducibility

Per agent: `python scripts/exp_sample.py --package <pkg> --runs 3 --settle 300`. Token usage from model responses (exact); vCPU/GiB-seconds + Memory Bank usage from Cloud Monitoring (per-engine); grounding from event `grounding_metadata` (per-interaction); Imagen from Monitoring `model_invocation_count` (model_user_id contains 'imagen'). Prices from the live Cloud Billing Catalog. Master summary regenerated by `scripts/build_summaries.py`.

_See also: [COMBINED_SKU_USAGE_REPORT.md](../COMBINED_SKU_USAGE_REPORT.md) (repo-root version of §1–§5 above), [GEAP_COMPONENTS.md](../GEAP_COMPONENTS.md), [COST_DATA_COLLECTION_PROCESS.md](../COST_DATA_COLLECTION_PROCESS.md), [PROJECT_RUNBOOK.md](../PROJECT_RUNBOOK.md)._