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


def var_word(cv: float) -> str:
    """Plain-language variability label from a coefficient of variation %."""
    if cv < 15:
        return "Low"
    if cv < 40:
        return "Medium"
    if cv < 70:
        return "High"
    return "Very high"


def load(pkg):
    return json.loads((DATA / f"cost_report_{pkg}.json").read_text())


def agent_md(pkg):
    r = load(pkg); m = META[pkg]; v = r["variability"]; avg = r["per_run_avg"]
    rt = r["runtime"]; mem = r["memory_and_session"]
    eng = r["engine"].split("/")[-1]
    n_runs = max(len(r["runs"]), 1)
    retr_pr = mem.get("memories_retrieved", 0) / n_runs
    writ_pr = mem.get("memories_written", 0) / n_runs
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
        "## 4. Usage distribution (3 runs, identical workload)", "",
        "Each row shows the **typical (average)** value, the **range** seen across runs (low to "
        "high), and how **variable** that is run-to-run (Low / Medium / High / Very high). Same "
        "task each run — differences come mostly from how much the model 'thinks'.", "",
        "| Metric | Typical (avg) | Range (low–high) | Variability |", "|---|---|---|---|",
        f"| Input tokens | {v['input_tokens']['mean']:.0f} | {v['input_tokens']['min']}–{v['input_tokens']['max']} | {var_word(v['input_tokens']['cv_pct'])} |",
        f"| Output tokens (incl. thinking) | {v['output_tokens']['mean']:.0f} | {v['output_tokens']['min']}–{v['output_tokens']['max']} | {var_word(v['output_tokens']['cv_pct'])} |",
        f"| Model calls | {v['model_calls']['mean']:.1f} | {v['model_calls']['min']}–{v['model_calls']['max']} | {var_word(v['model_calls']['cv_pct'])} |",
        f"| Session events | {v['session_events']['mean']:.1f} | {v['session_events']['min']}–{v['session_events']['max']} | {var_word(v['session_events']['cv_pct'])} |",
        f"| Memories written / run | ~{writ_pr:.1f} | — | — |",
        f"| Memory retrievals / run | ~{retr_pr:.1f} | — | — |",
        f"| Model cost ($) | {v['model_usd']['mean']:.4f} | {v['model_usd']['min']:.4f}–{v['model_usd']['max']:.4f} | {var_word(v['model_usd']['cv_pct'])} |",
        "",
        ("_Note: memory retrievals = 0 because this agent has no preload_memory tool — it generates "
         "memories from the session but doesn't read them back. Sessions + memory generation still "
         "incur cost._" if retr_pr == 0 else ""),
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
            "in_range": f"{v['input_tokens']['min']}–{v['input_tokens']['max']}",
            "out_range": f"{v['output_tokens']['min']}–{v['output_tokens']['max']}",
            "sess": v["session_events"]["mean"], "mem_written": writ_pr,
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
          "out_tok": 1605, "in_range": "2552–4001", "out_range": "752–3150",
          "sess": 11.5, "mem_written": 3.25, "model": 0.0050, "runtime": 0.0035,
          "mem": 0.0080, "total": 0.0165, "model_cv": 48, "total_min": 0.0029 + 0.0115,
          "total_max": 0.0091 + 0.0115}
    rows = rowdata + [ma]
    for r in rows:
        r["predict"] = {"Low": "Very predictable", "Medium": "Fairly predictable",
                        "High": "Variable", "Very high": "Highly variable"}[var_word(r["model_cv"])]
    L = ["# Combined Cost Estimation Report — ADK Agents on Gemini Enterprise Agent Platform", "",
         "Estimated **cost per interaction** for 5 agents deployed to Vertex AI Agent Engine. "
         "Measured from real usage (model token counts + Cloud Monitoring) and priced at Google's "
         "public list rates. **These are list-price estimates of actual measured usage — not the "
         "final invoice.** One *interaction* = a 2-turn conversation plus a memory-write "
         "(memory_assistant = 3-turn). All run on gemini-2.5-flash.", "",
         "**How to read variability:** we ran each agent 3 times on the *same* task. **Typical** is "
         "the average cost; **Range** is the cheapest-to-most-expensive run. A wide range means cost "
         "is hard to predict run-to-run (the model decides how much to \"think\" each time).", "",
         "## 1. Cost comparison (per interaction)", "",
         "| Agent | Complexity | Architecture | Typical cost | Range (low–high) | Predictability |",
         "|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: -x["total"]):
        L.append(f"| {r['title']} | {r['complexity']} | {r['pattern']} | "
                 f"**${r['total']:.4f}** | ${r['total_min']:.4f} – ${r['total_max']:.4f} | {r['predict']} |")
    totals = [r["total"] for r in rows]
    widest = max(rows, key=lambda r: r["total_max"] / r["total_min"])
    L += ["",
          f"- **Cheapest vs priciest agent:** ${min(totals):.4f} → ${max(totals):.4f} per "
          f"interaction — about a **{max(totals)/min(totals):.0f}× difference**, driven by the agent's design.",
          f"- **Same agent, run to run:** cost can swing by up to "
          f"**{(widest['total_max']/widest['total_min']-1)*100:.0f}%** (e.g. {widest['title']}: "
          f"${widest['total_min']:.4f}–${widest['total_max']:.4f}) on the identical task.",
          "- **Planning guidance:** budget with the **high end of the range**, then multiply by your "
          "expected interactions per month.", "",
          "## 2. Usage per interaction (what drives the cost)", "",
          "The raw work each agent does per interaction (averaged over 3 runs). Token counts are "
          "the main cost driver; input-token ranges show how much this varies run-to-run.", "",
          "| Agent | Input tokens (range) | Output tokens (range) | Model calls | Session events | Memories written |",
          "|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: -x["total"]):
        L.append(f"| {r['title']} | {r['in_tok']:.0f} ({r['in_range']}) | "
                 f"{r['out_tok']:.0f} ({r['out_range']}) | {r['calls']:.1f} | "
                 f"{r['sess']:.1f} | ~{r['mem_written']:.1f} |")
    L += ["",
          "**financial-advisor stands out** — it processes 4–10× more input tokens than the others "
          "(deep multi-specialist analysis), which is why its compute cost is so high.", "",
          "## 3. Which products (SKUs) each agent uses", "",
          "Dollar value = measured cost per interaction for that product. \"Used¹\" = the agent uses "
          "the product but we don't yet meter it (it would add to the total). \"—\" = not used.", "",
          "| Agent | Gemini model | Compute (Agent Runtime) | Sessions | Memory Bank | Web Search grounding | Image generation |",
          "|---|---|---|---|---|---|---|"]
    sku = {
        "financial-advisor": ("$0.0125", "$0.0196", "$0.0015", "$0.0029", "Used¹", "—"),
        "academic-research": ("$0.0078", "$0.0054", "$0.0010", "$0.0025", "Used¹", "—"),
        "blog-writer": ("$0.0085", "$0.0055", "$0.0010", "$0.0036", "Used¹", "—"),
        "marketing-agency": ("$0.0043", "$0.0055", "$0.0013", "$0.0024", "Used¹", "Used¹"),
        "memory_assistant (EXP-004/5)": ("$0.0050", "$0.0035", "$0.0029", "$0.0050", "—", "—"),
    }
    for r in sorted(rows, key=lambda x: -x["total"]):
        c = sku.get(r["title"])
        if c:
            L.append(f"| {r['title']} | {c[0]} | {c[1]} | {c[2]} | {c[3]} | {c[4]} | {c[5]} |")
    L += ["",
          "¹ *Web Search grounding bills $14–45 per 1,000 grounded prompts; image generation "
          "(Imagen) bills per image. Both are used above but not yet metered here, so real totals "
          "run somewhat higher.*", "",
          "## 4. Detailed SKU breakdown — the two most elaborate agents", "",
          "### financial-advisor — most expensive, compute-heavy", "",
          "Coordinator + 4 specialist sub-agents (data, trading, execution, risk). It pulls "
          "17,000–34,000 input tokens per run, so **server compute is the biggest cost, not the AI model**.", "",
          "| Product | Cost per interaction | Share |", "|---|---|---|",
          "| Compute (Agent Runtime) | $0.0196 | 58% |",
          "| Gemini model (tokens) | $0.0125 | 37% |",
          "| Memory Bank + Sessions | $0.0015 | 5% |",
          "| **Total (measured)** | **~$0.0336** | 100% |",
          "| Web Search grounding | not yet metered | would add |", "",
          "### memory_assistant — most Agent Platform features", "",
          "Coordinator + 2 sub-agents + long-term Memory Bank. **Memory + session operations are the "
          "single biggest slice — larger than the AI model itself.**", "",
          "| Product | Cost per interaction | Share |", "|---|---|---|",
          "| Memory Bank + Sessions | $0.0080 | 48% |",
          "| Gemini model (tokens) | $0.0050 | 30% |",
          "| Compute (Agent Runtime) | $0.0035 | 21% |",
          "| **Total (measured)** | **~$0.0165** | |", "",
          "## 5. Key takeaways for leadership", "",
          "1. **A simple agent and a complex one differ ~3× in cost** for the same kind of request — "
          "the agent's design (number of specialist sub-agents, depth of analysis) is the main cost lever.",
          "2. **The most expensive agent is dominated by compute, not the AI model** — financial-advisor "
          "does heavy multi-step analysis, so server time costs more than the words generated.",
          "3. **Cost is not fixed per request** — the same task can cost up to ~2× more on one run than "
          "another because the model varies how much it reasons. Budget for the high end of the range.",
          "4. **The newer Agent Platform features (Memory Bank, Sessions) carry real cost** — for a "
          "memory-enabled agent they were the single biggest line item, bigger than the AI model.",
          "5. **A few costs aren't counted yet** (web Search grounding, image generation, logging/tracing), "
          "so real bills will run somewhat higher than the figures here.", "",
          "## Method & reproducibility", "",
          "Per agent: `python scripts/exp_sample.py --package <pkg> --runs 3 --settle 300`. Token usage "
          "from the model response (exact); compute + Memory Bank usage from Cloud Monitoring (per-agent); "
          "prices from Google's live Billing Catalog. Per-agent detail in `agent_summaries/`.", "",
          "_Engines deployed: financial_advisor, academic_research, blogger_agent, marketing_agency "
          "(+ memory_assistant). Each accrues idle compute (~$25/mo) until torn down._"]
    (REPO / "COMBINED_COST_REPORT.md").write_text("\n".join(L))


def main():
    rowdata = [agent_md(p) for p in PACKAGES]
    combined(rowdata)
    print("Wrote summaries:", [f"agent_summaries/{p}.md" for p in PACKAGES])
    print("Wrote COMBINED_COST_REPORT.md")


if __name__ == "__main__":
    main()
