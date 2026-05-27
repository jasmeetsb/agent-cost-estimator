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
        "arch": "interactive_blogger_agent orchestrates 4 sub-agents + tools.",
        "skus": "Gemini tokens, Agent Runtime, Sessions, Memory Bank, Google Search grounding",
    },
    "marketing_agency": {
        "title": "marketing-agency", "use_case": "End-to-end website/branding launch suite",
        "complexity": "Medium-High", "pattern": "Hierarchical (coordinator + AgentTool creators)",
        "arch": "marketing_coordinator delegates to domain, website, marketing & logo creators; "
                "logo creation uses Imagen (genmedia).",
        "skus": "Gemini tokens, Agent Runtime, Sessions, Memory Bank, Imagen (genmedia), Google Search grounding",
    },
}
PACKAGES = ["financial_advisor", "academic_research", "blogger_agent", "marketing_agency"]


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


def derive(pkg):
    """Per-interaction SKU usage quantities (+ secondary derived cost) for an agent."""
    r = load(pkg); v = r["variability"]; rt = r["runtime"]; mem = r["memory_and_session"]
    avg = r["per_run_avg"]; n = max(len(r["runs"]), 1)
    gm = r.get("grounding_and_media") or {}
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
        # secondary derived cost ($/interaction)
        "c_model": avg["model_usd"], "c_runtime": avg["runtime_usd"], "c_memsess": avg["memory_session_usd"],
        "c_total": avg["total_usd"], "c_total_min": v["model_usd"]["min"] + avg["runtime_usd"] + avg["memory_session_usd"],
        "c_total_max": v["model_usd"]["max"] + avg["runtime_usd"] + avg["memory_session_usd"],
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
        "## 1. Architecture", "", m["arch"], f"\n**Pattern:** {m['pattern']}", "",
        "## 2. SKUs (products) consumed", "", m["skus"],
        "\n(Sessions + Agent Runtime are automatic on Agent Engine; Memory Bank generation exercised "
        "via add_session_to_memory. Search grounding / Imagen used by the agent but usage not yet "
        "metered here — see §7.)", "",
        "## 3. How usage was measured", "",
        "Deployed to Agent Engine; per run = 2-turn conversation in one session + add_session_to_memory; "
        "3 runs for variability; 300s Monitoring settle; token usage from the model response "
        "(`usage_metadata`, exact), runtime + Memory Bank usage from Cloud Monitoring (per-engine).",
        f"Reproduce: `python scripts/exp_sample.py --package {d['pkg']} --runs 3 --settle 300`", "",
        "## 4. SKU usage per interaction (PRIMARY)", "",
        "Measured usage quantities per interaction (avg over 3 runs), with run-to-run range and variability.", "",
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
        f"| **Total (measured SKUs)** | **{d['c_total']:.4f}** (range {d['c_total_min']:.4f}–{d['c_total_max']:.4f}) |",
    ]
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
          f"{max(r['in_tok'] for r in rows)/min(r['in_tok'] for r in rows):.0f}× spread driven by "
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


def main():
    ds = [derive(p) for p in PACKAGES]
    for d in ds:
        agent_md(d)
    combined(ds)
    print("Wrote per-agent summaries + COMBINED_SKU_USAGE_REPORT.md")


if __name__ == "__main__":
    main()
