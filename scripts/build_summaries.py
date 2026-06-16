"""Generate per-agent SKU-usage summaries (markdown) + a combined report.

PURPOSE: estimate **usage per SKU** for different agent deployments. Usage
quantities (tokens, vCPU-seconds, GiB-seconds, session events, memory ops) are
the primary output. Dollar cost is a SECONDARY, derived view (usage x catalog
list price) — this is NOT an expense report or a cost-optimization deck.

Reads data/cost_report_<package>.json for the deployed agents and writes
agent_summaries/<package>.md each, then COMBINED_SKU_USAGE_REPORT.md.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent_cost_estimator import load_or_build

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
OUT = REPO / "agent_summaries"
OUT.mkdir(exist_ok=True)

PB = load_or_build("gemini-2.5-flash")
VCPU_RATE = PB.runtime_vcpu_core_sec_usd or 2.4e-5
MEM_RATE = PB.runtime_mem_gib_sec_usd or 2.5e-6

META = {
    "financial_advisor": {
        "title": "financial-advisor", "use_case": "Stock analysis & trading-strategy advisor",
        "complexity": "High", "pattern": "Hierarchical (coordinator + 4 AgentTool specialists)",
        "diagram": """graph TB
    User([User]) --> Coord
    subgraph Engine["Vertex AI Agent Engine — financial_advisor"]
        direction TB
        Coord[financial_coordinator]
        Coord -->|AgentTool| DA[data_analyst]
        Coord -->|AgentTool| TA[trading_analyst]
        Coord -->|AgentTool| EA[execution_analyst]
        Coord -->|AgentTool| RA[risk_analyst]
    end
    subgraph Core["Always-on Agent Platform SKUs"]
        direction LR
        Gemini[("Gemini 2.5 Flash<br/>per-token")]
        Runtime[("Agent Runtime<br/>vCPU + memory-sec")]
        Sess[("Sessions<br/>per event appended")]
        MB[("Memory Bank<br/>per memory + gen tokens")]
    end
    subgraph Extras["Agent-specific SKUs"]
        Search[("Google Search grounding<br/>capable, 0 measured")]
    end
    Engine -.-> Core
    DA -.-> Search""",
        "arch": ("`financial_coordinator` (root) delegates to 4 specialist sub-agents wrapped as "
                 "AgentTools, each its own LlmAgent:\n"
                 "- `data_analyst` — fetches and analyzes market/ticker data\n"
                 "- `trading_analyst` — proposes a trading strategy from the data\n"
                 "- `execution_analyst` — defines an execution plan (timing, sizing)\n"
                 "- `risk_analyst` — assesses risks of the proposed strategy\n\n"
                 "A single user query fans out to multiple model calls; in EXP-006 it consumed "
                 "17k–34k input tokens per interaction (heaviest input-token consumer in the corpus)."),
        "skus": "Gemini tokens (input/output/cached); Agent Runtime (vCPU + memory); Sessions; "
                "Memory Bank (generation + writes); Google Search grounding (capable but not triggered).",
    },
    "academic_research": {
        "title": "academic-research", "use_case": "Academic literature analysis & discovery",
        "complexity": "Medium-High", "pattern": "Hierarchical (coordinator + AgentTool sub-agents)",
        "diagram": """graph TB
    User([User]) --> Coord
    subgraph Engine["Vertex AI Agent Engine — academic_research"]
        direction TB
        Coord[academic_coordinator]
        Coord -->|AgentTool| WS[academic_websearch]
        Coord -->|AgentTool| NR[academic_newresearch]
    end
    subgraph Core["Always-on Agent Platform SKUs"]
        direction LR
        Gemini[("Gemini 2.5 Flash<br/>per-token")]
        Runtime[("Agent Runtime<br/>vCPU + memory-sec")]
        Sess[("Sessions<br/>per event appended")]
        MB[("Memory Bank<br/>per memory + gen tokens")]
    end
    subgraph Extras["Agent-specific SKUs"]
        Search[("Google Search grounding<br/>capable, 0 measured")]
    end
    Engine -.-> Core
    WS -.-> Search""",
        "arch": ("`academic_coordinator` (root) routes between 2 specialist AgentTools:\n"
                 "- `academic_websearch_agent` — searches the web for relevant papers\n"
                 "- `academic_newresearch_agent` — proposes new research directions from findings\n\n"
                 "Sequential flow: search → analyze → synthesize. Lightweight architecture; cost "
                 "variability is high (model decides how much to reason)."),
        "skus": "Gemini tokens; Agent Runtime (vCPU + memory); Sessions; Memory Bank; "
                "Google Search grounding (capable but not triggered in our workloads).",
    },
    "blogger_agent": {
        "title": "blog-writer", "use_case": "Multi-agent technical blog authoring",
        "complexity": "High", "pattern": "Hierarchical + Sequential (4 sub-agents) + HITL",
        "diagram": """graph TB
    User([User]) <-->|HITL refine| Coord
    subgraph Engine["Vertex AI Agent Engine — blog-writer"]
        direction TB
        Coord[interactive_blogger_agent]
        Coord --> P1[blog_planner]
        P1 --> P2[blog_writer]
        P2 --> P3[blog_editor]
        P3 --> P4[social_media_writer]
    end
    subgraph Core["Always-on Agent Platform SKUs"]
        direction LR
        Gemini[("Gemini 2.5 Flash<br/>per-token")]
        Runtime[("Agent Runtime<br/>vCPU + memory-sec")]
        Sess[("Sessions<br/>per event appended")]
        MB[("Memory Bank<br/>per memory + gen tokens")]
    end
    Engine -.-> Core""",
        "arch": ("`interactive_blogger_agent` orchestrates a 4-stage pipeline of sub-agents:\n"
                 "1. `blog_planner` — outlines structure from the topic\n"
                 "2. `blog_writer` — drafts the post\n"
                 "3. `blog_editor` — refines tone, clarity, structure\n"
                 "4. `social_media_writer` — creates social posts from the blog\n\n"
                 "Human-in-the-loop: the user can request changes mid-flow and the root re-invokes "
                 "the relevant sub-agent."),
        "skus": "Gemini tokens; Agent Runtime (vCPU + memory); Sessions; Memory Bank; "
                "Google Search grounding (capable, not triggered).",
    },
    "marketing_agency": {
        "title": "marketing-agency", "use_case": "End-to-end website/branding launch suite",
        "complexity": "Medium-High", "pattern": "Hierarchical (coordinator + AgentTool creators)",
        "diagram": """graph TB
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
    LC -.-> GCS""",
        "arch": ("`marketing_coordinator` (root) delegates to 4 specialist creators wrapped as AgentTools:\n"
                 "- `domain_create_agent` — suggests/validates domain names\n"
                 "- `website_create_agent` — drafts website hero + content\n"
                 "- `marketing_create_agent` — develops the marketing plan\n"
                 "- `logo_create_agent` — generates the brand logo via Imagen (gemini-2.5-flash-image)\n\n"
                 "Logo generation is the only sub-agent that exercises the genmedia SKU surface."),
        "skus": "Gemini tokens; Agent Runtime (vCPU + memory); Sessions; Memory Bank; "
                "Imagen / gemini-2.5-flash-image (genmedia, billed per image); Google Search grounding "
                "(capable, not triggered in our 2-turn workloads).",
    },
    "nexshift_agent": {
        "title": "nexshift-agent", "use_case": "AI nurse rostering & scheduling optimizer",
        "complexity": "High", "pattern": "Hierarchical + Sequential + Parallel + HITL (4 patterns)",
        "diagram": """graph TB
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
    Engine -.-> Core""",
        "arch": ("`RosteringCoordinator` (root) orchestrates **7 specialist sub-agents** across the "
                 "rostering flow:\n"
                 "- `context_gatherer` — collects shift requirements + constraints\n"
                 "- `config` — validates roster configuration\n"
                 "- `compliance` — checks labor-law & policy constraints\n"
                 "- `solver_agent` — runs the OR-Tools CP-SAT constraint solver (compute-heavy)\n"
                 "- `empathy` — surfaces employee concerns / exceptions\n"
                 "- `presenter` — formats the final roster for output\n\n"
                 "**31 tools** total across sub-agents — the broadest tool surface in this corpus. "
                 "The OR-Tools constraint solve runs inside Agent Runtime, so vCPU cost can spike "
                 "for harder rosters. Our experimental prompts were too free-form to trigger the "
                 "full solver pipeline (returned mostly empty responses)."),
        "skus": "Gemini tokens; Agent Runtime (vCPU/memory, **compute-heavy from CP-SAT solver**); "
                "Sessions; Memory Bank.",
    },
    "fomc_research": {
        "title": "fomc-research", "use_case": "FOMC meeting financial-analysis report",
        "complexity": "High", "pattern": "Hierarchical + Sequential, multimodal pipeline",
        "diagram": """graph TB
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
    R3 -.-> Search""",
        "arch": ("Hierarchical multi-stage research pipeline. Root agent coordinates 4 sub-agents in "
                 "sequence:\n"
                 "- `retrieve_meeting_data_agent` — fetches FOMC meeting metadata from **BigQuery**\n"
                 "- `extract_page_data_agent` — downloads + parses official PDF transcripts "
                 "(pdfplumber + Cloud Storage), then runs **multimodal Gemini** on the PDFs\n"
                 "- `research_agent` — gathers contextual web background\n"
                 "- `analysis_agent` — synthesizes the final report on rates / inflation outlook\n\n"
                 "Multimodal: passes raw PDF documents to Gemini as inputs (not just text)."),
        "skus": "Gemini tokens (text + multimodal); Agent Runtime (vCPU + memory); Sessions; Memory Bank; "
                "**BigQuery** (FOMC dataset queries); **Cloud Storage** (PDF downloads); Google Search "
                "grounding (research_agent, capable but didn't trigger in our prompts).",
    },
    "plumber_agent": {
        "title": "plumber-data-engineering-assistant", "use_case": "Build/deploy data pipelines "
                                                                    "(Dataflow / Dataproc / dbt / GCS)",
        "complexity": "High", "pattern": "Hierarchical (deepest in corpus: coordinator + 6 specialists)",
        "diagram": """graph TB
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
    GH -.-> GHE""",
        "arch": ("`plumber_agent` (root) routes data-engineering requests to **6 specialist sub-agents** "
                 "— the deepest hierarchy in this corpus. Each sub-agent owns a distinct GCP data product:\n"
                 "- `dataflow_agent` — Dataflow pipeline design + job submission\n"
                 "- `dataproc_agent` — Dataproc cluster operations\n"
                 "- `dataproc_template_agent` — Dataproc template management\n"
                 "- `dbt_agent` — dbt model generation; writes SQL to **GCS** + executes against **BigQuery**\n"
                 "- `github_agent` — repo operations via GitPython (clone, branch, commit)\n"
                 "- `monitoring_agent` — reads Cloud Monitoring metrics for pipeline observability\n\n"
                 "By **intent**, this agent touches ~10–11 distinct GCP product SKUs (the broadest in our "
                 "corpus). In practice, whether each SKU bills depends on whether the user prompt invokes "
                 "that sub-agent against real resources."),
        "skus": "Gemini tokens; Agent Runtime (vCPU + memory); Sessions; Memory Bank; **BigQuery** (dbt "
                "execution); **Cloud Storage** (SQL artifacts, GCS data IO); **Dataflow**, **Dataproc**, "
                "**Dataform** (sub-agent intent, only billed when actually invoked); **Cloud Monitoring** "
                "API reads.",
    },
}
META["on_brand_genmedia"] = {
    "title": "on-brand-genmedia", "use_case": "Brand-compliant image generation with quality gate",
    "complexity": "High", "pattern": "Loop + Hierarchical (iterate-until-on-brand)",
    "diagram": """graph TB
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
    Img -.-> GCS""",
    "arch": ("Iterative image generation with a scoring gate. Sub-agents:\n"
             "- `prompt_agent` — refines the image-generation prompt from user intent\n"
             "- `image_agent` — generates the image via `gemini-2.5-flash-image` (Imagen-family genmedia)\n"
             "- `scoring_agent` — scores the image against brand guidelines (0–100)\n"
             "- `checker_agent` — gate: if score < `SCORE_THRESHOLD` (default 45), loop back to "
             "prompt refinement; up to `MAX_ITERATIONS` (default 2)\n\n"
             "Multiple Imagen calls per interaction make this the costliest agent in our corpus by "
             "image-gen SKU + model tokens combined."),
    "skus": "Gemini tokens (heavy fan-out across iterations); Agent Runtime (vCPU + memory); "
            "Sessions; Memory Bank; **Imagen / gemini-2.5-flash-image** (per-image SKU, multiple per "
            "interaction); Cloud Storage (image artifacts).",
}
# ---- Archetype agents (calculator archetypes, Moderate complexity) ----
META["conversational_chatbot"] = {
    "title": "conversational-chatbot (archetype)", "use_case": "Customer-support Q&A chatbot",
    "complexity": "Archetype: Conversational Chatbot / Moderate",
    "pattern": "Single agent + light tools + Memory Bank",
    "diagram": """graph TB
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
    Engine -.-> Core""",
    "arch": ("Single user-facing support agent (archetype: Conversational Chatbot, Moderate). "
             "Light tool use — `faq_lookup` + `kb_search` (stand-ins for a BigQuery/KB lookup) — and "
             "`preload_memory` for returning-user personalization. Volume-driven archetype: cheap "
             "model, short turns. Measured ~4 model calls / ~8 session events per 2-turn interaction."),
    "skus": "Gemini tokens; Agent Runtime (vCPU + memory); Sessions; Memory Bank. (BigQuery/KB lookup "
            "mocked locally — would bill BigQuery in production.)",
}
META["workflow_operator"] = {
    "title": "workflow-operator (archetype)", "use_case": "Order-fulfillment workflow operator",
    "complexity": "Archetype: Workflow Operator / Moderate",
    "pattern": "Single agent + heavy tool fan-out (8 tools)",
    "diagram": """graph TB
    User([User]) --> Op
    subgraph Engine["Agent Engine — workflow_operator"]
        direction TB
        Op["operator_agent (Gemini 2.5 Flash)"]
        Op --> T1[lookup_order]
        Op --> T2[check_inventory]
        Op --> T3[validate_address]
        Op --> T4[calculate_shipping]
        Op --> T5[apply_discount]
        Op --> T6[update_order_status]
        Op --> T7[send_notification]
        Op --> T8[log_transaction]
    end
    subgraph Core["Always-on Agent Platform SKUs"]
        direction LR
        Gemini[("Gemini 2.5 Flash<br/>per-token (high tool fan-out)")]
        Runtime[("Agent Runtime<br/>vCPU + memory-sec")]
        Sess[("Sessions<br/>per event appended")]
        MB[("Memory Bank<br/>per memory + gen tokens")]
    end
    Engine -.-> Core
    T1 -.->|prod: via| Backend[(BigQuery / Apigee-fronted APIs)]""",
    "arch": ("Single agent that drives an order-fulfillment workflow end to end with heavy tool "
             "fan-out (archetype: Workflow Operator, Moderate). 8 tools — lookup_order, "
             "check_inventory, validate_address, calculate_shipping, apply_discount, "
             "update_order_status, send_notification, log_transaction. Tool-fan-out-driven: measured "
             "~12.5 model calls / ~25 session events per 2-turn interaction (highest tool churn of "
             "the four archetypes). Tools stand in for backend/API calls (Apigee + BigQuery in prod)."),
    "skus": "Gemini tokens; Agent Runtime (vCPU + memory); Sessions; Memory Bank. (Backend tool calls "
            "mocked — would bill BigQuery + Apigee in production.)",
}
META["autonomous_researcher"] = {
    "title": "autonomous-researcher (archetype)", "use_case": "Deep web research with synthesis",
    "complexity": "Archetype: Autonomous Researcher / Moderate",
    "pattern": "Single agent + Google Search grounding, long outputs",
    "diagram": """graph TB
    User([User]) --> Res
    subgraph Engine["Agent Engine — autonomous_researcher"]
        direction TB
        Res["researcher_agent (Gemini 2.5 Flash)<br/>plan → search → synthesize"]
        Res -->|tool| GSt[google_search]
    end
    subgraph Core["Always-on Agent Platform SKUs"]
        direction LR
        Gemini[("Gemini 2.5 Flash<br/>per-token (long outputs)")]
        Runtime[("Agent Runtime<br/>vCPU + memory-sec")]
        Sess[("Sessions<br/>per event appended")]
        MB[("Memory Bank<br/>per memory + gen tokens")]
    end
    subgraph Extras["Agent-specific SKUs"]
        GS[("Google Search grounding<br/>per grounded prompt")]
    end
    Engine -.-> Core
    GSt -.-> GS""",
    "arch": ("Deep-research agent (archetype: Autonomous Researcher, Moderate). Plans, grounds on the "
             "web via ADK `google_search`, and synthesizes long reports. Token-depth-driven: premium "
             "model intent (Gemini Pro), long outputs (~6,000 output tokens/interaction measured), and "
             "Search grounding (~69 grounded searches across the run — the first SKU usage that "
             "actually exercises Search grounding in this project). Internal-corpus RAG (Vertex AI "
             "Search) deferred to the High variant, since google_search must be the sole tool."),
    "skus": "Gemini tokens (long outputs); Agent Runtime (vCPU + memory); Sessions; Memory Bank; "
            "**Google Search grounding** (measured non-zero).",
}
META["multi_agent_orchestrator"] = {
    "title": "multi-agent-orchestrator (archetype)", "use_case": "Decompose-and-delegate orchestration",
    "complexity": "Archetype: Multi-Agent Orchestrator / Moderate",
    "pattern": "Coordinator + 3 specialist sub-agents (agent-call fan-out)",
    "diagram": """graph TB
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
    DS -.->|prod| BQ[(BigQuery / RAG)]""",
    "arch": ("Coordinator that decomposes a request and delegates to 3 specialist sub-agents — "
             "data_specialist (metrics / records / corpus), analysis_specialist (stats / trends), "
             "action_specialist (summary / ticket / notify) (archetype: Multi-Agent Orchestrator, "
             "Moderate). Fan-out-driven and the most expensive of the four: measured ~20,000 input "
             "tokens, ~12.5 model calls, ~25 session events per 2-turn interaction (coordinator + "
             "sub-agent token multiplication). Specialist tools are local stand-ins for BigQuery / RAG."),
    "skus": "Gemini tokens (coordinator + sub-agents); Agent Runtime (vCPU + memory); Sessions; "
            "Memory Bank. (Specialist BigQuery/RAG calls mocked — would bill in production.)",
}

PACKAGES = ["financial_advisor", "academic_research", "blogger_agent", "marketing_agency",
            "nexshift_agent", "fomc_research", "plumber_agent", "on_brand_genmedia",
            "conversational_chatbot", "workflow_operator", "autonomous_researcher",
            "multi_agent_orchestrator"]


def var_word(cv: float) -> str:
    if cv < 15:
        return "Low"
    if cv < 40:
        return "Medium"
    if cv < 70:
        return "High"
    return "Very high"


def load(pkg):
    return json.loads((DATA / f"cost_report_{pkg}.json").read_text())


def load_transcript(pkg):
    """Read transcript JSONL → list of turn dicts. Returns [] if no transcript."""
    p = DATA / f"transcript_{pkg}.jsonl"
    if not p.exists():
        return []
    rows = []
    with p.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def transcript_interactions(pkg):
    """Group a transcript into interactions by user_id (preserving order).
    Returns a list of interactions, each a list of turn records."""
    rows = load_transcript(pkg)
    inters, by_user = [], {}
    for r in rows:
        u = r.get("user")
        if u not in by_user:
            by_user[u] = []
            inters.append(by_user[u])
        by_user[u].append(r)
    return inters


def workload_profile(pkg, max_chars=200):
    """Summarize a transcript's workload for §7.
    Returns dict: n_interactions, turn_counts (Counter), scenarios (list of
    distinct conversations as prompt-lists), sample (first interaction turns)."""
    import collections
    inters = transcript_interactions(pkg)
    if not inters:
        return None
    turn_counts = collections.Counter(len(it) for it in inters)
    # Distinct scenarios = distinct tuples of inputs (order-preserving).
    seen, scenarios = set(), []
    for it in inters:
        key = tuple((t.get("input") or "").strip() for t in it)
        if key not in seen:
            seen.add(key)
            scenarios.append([t.get("input", "") for t in it])
    sample = []
    for i, t in enumerate(inters[0], 1):
        txt = (t.get("output_text") or "").replace("\n", " ").strip()
        if len(txt) > max_chars:
            txt = txt[:max_chars] + "…"
        u = t.get("usage") or {}
        sample.append((i, t.get("input", ""), u.get("prompt", 0), u.get("output", 0), txt))
    return {"n_interactions": len(inters), "turn_counts": dict(sorted(turn_counts.items())),
            "scenarios": scenarios, "sample": sample}


def derive(pkg):
    """Per-interaction SKU usage quantities (+ secondary derived cost) for an agent."""
    r = load(pkg); v = r["variability"]; rt = r["runtime"]; mem = r["memory_and_session"]
    avg = r["per_run_avg"]; n = max(len(r["runs"]), 1)
    gm = r.get("grounding_and_media") or {}
    image_per_run = (gm.get("image_gen_usd", 0) or 0) / n
    grounding_per_run = (gm.get("search_grounding_usd", 0) or 0) / n
    # Prefer raw measured seconds (newer reports); else back-derive from priced $ / rate.
    ru = r.get("runtime_usage")
    if ru:
        vcpu_total, gib_total = ru["cpu_core_seconds"], ru["memory_gib_seconds"]
    else:
        vcpu_total, gib_total = rt["cpu_usd"] / VCPU_RATE, rt["memory_usd"] / MEM_RATE
    return {
        "pkg": pkg, "title": META[pkg]["title"], "complexity": META[pkg]["complexity"],
        "pattern": META[pkg]["pattern"], "engine": r["engine"].split("/")[-1], "n": n,
        # usage quantities per interaction
        "in_tok": v["input_tokens"]["mean"], "in_rng": f"{v['input_tokens']['min']}–{v['input_tokens']['max']}",
        "in_var": var_word(v["input_tokens"]["cv_pct"]),
        "out_tok": v["output_tokens"]["mean"], "out_rng": f"{v['output_tokens']['min']}–{v['output_tokens']['max']}",
        "out_var": var_word(v["output_tokens"]["cv_pct"]),
        "calls": v["model_calls"]["mean"], "calls_var": var_word(v["model_calls"]["cv_pct"]),
        "vcpu_sec": vcpu_total / n,
        "gib_sec": gib_total / n,
        "sess": v["session_events"]["mean"], "sess_var": var_word(v["session_events"]["cv_pct"]),
        "gen_tok": mem["generate_memories_tokens"] / n,
        "mem_written": mem.get("memories_written", 0) / n,
        "mem_retrieved": mem.get("memories_retrieved", 0) / n,
        "web_searches": gm.get("web_search_requests", 0), "images": gm.get("images_generated", 0),
        # Model Armor (P1) — DERIVED, not deployed: bills per token scanned ($0.10/1M).
        # Assumes 100% of conversation I/O (input+output tokens) is scanned. If only the
        # user-facing boundary is scanned, it's a fraction of this.
        "armor_tokens": v["input_tokens"]["mean"] + v["output_tokens"]["mean"],
        "c_model_armor": (v["input_tokens"]["mean"] + v["output_tokens"]["mean"]) * 0.10 / 1e6,
        "fs_reads": (r.get("cumulative", {}) or {}).get("fs_reads", 0),
        "fs_writes": (r.get("cumulative", {}) or {}).get("fs_writes", 0),
        "fs_reads_pi": (r.get("cumulative", {}) or {}).get("fs_reads", 0) / n,
        "fs_writes_pi": (r.get("cumulative", {}) or {}).get("fs_writes", 0) / n,
        # secondary derived cost ($/interaction)
        "c_model": avg["model_usd"], "c_runtime": avg["runtime_usd"], "c_memsess": avg["memory_session_usd"],
        "c_firestore": avg.get("firestore_usd", 0),
        "c_image": image_per_run, "c_grounding": grounding_per_run,
        "c_total": avg["total_usd"] + image_per_run + grounding_per_run
        + (v["input_tokens"]["mean"] + v["output_tokens"]["mean"]) * 0.10 / 1e6,
        "c_total_min": v["model_usd"]["min"] + avg["runtime_usd"] + avg["memory_session_usd"] + image_per_run + grounding_per_run,
        "c_total_max": v["model_usd"]["max"] + avg["runtime_usd"] + avg["memory_session_usd"] + image_per_run + grounding_per_run,
        "cost_var": var_word(v["model_usd"]["cv_pct"]),
    }


def agent_md(d):
    m = META[d["pkg"]]
    retr_note = ("\n_Memory retrievals = 0: this agent has no preload_memory tool — it writes "
                 "memories from the session but doesn't read them back._" if d["mem_retrieved"] == 0 else "")
    lines = [
        f"# SKU Usage Summary — `{m['title']}` ({d['pkg']})", "",
        f"- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `{d['engine']}`",
        f"- **Use case:** {m['use_case']} · **Complexity:** {d['complexity']}",
        f"- **Unit:** 1 interaction = 2-turn conversation + memory-write ({d['calls']:.1f} model calls avg). "
        "Deployed on Vertex AI Agent Engine (GEAP).",
        "- **Focus:** measured **usage per SKU**; dollar cost is a secondary derived view (§6).", "",
        "## 1. Architecture", "",
        "```mermaid", m["diagram"], "```", "",
        m["arch"], f"\n**Pattern:** {m['pattern']}", "",
        "## 2. SKUs (products) consumed", "", m["skus"],
        "\n(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised "
        "via add_session_to_memory. Search grounding / Imagen used by the agent but usage not yet "
        "metered here — see §7.)", "",
        "## 3. How usage was measured", "",
        f"Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; "
        f"**{d['n']} runs** for variability; 300s Monitoring settle; token usage from the model response "
        f"(`usage_metadata`, exact), runtime + Memory Bank usage from Cloud Monitoring (per-engine).",
        f"Reproduce: `python scripts/exp_sample.py --package {d['pkg']} --runs {d['n']} --settle 300`", "",
        f"## 4. SKU usage per interaction (PRIMARY)", "",
        f"Measured usage quantities per interaction (avg over {d['n']} runs), with run-to-run range and variability.", "",
        "| SKU dimension | Unit | Typical | Range | Variability |", "|---|---|---|---|---|",
        f"| Gemini input tokens | tokens | {d['in_tok']:.0f} | {d['in_rng']} | {d['in_var']} |",
        f"| Gemini output tokens (incl. thinking) | tokens | {d['out_tok']:.0f} | {d['out_rng']} | {d['out_var']} |",
        f"| Model calls | calls | {d['calls']:.1f} | — | {d['calls_var']} |",
        f"| Agent Runtime — vCPU | vCPU-seconds | {d['vcpu_sec']:.1f} | — | — |",
        f"| Agent Runtime — memory | GiB-seconds | {d['gib_sec']:.1f} | — | — |",
        f"| Sessions | events appended | {d['sess']:.1f} | — | {d['sess_var']} |",
        f"| Memory Bank — generation | tokens | {d['gen_tok']:.0f} | — | — |",
        f"| Memory Bank — memories written | memories | {d['mem_written']:.1f} | — | — |",
        f"| Memory Bank — retrievals | reads | {d['mem_retrieved']:.1f} | — | — |",
        (f"| Firestore — document writes | writes | {d['fs_writes_pi']:.2f} | — | — |"
         if d.get('fs_writes', 0) or d.get('fs_reads', 0) else None),
        (f"| Firestore — document reads | reads | {d['fs_reads_pi']:.2f} | — | — |"
         if d.get('fs_writes', 0) or d.get('fs_reads', 0) else None),
        retr_note, "",
        "## 5. Grounding & media usage (now collected)", "",
        f"- **Google Search grounding:** {d['web_searches']:.0f} grounded web-search requests measured "
        "(Cloud Monitoring, project-wide). The agent *can* ground on Search but this workload did not "
        "trigger it; would bill ~$0.035/request if used.",
        f"- **Image generation (Imagen):** {d['images']:.0f} images measured (from response events). "
        "Would bill ~$0.04/image if used.", "",
        "## 5b. Caveats on usage capture", "",
        "- vCPU/GiB-seconds are amortized over the measurement window (utilization-dependent).",
        "- Memory storage (stored-memory count over time) is export-only.",
        "- Grounding count is project-wide (no per-engine label); image count is event-based.",
        "- Still uncaptured: Cloud Trace, Logging, Storage.", "",
        "## 6. Secondary: derived cost (usage × catalog list price)", "",
        "Provided for reference only. List price, not actual billed; **usage above is the primary output.**", "",
        "| SKU | $/interaction |", "|---|---|",
        f"| Gemini tokens | {d['c_model']:.4f} |",
        f"| Agent Runtime | {d['c_runtime']:.4f} |",
        f"| Memory Bank + Sessions | {d['c_memsess']:.4f} |",
        (f"| Firestore ({d['fs_writes']:.0f}w/{d['fs_reads']:.0f}r over {d['n']} runs) | {d['c_firestore']:.7f} |"
         if d.get('fs_writes', 0) or d.get('fs_reads', 0) else None),
        f"| Model Armor (derived: {d['armor_tokens']:.0f} tok scanned @ $0.10/1M) | {d['c_model_armor']:.6f} |",
        (f"| Imagen (image generation) | {d['c_image']:.4f} |" if d['c_image'] else None),
        (f"| Search grounding | {d['c_grounding']:.4f} |" if d['c_grounding'] else None),
        f"| **Total (measured SKUs)** | **{d['c_total']:.4f}** (range {d['c_total_min']:.4f}–{d['c_total_max']:.4f}) |",
    ]
    # §7 — test workload + sample interaction from transcripts.
    wp = workload_profile(d["pkg"])
    rows = load_transcript(d["pkg"])
    if wp:
        tc = wp["turn_counts"]
        multi = len(wp["scenarios"]) > 1
        turn_desc = (", ".join(f"{n}-turn×{c}" for n, c in tc.items())
                     if multi else f"{next(iter(tc), 2)} turns each")
        lines += ["",
                  "## 7. Test workload & sample interactions", "",
                  f"**{wp['n_interactions']} interactions** ({len(rows)} total user turns), "
                  f"fresh user_id per interaction. "
                  + (f"Interactions cycle **{len(wp['scenarios'])} distinct conversation scenarios** of "
                     f"varying length ({turn_desc}) — real-world interactions differ in length and topic, "
                     "so this spreads coverage rather than repeating one script."
                     if multi else
                     "All interactions repeat the same 2-turn workload to isolate run-to-run variability."),
                  ""]
        for si, sc in enumerate(wp["scenarios"], 1):
            lines.append(f"**Scenario {si}** ({len(sc)} turns):" if multi else "**Workload (turn-by-turn):**")
            lines.append("")
            lines.append("| Turn | User query |"); lines.append("|---|---|")
            for ti, q in enumerate(sc, 1):
                lines.append(f"| {ti} | {q.replace('|', '\\|')} |")
            lines.append("")
        lines += ["**Sample interaction (first run):**", ""]
        for tn, q, ipt, opt, preview in wp["sample"]:
            lines.append(f"- **Turn {tn}** ({ipt} in / {opt} out tokens) — user: *{q.replace('|', '\\|')}*")
            lines.append(f"  - reply preview: {preview}")
        lines.append("")
        lines.append(f"Full transcripts: `data/transcript_{d['pkg']}.jsonl` (one JSON record per turn; "
                     "full input, output_text, every tool call+response, per-step usage). "
                     "**Not committed** (data/ is gitignored — runtime artifact).")
    (OUT / f"{d['pkg']}.md").write_text("\n".join(x for x in lines if x is not None))


def combined(ds):
    ma = {"title": "memory_assistant", "complexity": "High", "pattern": "Hierarchical + Memory Bank",
          "in_tok": 3398, "in_rng": "2552–4001", "out_tok": 1605, "out_rng": "752–3150",
          "calls": 5.75, "vcpu_sec": 39.0, "gib_sec": 560.0, "sess": 11.5, "gen_tok": 2493,
          "mem_written": 3.25, "mem_retrieved": 2.5, "web_searches": 0, "images": 0,
          "c_model": 0.0050, "c_runtime": 0.0035, "c_memsess": 0.0080, "c_total": 0.0165,
          "c_total_min": 0.0144, "c_total_max": 0.0206, "cost_var": "High"}
    rows = ds + [ma]
    sortk = lambda r: -r["in_tok"]
    L = ["# Combined SKU-Usage Report — ADK Agents on Gemini Enterprise Agent Platform", "",
         "**Purpose:** estimate **usage per SKU** across different agent architectures deployed to "
         "Vertex AI Agent Engine. Usage quantities are the primary output; dollar cost is a secondary "
         "derived view (usage × catalog list price). This is **not** an expense report or a "
         "cost-optimization exercise — it characterizes what each agent *consumes*, by SKU.", "",
         "Unit = one interaction (2-turn conversation + memory-write; memory_assistant = 3-turn). "
         "All gemini-2.5-flash. 3 runs/agent; usage from model responses + Cloud Monitoring (per-engine).", "",
         "## 1. SKU usage per interaction — model & compute (PRIMARY)", "",
         "| Agent | Input tokens (range) | Output tokens (range) | Model calls | vCPU-seconds | GiB-seconds |",
         "|---|---|---|---|---|---|"]
    for r in sorted(rows, key=sortk):
        L.append(f"| {r['title']} | {r['in_tok']:.0f} ({r['in_rng']}) | {r['out_tok']:.0f} ({r['out_rng']}) "
                 f"| {r['calls']:.1f} | {r['vcpu_sec']:.1f} | {r['gib_sec']:.0f} |")
    L += ["",
          "## 2. SKU usage per interaction — Agent Platform features (PRIMARY)", "",
          "| Agent | Session events | Memory-gen tokens | Memories written | Memory retrievals |",
          "|---|---|---|---|---|"]
    for r in sorted(rows, key=sortk):
        L.append(f"| {r['title']} | {r['sess']:.1f} | {r['gen_tok']:.0f} | {r['mem_written']:.1f} | {r['mem_retrieved']:.1f} |")
    L += ["",
          "_Memory retrievals are ~0 for the sample agents (no preload_memory tool); memory_assistant "
          "retrieves because cross-session recall is its purpose._", "",
          "## 2b. Grounding & media usage (now collected)", "",
          "Collectors added for Google Search grounding (Cloud Monitoring) and image generation "
          "(response events). **Measured 0 for all agents in these runs** — the agents have the "
          "capability but the short 2-turn workloads did not trigger Search or image generation.", "",
          "| Agent | Web-search grounded requests | Images generated |",
          "|---|---|---|"]
    for r in sorted(rows, key=sortk):
        L.append(f"| {r['title']} | {r.get('web_searches', 0):.0f} | {r.get('images', 0):.0f} |")
    L += ["",
          "_Would bill ~$0.035 per grounded request (Gemini 2.x) and ~$0.04 per image (Imagen) if triggered._", "",
          "## 3. SKU presence matrix (which agents touch which SKUs)", "",
          "| Agent | Gemini tokens | Agent Runtime | Sessions | Memory Bank | Search grounding | Image gen |",
          "|---|---|---|---|---|---|---|"]
    pres = {
        "financial-advisor": "✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | —",
        "academic-research": "✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | —",
        "blog-writer": "✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | —",
        "marketing-agency": "✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | capable, 0 measured",
        "memory_assistant": "✓ | ✓ | ✓ | ✓ (write+read) | — | —",
        "nexshift-agent": "✓ | ✓ (CP-SAT compute) | ✓ | ✓ (write) | — | —",
        "fomc-research": "✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — (BigQuery + Cloud Storage intended)",
        "plumber-data-engineering-assistant": "✓ | ✓ | ✓ | ✓ (write) | — | — (+BQ/GCS/Dataflow/Dataproc/Dataform by intent)",
        "on-brand-genmedia": "✓ | ✓ | ✓ | ✓ (write) | — | **27 images measured (gemini-2.5-flash-image)**",
    }
    for r in sorted(rows, key=sortk):
        if r["title"] in pres:
            L.append(f"| {r['title']} | {pres[r['title']]} |")
    L += ["",
          "## 4. Secondary: derived cost per interaction (usage × catalog list price)", "",
          "Reference only — list price, not actual billed. The usage tables above are the deliverable.", "",
          "| Agent | Gemini $ | Runtime $ | Mem+Sess $ | Total $ (range) | Cost variability |",
          "|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: -x["c_total"]):
        L.append(f"| {r['title']} | {r['c_model']:.4f} | {r['c_runtime']:.4f} | {r['c_memsess']:.4f} | "
                 f"{r['c_total']:.4f} ({r['c_total_min']:.4f}–{r['c_total_max']:.4f}) | {r['cost_var']} |")
    L += ["",
          "## 5. Usage-pattern observations", "",
          "1. **Input-token usage is the biggest differentiator** — financial-advisor consumes "
          f"~{max(r['in_tok'] for r in rows):.0f} input tokens/interaction vs "
          f"~{min(r['in_tok'] for r in rows):.0f} for the lightest, a "
          f"{max(r['in_tok'] for r in rows)/max(min(r['in_tok'] for r in rows), 1):.0f}× spread driven by "
          "depth of multi-specialist analysis.",
          "2. **vCPU-seconds track analysis depth**, not just call count — the heaviest agent burns far "
          "more compute per interaction.",
          "3. **Output-token usage is the most variable SKU** run-to-run (the model varies how much it "
          "reasons), so token usage should be reported as a range, not a single number.",
          "4. **Memory generation + session events are consumed even when memories are never read back** "
          "— a real SKU footprint for any session-persisted agent.",
          "5. **Search-grounding and image-generation collectors are now in place** (grounding from "
          "Cloud Monitoring, images from response events). They measured **0** for these workloads — "
          "the agents are capable but the short 2-turn tasks didn't trigger them. Remaining uncaptured "
          "SKUs: Cloud Trace, Logging, Storage.", "",
          "## Method & reproducibility", "",
          "Per agent: `python scripts/exp_sample.py --package <pkg> --runs 3 --settle 300`. Token usage "
          "from model responses (exact); vCPU/GiB-seconds + Memory Bank usage from Cloud Monitoring "
          "(per-engine), back-derived to quantities. Per-agent detail in `agent_summaries/`.", "",
          "_Engines: financial_advisor, academic_research, blogger_agent, marketing_agency (+ memory_assistant)._"]
    (REPO / "COMBINED_SKU_USAGE_REPORT.md").write_text("\n".join(L))


# Agent name -> per-agent doc filename (relative to agent_summaries/).
LINKS = {
    "financial-advisor": "financial_advisor.md",
    "academic-research": "academic_research.md",
    "blog-writer": "blogger_agent.md",
    "marketing-agency": "marketing_agency.md",
    "memory_assistant": "memory_assistant.md",
    "nexshift-agent": "nexshift_agent.md",
    "fomc-research": "fomc_research.md",
    "plumber-data-engineering-assistant": "plumber_agent.md",
    "on-brand-genmedia": "on_brand_genmedia.md",
    "conversational-chatbot (archetype)": "conversational_chatbot.md",
    "workflow-operator (archetype)": "workflow_operator.md",
    "autonomous-researcher (archetype)": "autonomous_researcher.md",
    "multi-agent-orchestrator (archetype)": "multi_agent_orchestrator.md",
}

# Brief descriptions for the "Agents at a glance" header section.
DESCRIPTIONS = {
    "financial-advisor": ("Stock analysis & trading-strategy advisor. Hierarchical: coordinator "
                          "+ 4 AgentTool specialists (data, trading, execution, risk). Heaviest "
                          "input-token consumer; runtime-dominated."),
    "memory_assistant": ("Personal assistant with long-term cross-session memory. Coordinator + "
                         "2 sub-agents + Memory Bank (write+read). Exercises the most Agent "
                         "Platform features in this corpus."),
    "blog-writer": ("Multi-agent technical blog authoring. Coordinator + 4 sub-agents (outline, "
                    "draft, edit, social) + HITL refinement."),
    "academic-research": ("Academic literature discovery & analysis. Coordinator + AgentTool "
                          "websearch + new-research specialists."),
    "marketing-agency": ("End-to-end branding suite: domain, website, marketing, logo (Imagen) "
                         "creators wrapped as AgentTools under one coordinator."),
    "nexshift-agent": ("AI nurse rostering optimizer. Coordinator + 7 sub-agents + OR-Tools CP-SAT "
                       "solver. 4 orchestration patterns (Hierarchical + Sequential + Parallel + HITL), "
                       "31 tools — broadest tool surface in the corpus."),
    "fomc-research": ("FOMC meeting financial-analysis report. Hierarchical + Sequential multimodal "
                      "pipeline (BigQuery metadata + PDF transcripts via pdfplumber + multimodal Gemini)."),
    "plumber-data-engineering-assistant": ("Build/deploy data pipelines. Deepest hierarchy in the corpus: "
                                            "root + 6 specialist sub-agents (Dataflow / Dataproc / "
                                            "Dataproc-templates / dbt / GitHub / Cloud Monitoring). Touches "
                                            "~10–11 distinct GCP product SKUs by intent."),
    "on-brand-genmedia": ("Brand-compliant iterative image generation. Loop + Hierarchical: prompt → "
                          "image (gemini-2.5-flash-image) → score → re-prompt if below threshold. "
                          "Heaviest image-gen SKU usage in the corpus."),
    # Calculator archetypes (moderate complexity), purpose-built for this project.
    "conversational-chatbot (archetype)": ("Calculator archetype: Conversational Chatbot / Moderate. "
                          "Single support agent + light tools + Memory Bank. Cheapest archetype; volume-driven."),
    "workflow-operator (archetype)": ("Calculator archetype: Workflow Operator / Moderate. Single agent "
                          "driving an 8-tool order workflow. Tool-fan-out-driven (highest session-event churn)."),
    "autonomous-researcher (archetype)": ("Calculator archetype: Autonomous Researcher / Moderate. Single "
                          "agent + Google Search grounding, long outputs. Token-depth-driven; exercises Search grounding."),
    "multi-agent-orchestrator (archetype)": ("Calculator archetype: Multi-Agent Orchestrator / Moderate. "
                          "Coordinator + 3 specialist sub-agents. Fan-out-driven; most expensive archetype."),
}


def linkify(name: str) -> str:
    return f"[{name}]({LINKS[name]})" if name in LINKS else name


def master(ds):
    ma = {"title": "memory_assistant", "complexity": "High", "pattern": "Hierarchical + Memory Bank",
          "in_tok": 3398, "in_rng": "2552–4001", "out_tok": 1605, "out_rng": "752–3150",
          "calls": 5.75, "vcpu_sec": 39.0, "gib_sec": 560.0, "sess": 11.5, "gen_tok": 2493,
          "mem_written": 3.25, "mem_retrieved": 2.5, "web_searches": 0, "images": 0,
          "c_model": 0.0050, "c_runtime": 0.0035, "c_memsess": 0.0080, "c_total": 0.0165,
          "c_total_min": 0.0144, "c_total_max": 0.0206, "cost_var": "High"}
    rows = ds + [ma]
    sortk = lambda r: -r["in_tok"]

    totals = [r["c_total"] for r in rows]
    L = ["# Master Summary — Implemented Agent Architectures", "",
         "**Living index** of every agent architecture deployed in this project, the SKUs each "
         "consumes, measured per-interaction usage, and derived list-price cost. Update this doc "
         "whenever a new agent is added. Per-agent details (architecture, methodology, full "
         "usage distribution + variability) live in linked files below.", "",
         "## Executive summary", "",
         f"- **{len(rows)} agents deployed** on Vertex AI Agent Engine (Gemini Enterprise Agent Platform).",
         f"- **Cost spans ${min(totals):.4f}–${max(totals):.4f} per interaction** at catalog list "
         f"price ({max(totals)/min(totals):.0f}× spread), driven by architecture (sub-agent fan-out, "
         f"analysis depth) more than the prompt.",
         "- **Architecture matters more than prompt:** financial-advisor consumes ~7× more input "
         "tokens than the lightest agent and is the only **runtime-dominated** one.",
         "- **Run-to-run variability is real:** identical task can swing total cost ~2× (output/"
         "thinking tokens are the noisy SKU).",
         "- **Memory + session SKUs are a meaningful slice** even when memories are never read back "
         "— always present for any session-persisted agent.",
         "- **Collectors built and validated** for tokens, vCPU/memory, sessions, Memory Bank, "
         "Search grounding, and Imagen. Still uncaptured: Cloud Trace, Logging, Storage.", "",
         "## What \"per interaction\" means", "",
         "All usage and cost figures below are **per interaction** — the unit of work the cost "
         "harness measures. One interaction =",
         "",
         "- **For the 4 ADK sample agents (financial-advisor, academic-research, blog-writer, "
         "marketing-agency):** a **2-turn conversation in one session** + an `add_session_to_memory` "
         "call that triggers Memory Bank generation. Typically fans out to 2–6 model calls and "
         "~4–7 session events depending on sub-agent delegation.",
         "- **For `memory_assistant`:** a **3-turn flow across 2 sessions** — Session A receives 2 "
         "user facts → `add_session_to_memory` → Session B issues 1 recall query. ~5.75 model calls "
         "and ~11.5 session events.",
         "",
         "**Caveat:** because `memory_assistant`'s interaction has more turns, its raw $/interaction "
         "is not strictly apples-to-apples with the 2-turn samples — normalize to **$/turn or "
         "$/model-call** for head-to-head comparison. Variability stats (low/high range) are over "
         "3 runs per agent.", "",
         "All agents: model `gemini-2.5-flash`, deployed to Vertex AI Agent Engine. Reproduce: "
         "`python scripts/exp_sample.py --package <pkg> --runs 3 --settle 300`.", "",
         "## Agents at a glance", ""]
    for r in sorted(rows, key=sortk):
        t = r["title"]; desc = DESCRIPTIONS.get(t, "")
        link = f" → [details]({LINKS[t]})" if t in LINKS else ""
        L.append(f"- **{t}** — {desc}{link}")
    L += ["",
          "## 1. SKU usage per interaction — model & compute (PRIMARY)", "",
          "| Agent | Input tokens (range) | Output tokens (range) | Model calls | vCPU-seconds | GiB-seconds |",
          "|---|---|---|---|---|---|"]
    for r in sorted(rows, key=sortk):
        L.append(f"| {linkify(r['title'])} | {r['in_tok']:.0f} ({r['in_rng']}) | "
                 f"{r['out_tok']:.0f} ({r['out_rng']}) | {r['calls']:.1f} | {r['vcpu_sec']:.1f} | {r['gib_sec']:.0f} |")
    L += ["",
          "## 2. SKU usage per interaction — Agent Platform features (PRIMARY)", "",
          "| Agent | Session events | Memory-gen tokens | Memories written | Memory retrievals |",
          "|---|---|---|---|---|"]
    for r in sorted(rows, key=sortk):
        L.append(f"| {linkify(r['title'])} | {r['sess']:.1f} | {r['gen_tok']:.0f} | "
                 f"{r['mem_written']:.1f} | {r['mem_retrieved']:.1f} |")
    L += ["",
          "_Memory retrievals are ~0 for the sample agents (no preload_memory tool); memory_assistant "
          "retrieves because cross-session recall is its purpose._", "",
          "## 2b. Grounding & image generation", "",
          "Collectors: **`extract_grounding_from_events`** (per-interaction, attributable — validated "
          "with a separate `grounded_news` agent) and **`collect_imagen_usage`** (Cloud Monitoring "
          "`model_invocation_count` for imagen models — validated with 7 captured invocations). "
          "Measured 0 for the agents below: their 2-turn workloads did not trigger Search or image "
          "generation; the collectors themselves are validated working.", "",
          "| Agent | Grounded prompts | Images generated |", "|---|---|---|"]
    for r in sorted(rows, key=sortk):
        L.append(f"| {linkify(r['title'])} | {r.get('web_searches', 0):.0f} | {r.get('images', 0):.0f} |")
    L += ["",
          "_Would bill ~$0.035 per grounded prompt (Gemini 2.x) and ~$0.04 per image (Imagen) if triggered._", "",
          "## 3. SKU presence matrix (which agents touch which SKUs)", "",
          "| Agent | Gemini tokens | Agent Runtime | Sessions | Memory Bank | Search grounding | Image gen |",
          "|---|---|---|---|---|---|---|"]
    pres = {
        "financial-advisor": "✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | —",
        "academic-research": "✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | —",
        "blog-writer": "✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | —",
        "marketing-agency": "✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | capable, 0 measured",
        "memory_assistant": "✓ | ✓ | ✓ | ✓ (write+read) | — | —",
        "nexshift-agent": "✓ | ✓ (CP-SAT compute) | ✓ | ✓ (write) | — | —",
        "fomc-research": "✓ | ✓ | ✓ | ✓ (write) | capable, 0 measured | — (BigQuery + Cloud Storage intended)",
        "plumber-data-engineering-assistant": "✓ | ✓ | ✓ | ✓ (write) | — | — (+BQ/GCS/Dataflow/Dataproc/Dataform by intent)",
        "on-brand-genmedia": "✓ | ✓ | ✓ | ✓ (write) | — | **27 images measured (gemini-2.5-flash-image)**",
        "conversational-chatbot (archetype)": "✓ | ✓ | ✓ | ✓ (write) | — | — (BigQuery KB mocked)",
        "workflow-operator (archetype)": "✓ | ✓ | ✓ | ✓ (write) | — | — (BigQuery/Apigee mocked)",
        "autonomous-researcher (archetype)": "✓ | ✓ | ✓ | ✓ (write) | **measured non-zero** | —",
        "multi-agent-orchestrator (archetype)": "✓ | ✓ | ✓ | ✓ (write) | — | — (BigQuery/RAG mocked)",
    }
    for r in sorted(rows, key=sortk):
        if r["title"] in pres:
            L.append(f"| {linkify(r['title'])} | {pres[r['title']]} |")
    L += ["",
          "**+ Firestore (operational DB):** the 4 archetype agents also exercise a real **Firestore** "
          "SKU (save_note/load_note → document writes/reads, scoped per authenticated user). Measured "
          "non-zero on all 4 (workflow_operator heaviest: ~1 read + ~1 write/interaction). Cost is "
          "negligible (~$3e-7/interaction) but the SKU is exercised + measured. Not in the calculator "
          "(it only models BigQuery + Vector Search for data). The sample agents (EXP-006/007) don't use it.",
          "",
          "## 4. Secondary: derived cost per interaction (usage × catalog list price)", "",
          "Reference only — list price, not actual billed. The usage tables above are the deliverable.", "",
          "| Agent | Gemini $ | Runtime $ | Mem+Sess $ | Total $ (range) | Cost variability |",
          "|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: -x["c_total"]):
        L.append(f"| {linkify(r['title'])} | {r['c_model']:.4f} | {r['c_runtime']:.4f} | {r['c_memsess']:.4f} | "
                 f"{r['c_total']:.4f} ({r['c_total_min']:.4f}–{r['c_total_max']:.4f}) | {r['cost_var']} |")
    L += ["",
          "## 5. Usage-pattern observations", "",
          "1. **Input-token usage is the biggest differentiator** — financial-advisor consumes "
          f"~{max(r['in_tok'] for r in rows):.0f} input tokens/interaction vs "
          f"~{min(r['in_tok'] for r in rows):.0f} for the lightest, a "
          f"{max(r['in_tok'] for r in rows)/max(min(r['in_tok'] for r in rows), 1):.0f}× spread driven by "
          "depth of multi-specialist analysis.",
          "2. **vCPU-seconds track analysis depth**, not just call count — the heaviest agent burns far "
          "more compute per interaction.",
          "3. **Output-token usage is the most variable SKU** run-to-run (the model varies how much it "
          "reasons), so token usage should be reported as a range, not a single number.",
          "4. **Memory generation + session events are consumed even when memories are never read back** "
          "— a real SKU footprint for any session-persisted agent.",
          "5. **Grounding and Imagen collectors are validated** (separate validation runs registered "
          "non-zero usage). For the 5 agents above the workloads simply didn't trigger them.", "",
          "## 6. Experiment query volume (what we actually sent)", "",
          "Each agent's test consists of N **interactions**, each = a 2-turn conversation + a "
          "memory-write (memory_assistant = 3-turn). Inside one interaction the user_id stays "
          "constant; across interactions we mint a fresh user_id so memory state doesn't carry "
          "over. Sample agents (EXP-006/007) repeat one 2-turn workload; **archetype agents "
          "(EXP-008) cycle multiple conversation scenarios of varying length** (2–5 turns).", "",
          "| Agent | Interactions | Turns/interaction | Total user turns | Source |",
          "|---|---|---|---|---|"]
    qrows = []
    for pkg, title in [("financial_advisor", "financial-advisor"),
                       ("academic_research", "academic-research"),
                       ("blogger_agent", "blog-writer"),
                       ("marketing_agency", "marketing-agency"),
                       ("nexshift_agent", "nexshift-agent"),
                       ("fomc_research", "fomc-research"),
                       ("plumber_agent", "plumber-data-engineering-assistant"),
                       ("on_brand_genmedia", "on-brand-genmedia"),
                       ("conversational_chatbot", "conversational-chatbot (archetype)"),
                       ("workflow_operator", "workflow-operator (archetype)"),
                       ("autonomous_researcher", "autonomous-researcher (archetype)"),
                       ("multi_agent_orchestrator", "multi-agent-orchestrator (archetype)")]:
        wp = workload_profile(pkg)
        if not wp:
            continue
        tc = wp["turn_counts"]
        turns_disp = "–".join(str(x) for x in (min(tc), max(tc))) if min(tc) != max(tc) else str(min(tc))
        total_turns = sum(n * c for n, c in tc.items())
        if pkg in ("financial_advisor", "academic_research", "blogger_agent", "marketing_agency"):
            exp = "EXP-006"
        elif pkg in ("conversational_chatbot", "workflow_operator", "autonomous_researcher",
                     "multi_agent_orchestrator"):
            exp = "EXP-008 (archetype)"
        else:
            exp = "EXP-007"
        qrows.append((title, wp["n_interactions"], turns_disp, total_turns, exp))
    # Also memory_assistant (hand-tracked) and grounded_news (validation only).
    qrows.append(("memory_assistant", 4, "3", 12, "EXP-005"))
    qrows.append(("grounded_news (validation)", 2, "1", 2, "collector-validation"))
    total = sum(r[3] for r in qrows)
    for nm, ni, tt, tq, exp in sorted(qrows, key=lambda x: -x[3]):
        L.append(f"| {linkify(nm) if nm in LINKS else nm} | {ni} | {tt} | **{tq}** | {exp} |")
    L.append(f"| **TOTAL** | — | — | **{total}** | all experiments combined |")
    L += ["",
          "Full per-turn transcripts (input, output_text, tool calls/responses, per-step usage) live "
          "at `data/transcript_<agent>.jsonl` locally. **Not committed** — `data/` is gitignored as "
          "runtime artifact. Each per-agent doc's §7 shows the workload prompts + one sample "
          "interaction inline.", "",
          "## Per-agent detail docs", ""]
    for r in sorted(rows, key=sortk):
        t = r["title"]
        if t in LINKS:
            L.append(f"- [{t}]({LINKS[t]}) — {DESCRIPTIONS.get(t, '').split('.')[0]}.")
    L += ["",
          "## Method & reproducibility", "",
          "Per agent: `python scripts/exp_sample.py --package <pkg> --runs 3 --settle 300`. Token "
          "usage from model responses (exact); vCPU/GiB-seconds + Memory Bank usage from Cloud "
          "Monitoring (per-engine); grounding from event `grounding_metadata` (per-interaction); "
          "Imagen from Monitoring `model_invocation_count` (model_user_id contains 'imagen'). "
          "Prices from the live Cloud Billing Catalog. Master summary regenerated by "
          "`scripts/build_summaries.py`.", "",
          "_See also: [COMBINED_SKU_USAGE_REPORT.md](../COMBINED_SKU_USAGE_REPORT.md) (repo-root "
          "version of §1–§5 above), [GEAP_COMPONENTS.md](../GEAP_COMPONENTS.md), "
          "[COST_DATA_COLLECTION_PROCESS.md](../COST_DATA_COLLECTION_PROCESS.md), "
          "[PROJECT_RUNBOOK.md](../PROJECT_RUNBOOK.md)._"]
    (OUT / "MASTER_SUMMARY.md").write_text("\n".join(L))


def main():
    ds = [derive(p) for p in PACKAGES]
    for d in ds:
        agent_md(d)
    combined(ds)
    master(ds)
    print("Wrote per-agent summaries + COMBINED_SKU_USAGE_REPORT.md + agent_summaries/MASTER_SUMMARY.md")


if __name__ == "__main__":
    main()
