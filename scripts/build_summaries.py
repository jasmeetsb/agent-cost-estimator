"""Generate per-agent cost summaries (markdown) + a combined cost report.

Reads data/cost_report_<package>.json for the 4 deployed adk-sample agents and
writes agent_summaries/<package>.md each (memory_assistant-style), then a
COMBINED_COST_REPORT.md comparing all agents (incl. memory_assistant).
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
OUT = REPO / "agent_summaries"
OUT.mkdir(exist_ok=True)

# Static descriptors per agent (from adk-samples analysis).
META = {
    "financial_advisor": {
        "title": "financial-advisor", "use_case": "Stock analysis & trading strategy advisor",
        "complexity": "High", "pattern": "Hierarchical (coordinator + 4 AgentTool specialists)",
        "arch": "financial_coordinator delegates to data_analyst, trading_analyst, "
                "execution_analyst, risk_analyst (each wrapped as an AgentTool).",
        "skus": "Gemini tokens, Agent Runtime (vCPU/mem), Sessions, Memory Bank, Google Search grounding",
    },
    "academic_research": {
        "title": "academic-research", "use_case": "Academic literature analysis & discovery",
        "complexity": "Medium-High", "pattern": "Hierarchical (coordinator + AgentTool sub-agents)",
        "arch": "academic_coordinator routes to websearch + new-research specialists.",
        "skus": "Gemini tokens, Agent Runtime, Sessions, Memory Bank, Google Search grounding",
    },
    "blogger_agent": {
        "title": "blog-writer", "use_case": "Multi-agent technical blog authoring",
        "complexity": "High", "pattern": "Hierarchical + Sequential (4 sub-agents) + HITL",
        "arch": "interactive_blogger_agent orchestrates 4 sub-agents (outline, draft, "
                "edit, social) + tools; human-in-the-loop refinement.",
        "skus": "Gemini tokens, Agent Runtime, Sessions, Memory Bank, Google Search grounding",
    },
    "marketing_agency": {
        "title": "marketing-agency", "use_case": "End-to-end website/branding launch suite",
        "complexity": "Medium-High", "pattern": "Hierarchical (coordinator + AgentTool creators)",
        "arch": "marketing_coordinator delegates to domain, website, marketing & logo "
                "creators; logo creation uses Imagen (genmedia).",
        "skus": "Gemini tokens, Agent Runtime, Sessions, Memory Bank, Imagen (genmedia), Google Search grounding",
    },
}

PACKAGES = ["financial_advisor", "academic_research", "blogger_agent", "marketing_agency"]


def load(pkg):
    return json.loads((DATA / f"cost_report_{pkg}.json").read_text())


def agent_md(pkg):
    r = load(pkg); m = META[pkg]; v = r["variability"]; avg = r["per_run_avg"]
    rt = r["runtime"]; mem = r["memory_and_session"]
    eng = r["engine"].split("/")[-1]
    lines = [
        f"# Agent Cost Summary — `{m['title']}` ({pkg})", "",
        f"- **Source:** google/adk-samples · **Model:** gemini-2.5-flash · **Engine:** `{eng}`",
        f"- **Use case:** {m['use_case']} · **Complexity:** {m['complexity']}",
        f"- **Cost unit:** 1 interaction = 2-turn conversation + memory generation "
        f"({int(v['model_calls']['mean'])} model calls avg). Deployed on Vertex AI Agent Engine (GEAP).",
        "",
        "## 1. Architecture", "", m["arch"], f"\n**Pattern:** {m['pattern']}", "",
        "## 2. Components / SKUs used", "", m["skus"],
        "\n(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation "
        "exercised via add_session_to_memory. Search grounding used by the agent but not yet "
        "metered here — see caveats.)", "",
        "## 3. How the experiment was run", "",
        "Deployed to Agent Engine; per run = 2-turn conversation in one session + "
        "add_session_to_memory; 3 runs for variability; 300s Monitoring settle; actual runtime "
        "+ memory_bank usage pulled from Cloud Monitoring and priced at catalog list rate.",
        f"Reproduce: `python scripts/exp_sample.py --package {pkg} --runs 3 --settle 300`", "",
        "## 4. Typical usage & variance (3 runs)", "",
        "| Metric | mean | min–max | CV% |", "|---|---|---|---|",
        f"| input tokens | {v['input_tokens']['mean']:.0f} | {v['input_tokens']['min']}–{v['input_tokens']['max']} | {v['input_tokens']['cv_pct']}% |",
        f"| output tokens | {v['output_tokens']['mean']:.0f} | {v['output_tokens']['min']}–{v['output_tokens']['max']} | {v['output_tokens']['cv_pct']}% |",
        f"| model calls | {v['model_calls']['mean']:.1f} | {v['model_calls']['min']}–{v['model_calls']['max']} | {v['model_calls']['cv_pct']}% |",
        f"| model cost ($) | {v['model_usd']['mean']:.4f} | {v['model_usd']['min']:.4f}–{v['model_usd']['max']:.4f} | {v['model_usd']['cv_pct']}% |",
        "",
        "## 5. Cost per interaction, by SKU (catalog list price)", "",
        "| SKU | per-run $ | note |", "|---|---|---|",
        f"| Conversation tokens | {avg['model_usd']:.4f} | input+output |",
        f"| Agent Runtime (vCPU+mem) | {avg['runtime_usd']:.4f} | amortized; utilization-dependent |",
        f"| Memory generation tokens | {mem['generate_memories_usd']:.4f} | {int(mem['generate_memories_tokens'])} tok @ input rate |",
        f"| Session events | {mem['session_events_usd']:.4f} | ~{mem['session_events_observed']} events |",
        f"| **Total per interaction** | **{avg['total_usd']:.4f}** | excl. Search grounding + Trace/Logging |",
        "",
        "## 6. Caveats", "",
        "- Catalog **list price**, not actual billed (internal project; true $ needs BigQuery export).",
        "- **Google Search grounding** is used by this agent but NOT yet metered (per-grounded-prompt SKU); add via Monitoring web_search metrics or export.",
        "- Memory *retrieval* = 0 (agent has no preload_memory tool); only memory *generation* is exercised.",
        "- Runtime cost is utilization-dependent; idle memory allocation dominates at low QPS.",
        "- Cloud Trace (enable_tracing), Logging, Storage, and (marketing) Imagen not captured.",
    ]
    (OUT / f"{pkg}.md").write_text("\n".join(lines))
    fixed = avg["runtime_usd"] + avg["memory_session_usd"]  # non-model components (amortized)
    return {"pkg": pkg, "title": m["title"], "complexity": m["complexity"],
            "pattern": m["pattern"], "calls": v["model_calls"]["mean"],
            "in_tok": v["input_tokens"]["mean"], "out_tok": v["output_tokens"]["mean"],
            "model": avg["model_usd"], "runtime": avg["runtime_usd"],
            "mem": avg["memory_session_usd"], "total": avg["total_usd"],
            "model_cv": v["model_usd"]["cv_pct"],
            "total_min": v["model_usd"]["min"] + fixed,
            "total_max": v["model_usd"]["max"] + fixed}


def combined(rowdata):
    # memory_assistant from EXP-005 (known figures): model 0.0050 (0.0029–0.0091),
    # runtime 0.0035, mem 0.0080 -> fixed 0.0115.
    ma = {"title": "memory_assistant (EXP-004/5)", "complexity": "High",
          "pattern": "Hierarchical + Memory Bank", "calls": 5.75, "in_tok": 3398,
          "out_tok": 1605, "model": 0.0050, "runtime": 0.0035, "mem": 0.0080,
          "total": 0.0165, "model_cv": 48, "total_min": 0.0029 + 0.0115,
          "total_max": 0.0091 + 0.0115}
    rows = rowdata + [ma]
    L = ["# Combined Cost Estimation Report — ADK Agents on Gemini Enterprise Agent Platform", "",
         "Cost-per-interaction estimates for 5 agents deployed to Vertex AI Agent Engine, measured "
         "via the harness (usage_metadata + Cloud Monitoring SKU extraction, priced at Billing "
         "Catalog list rates). **Costs are list-price estimates of actual measured usage, not billed "
         "dollars.** Unit = one interaction (2-turn conversation + memory generation; "
         "memory_assistant = 3-turn). All gemini-2.5-flash. **Total is mean over 3 runs; the "
         "min–max range reflects run-to-run model-cost variance (the variable component) with "
         "amortized runtime/memory held fixed.**", "",
         "## Per-agent comparison", "",
         "| Agent | Complexity | Pattern | Calls | Model $ | Runtime $ | Mem+Sess $ | **Total $/interaction (mean)** | **Total range (min–max)** | Model-cost CV |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: -x["total"]):
        L.append(f"| {r['title']} | {r['complexity']} | {r['pattern']} | {r['calls']:.1f} | "
                 f"{r['model']:.4f} | {r['runtime']:.4f} | {r['mem']:.4f} | "
                 f"**{r['total']:.4f}** | {r['total_min']:.4f}–{r['total_max']:.4f} | {r['model_cv']:.0f}% |")
    totals = [r["total"] for r in rows]
    L += ["",
          f"**Across agents:** ${min(totals):.4f}–${max(totals):.4f} per interaction "
          f"({max(totals)/min(totals):.1f}× spread on the means). **Within a single agent**, the "
          f"identical task varies up to {max((r['total_max']/r['total_min']) for r in rows):.1f}× "
          f"run-to-run (see Total range) — driven by output/thinking-token swings.", "",
          "## Key findings", "",
          "1. **Cost spans ~3× across agents** for similar 2-turn interactions — architecture "
          "complexity (sub-agent fan-out, analysis depth) drives it more than the workload.",
          "2. **financial-advisor is the most expensive (~$0.034)** and the only **runtime-dominated** "
          "one — it pulls 17k–34k input tokens/run and does heavy multi-specialist analysis, so vCPU "
          "compute outweighs token cost.",
          "3. **Model-token cost is highly variable (CV 35–80%)** run-to-run for the identical task — "
          "driven by output/thinking-token swings. Always quote a distribution, not a point estimate.",
          "4. **Memory generation + session events are a real, often-hidden slice** (~$0.003–0.005/run) "
          "present even when the agent never *retrieves* memory.",
          "5. **Runtime cost is utilization-dependent** — these numbers amortize over a busy window; "
          "at low QPS idle memory allocation dominates (see EXP-001).", "",
          "## Not captured (would raise the true cost)", "",
          "- **Google Search grounding** (all four samples ground on Search): $14–45 per 1,000 grounded prompts.",
          "- **Imagen/genmedia** (marketing-agency logo generation): per-image SKU.",
          "- **Cloud Trace** (tracing enabled on deploy), **Logging**, **Storage**, **memory storage** (monthly).",
          "- True billed dollars require **BigQuery billing export** (unavailable on this shared corp account).", "",
          "## Method & reproducibility", "",
          "Per agent: `python scripts/exp_sample.py --package <pkg> --runs 3 --settle 300`. "
          "Token usage from `usage_metadata` (exact); runtime + Memory Bank from Cloud Monitoring "
          "(`reasoning_engine/*`, engine-scoped); prices from the live Billing Catalog API. "
          "Per-agent detail in `agent_summaries/`.", "",
          "_Engines deployed: financial_advisor, academic_research, blogger_agent, marketing_agency "
          "(+ memory_assistant). All accrue idle runtime (~$25/mo each) until torn down._"]
    (REPO / "COMBINED_COST_REPORT.md").write_text("\n".join(L))


def main():
    rowdata = [agent_md(p) for p in PACKAGES]
    combined(rowdata)
    print("Wrote summaries:", [f"agent_summaries/{p}.md" for p in PACKAGES])
    print("Wrote COMBINED_COST_REPORT.md")


if __name__ == "__main__":
    main()
