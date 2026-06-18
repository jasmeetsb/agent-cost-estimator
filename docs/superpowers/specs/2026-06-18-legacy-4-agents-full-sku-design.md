# Design — Full-SKU + two-model build for 4 legacy agents (EXP-015)

**Goal:** bring fomc_research, plumber_agent, on_brand_genmedia, memory_assistant to parity with
the existing 12-agent corpus — appropriate SKUs + the two-model master/sub split — then deploy,
validate, and run the full experiment to gather per-SKU usage. (nexshift skipped: returns empty
to free-form prompts → no meaningful token data without a custom structured workload.)

## Decisions (from brainstorm)
- **Scope:** 4 agents (nexshift excluded).
- **SKU policy:** per-agent *appropriate* (not a forced uniform set).
- **Run scale:** canonical gemini-2.5-flash @ 80 interactions/agent (isolated windows, capturing
  complete `token_count`) + a 15-interaction two-model run for the master/sub %. Same basis +
  weight as the existing corpus.

## Per-agent SKU plan
| agent | Firestore | load_memory | RAG corpus | web grounding | Imagen | two-model |
|---|:--:|:--:|---|:--:|:--:|:--:|
| fomc_research | ✅ | ✅ | econ/Fed (`fomc-*`) | ✅ AgentTool | – | ✅ |
| plumber_agent | ✅ | ✅ | data-eng (`de-*`) | ✅ AgentTool | – | ✅ |
| on_brand_genmedia | ✅ | ✅ | brand guidelines (`brand-*`) | – | keep | ✅ |
| memory_assistant | ✅ | ✅ (switch from preload_memory) | – | – | – | ✅ |

Model Armor is derived (build_summaries computes from tokens — no code). Sessions / Runtime /
Memory-Bank generation are automatic on Agent Engine.

## Build (minimal-invasive, mirror the existing 8)
- Copy `fs_state.py` + `_gmodel.py` into each package; add `save_note`/`load_note` + `load_memory`
  to the root agent's tools; append env-guarded `apply_split(root_agent)` (default deploy =
  single 2.5-flash; `COST_TWO_MODEL=1` = 3.5-flash master / 3.1-flash-lite subs).
- fomc/plumber: add a dedicated `web_research` Agent (sole tool = `google_search`) wrapped as an
  **AgentTool** (NOT sub_agent — else grounding never runs in the deployed stream).
- fomc/plumber/on_brand: add a `VertexAiSearchTool` on `agent-knowledge`.
- Update each root instruction to actually call the new tools (load_memory→...→save_note; RAG;
  web_research).
- Extend `agent-knowledge` with ~6 docs each (`fomc-*`, `de-*`, `brand-*`) via `setup_rag.py`
  (GCS+JSONL); self-verify.
- Add/confirm 2-turn workloads in `exp_sample.WORKLOADS` for all 4.
- Update each agent's `META` in `build_summaries.py` (skus + arch reflect new SKUs).

## Experiment (per agent, sequential — token_count isolation)
1. **Validate** — deploy canonical, ~5 interactions, confirm non-empty + tools fire in transcript.
2. **Full canonical** — 80 isolated interactions, `--user-pool` for returning-user retrieval;
   capture stream + complete `token_count` + per-engine SKUs + transcript.
3. **Two-model split** — redeploy `COST_TWO_MODEL=1`, 15 isolated interactions → master/sub %.
4. **Finalize** — `backfill_memory`; regenerate summaries/§0/§1/docx/xlsx; runbook EXP-015.

## Risks / guards
- on_brand Imagen × `apply_split`: must only switch text LlmAgents, never the image model — verify.
- `google_search` must be the sole tool on its agent and wired as AgentTool (not sub_agent).
- Heavier deploy deps (on_brand image-gen, fomc/plumber sample libs) — may need extra `requirements`.
- New RAG docs must match the workloads or RAG returns nothing (self-verify search).
- All deploys sequential (staging race); all token_count runs sequential (project-wide metric).
- PROTECTED: never delete Beads `reasoningEngines/105003910208421888`; teardown by explicit ID only.
