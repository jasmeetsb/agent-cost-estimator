# Design — `agent-cost-estimates` clean results repo

**Goal:** produce a separate, clean, self-contained repo holding curated per-agent usage results
(starting with the 4 archetypes) for an extended team to (a) seed a cost calculator with default
per-interaction SKU numbers and (b) see the architecture that produced those numbers. The cost
calculator itself lives elsewhere and is out of scope.

## Decisions (from brainstorm, 2026-06-26)
- **Contents:** docs only — curated per-agent summary docs + a README index. No structured data
  file, no calculator app.
- **Doc format:** results-focused. Keep Architecture (diagram + short prose), the SKU-usage-per-
  interaction table, and derived cost. Drop verbose internal methodology + test-workload sections;
  keep a short "how to read / caveats" box.
- **Repo:** `agent-cost-estimates`, a NEW local git repo at `~/github/agent-cost-estimates/`,
  committed locally only. The user picks/creates the GitHub remote (public or private) and pushes.
- **Self-contained:** NO links back to the source repo (`agent-cost-estimator`, which is going
  private). A brief stand-alone methodology blurb in the README replaces the link-back.
- **Scrub internal identifiers:** no `jsb-genai-sa`, project number (436848677253), runtime SA
  emails, or reasoningEngine IDs in the clean docs. (Achieved by *generating* from `derive()` +
  `META` rather than copying the internal-laden summary `.md`, so internal IDs are simply never
  emitted.)
- **Model labeling:** all usage/cost numbers are labeled **gemini-2.5-flash** (the canonical
  80-interaction measurement basis). The master/sub split rows carry a one-line note that the
  *percentage* was derived from a separate two-model sidecar (master gemini-3.5-flash / sub
  gemini-3.1-flash-lite). No 3.x re-run — explicitly deferred.
- **Scope now:** the 4 archetypes. Generator is parameterized so the 4 use-case + legacy agents
  drop in later via a flag.

## Production approach: generator script
A new `scripts/export_clean_results.py` in the SOURCE repo (`agent-cost-estimator`):
- **Input:** `build_summaries.derive(pkg)` (all measured per-interaction numbers + master/sub
  split) and `build_summaries.META[pkg]` (title, use_case, pattern, Mermaid `diagram`, `arch`
  prose). Reproducible — re-run when numbers change or agents are added.
- **Transform:** render the results-focused doc template (below); scrub by construction (emit only
  selected fields, never engine/project IDs).
- **Output:** writes into a target dir (default `~/github/agent-cost-estimates/`):
  - `archetypes/<hyphenated-name>.md` for each archetype
  - `README.md` (index + comparison table + methodology blurb + disclaimer)
- **CLI:** `python scripts/export_clean_results.py --out ~/github/agent-cost-estimates [--group archetypes]`
- Default group = the 4 archetypes: `conversational_chatbot`, `workflow_operator`,
  `autonomous_researcher`, `multi_agent_orchestrator`.

## Per-archetype doc template (`archetypes/<name>.md`)
1. **Header:** `# <Title>` · one-line use-case · **Model: gemini-2.5-flash** · "Averaged over N
   interactions (≈T turns each)."
2. **Architecture:** the Mermaid diagram (```mermaid fence) + 2–3 sentence description (`META.arch`,
   trimmed). This is the "what produced these numbers" reference.
3. **SKU usage per interaction:** a table — Gemini input tokens, output tokens, **master vs
   sub-agent token split** (two rows: combined master_tok / sub_tok + %; the finer input/output ×
   role 4-way breakdown is omitted from the clean doc to stay readable — available on request),
   model calls, Agent Runtime vCPU-s / GiB-s, Sessions (events), Memory Bank generation tokens +
   memories retrieved, Firestore writes/reads, Vertex AI Search (RAG) queries, Google Search
   grounded turns, Imagen images. Omit rows that are zero/NA for that agent.
4. **Derived cost per interaction:** cost-by-SKU breakdown ($ per SKU) + **Total $/interaction**.
5. **How to read / caveats** (box): usage quantities are primary; $ is catalog **list price**, not
   billed dollars; runtime vCPU/GiB-s is an amortized **upper bound**; 1 interaction = an N-turn
   conversation; master/sub split % is from a two-model measurement (note in §3).

## README
- One-paragraph intro: "Curated per-interaction usage results for seeding the cost calculator.
  Each archetype links to its architecture + measured SKU usage."
- **Comparison table** across the 4 archetypes: key columns (Interactions, Turns, Input tok, Output
  tok, Model calls, Runtime vCPU-s, Sessions, Mem-gen tok, Mem retr, Firestore W/R, RAG, Grounding,
  Imagen, $/intxn).
- **Index** linking to each `archetypes/<name>.md`.
- **Methodology blurb** (self-contained, ~4 lines): deployed to Vertex AI Agent Engine (GEAP);
  each agent averaged over its own N interactions (~80–120; stated in each doc's header); usage
  from model `usage_metadata` + Cloud Monitoring (runtime, Memory Bank); dollars = Cloud Billing
  Catalog **list prices** (estimate, not billed spend).
- **Disclaimer:** model = gemini-2.5-flash; numbers are usage-quantity-primary, list-price estimates.

## Out of scope
- The cost calculator app or any structured data export (docs only).
- Re-measuring archetypes on gemini-3.x.
- Creating/choosing the GitHub remote or setting visibility (user does this).
- Use-case + legacy agents (generator supports them; not generated in this pass).

## Success criteria
- `agent-cost-estimates/` exists as a local git repo with a clean commit.
- 4 archetype docs render (valid Mermaid, complete tables) with no internal IDs present.
- README comparison table matches the per-doc numbers and the source master table.
- Re-running the generator reproduces the repo deterministically.
