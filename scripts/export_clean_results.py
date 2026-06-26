"""Export FULL, scrubbed agent summary docs into the clean `agent-cost-estimates` repo.

Takes the complete existing per-agent summary docs (agent_summaries/<pkg>.md) — architecture,
the full SKU usage table with ranges + variability, SKUs-consumed list, grounding/media,
caveats, derived cost, and test workload + sample interactions — and emits self-contained
Markdown for an extended team: internal IDs scrubbed, no links back to the (private) source repo.
A generated README on top carries the cross-agent comparison table + a stand-alone methodology
note.

Usage:
  python scripts/export_clean_results.py --out ~/github/agent-cost-estimates [--group archetypes|use_case|legacy|all]
"""
import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import build_summaries as bs  # noqa: E402

GROUPS = {
    "archetypes": ["conversational_chatbot", "workflow_operator",
                   "autonomous_researcher", "multi_agent_orchestrator"],
    "use_case":   ["financial_advisor", "academic_research", "marketing_agency", "blogger_agent"],
    "legacy":     ["memory_assistant", "fomc_research", "plumber_agent", "on_brand_genmedia"],
}
# pkg -> (display title, output filename stem)
NICE = {
    "conversational_chatbot":   ("Conversational Chatbot", "conversational-chatbot"),
    "workflow_operator":        ("Workflow Operator", "workflow-operator"),
    "autonomous_researcher":    ("Autonomous Researcher", "autonomous-researcher"),
    "multi_agent_orchestrator": ("Multi-Agent Orchestrator", "multi-agent-orchestrator"),
    "financial_advisor":        ("Financial Advisor", "financial-advisor"),
    "academic_research":        ("Academic Research", "academic-research"),
    "marketing_agency":         ("Marketing Agency", "marketing-agency"),
    "blogger_agent":            ("Technical Blogger", "technical-blogger"),
    "memory_assistant":         ("Memory Assistant", "memory-assistant"),
    "fomc_research":            ("FOMC Research", "fomc-research"),
    "plumber_agent":            ("Data-Engineering Assistant", "data-engineering-assistant"),
    "on_brand_genmedia":        ("On-Brand Image Generation", "on-brand-genmedia"),
}

# Scrub internal identifiers (safety net over the explicit line removals below).
_SCRUB = [
    (re.compile(r"projects/[\w-]+/locations/[\w-]+/reasoningEngines/\d+"), "<engine>"),
    (re.compile(r"reasoningEngines/\d+"), "<engine>"),
    (re.compile(r"jsb-genai-sa"), "<project>"),
    (re.compile(r"\b436848677253\b"), "<project-number>"),
    (re.compile(r"service-\d+@[\w.-]+gserviceaccount\.com"), "<runtime-sa>"),
    (re.compile(r"gs://[\w.-]+"), "<staging-bucket>"),
]


def clean_doc(pkg: str) -> str:
    """Full source summary, scrubbed of internal IDs / repo-internal references."""
    title, _ = NICE[pkg]
    lines = (REPO / "agent_summaries" / f"{pkg}.md").read_text().split("\n")
    out = []
    for ln in lines:
        s = ln.strip()
        # drop repo-internal lines that won't make sense / shouldn't ship externally
        if s.startswith("Reproduce:"):
            continue
        if s.startswith("Full transcripts:"):
            continue
        # drop the internal Engine ID from the header metadata line
        ln = re.sub(r"\s*·\s*\*\*Engine:\*\*\s*`[^`]*`", "", ln)
        # rewrite the internal "# SKU Usage Summary — `x (archetype)` (pkg)" title
        ln = re.sub(r"^# SKU Usage Summary — .*$", f"# {title} — SKU usage & architecture", ln)
        for pat, repl in _SCRUB:
            ln = pat.sub(repl, ln)
        out.append(ln)
    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text).rstrip() + "\n"
    return text


def comparison_table(ds):
    H = ("| Architecture | Interactions | Total turns | Input tokens | Output tokens | Model calls | "
         "Runtime vCPU-s | Session events | Mem-gen tokens | Mem retrieved | Firestore W/R | "
         "RAG queries | Grounded turns | $ / interaction |")
    S = "|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--:|--:|--:|--:|"
    rows = [H, S]
    for pkg, d in ds:
        title, fn = NICE[pkg]
        rows.append(
            f"| [{title}](agent-estimates/{fn}.md) | {d['n']} | {d['total_turns']} | "
            f"{d['in_tok']:,.0f} | {d['out_tok']:,.0f} | {d['calls']:.1f} | {d['vcpu_sec']:.1f} | "
            f"{d['sess']:.1f} | {d['gen_tok']:,.0f} | {d['mem_retrieved']:.2f} | "
            f"{d['fs_writes_pi']:.2f}/{d['fs_reads_pi']:.2f} | {d.get('rag_pi',0):.2f} | "
            f"{d.get('web_ground_pi',0):.2f} | {d['c_total']:.4f} |")
    return "\n".join(rows)


def readme(ds, group):
    label = {"archetypes": "Archetypes"}.get(group, group.replace("_", "-").title())
    L = [
        "# Agent cost estimates",
        "",
        "Curated **per-interaction usage results** for representative GCP agent architectures. Each "
        "agent below links to its full architecture, measured SKU usage (with ranges + variability), "
        "derived cost, and the exact test workload behind the numbers.",
        "",
        f"## {label}",
        "",
        comparison_table(ds),
        "",
        "_All values are **per interaction** (averaged) unless noted. **Total turns** = total user turns "
        "across the whole experiment. **Mem-gen tokens** = Memory Bank generation tokens; **Mem "
        "retrieved** = memories recalled via `load_memory`. **Firestore W/R** = document writes / reads. "
        "**Grounded turns** = Google Search grounded query-turns. **$ / interaction** is a catalog "
        "list-price estimate (see below)._",
        "",
        "## How these were measured",
        "",
        "- Each agent was built on Google's **Agent Development Kit (ADK)**, deployed to **Vertex AI "
        "Agent Engine**, and run for its stated number of interactions (multi-turn; see each page).",
        "- **Model: gemini-2.5-flash** for all usage and cost numbers.",
        "- Token usage from the model's `usage_metadata`, or from Cloud Monitoring `token_count` for "
        "agents whose sub-agents are invoked as callable tools (each page states which, and why); "
        "runtime + Memory Bank from Cloud Monitoring; RAG / grounding / Firestore counted from the "
        "agent's tool calls; Imagen from Cloud Monitoring.",
        "- **Dollars are Cloud Billing Catalog list-price estimates**, not billed spend. Usage "
        "quantities are the primary output; cost is a secondary derived view.",
        "- The **coordinator vs sub-agent token split %** (where shown) comes from a separate "
        "two-model measurement (coordinator on gemini-3.5-flash, sub-agents on gemini-3.1-flash-lite).",
        "",
        "_Numbers are estimates for planning, not a billing guarantee._",
        "",
    ]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="target repo dir (e.g. ~/github/agent-cost-estimates)")
    ap.add_argument("--group", default="archetypes", choices=list(GROUPS) + ["all"])
    args = ap.parse_args()
    out = Path(args.out).expanduser()
    sub = "agent-estimates"  # single home for all agent docs; the README groups them by type
    (out / sub).mkdir(parents=True, exist_ok=True)

    pkgs = sum(GROUPS.values(), []) if args.group == "all" else GROUPS[args.group]
    ds = [(p, bs.derive(p)) for p in pkgs]
    for pkg, _ in ds:
        _, fn = NICE[pkg]
        (out / sub / f"{fn}.md").write_text(clean_doc(pkg))
        print(f"  wrote {sub}/{fn}.md")
    (out / "README.md").write_text(readme(ds, args.group))
    print("  wrote README.md")
    print(f"\nExported {len(ds)} agent(s) to {out}")


if __name__ == "__main__":
    main()
