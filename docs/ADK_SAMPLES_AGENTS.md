# ADK Sample Agents — Architecture & Cost-Surface Summary

Survey of the **74 Python sample agents** in [google/adk-samples](https://github.com/google/adk-samples/tree/main/python/agents),
characterized for: **use case**, **complexity**, **architecture pattern**, and the **GCP / Agent
Platform SKUs** each would consume when deployed.

**Why this matters for this project:** it maps the space of agent shapes our cost-estimator harness
will eventually need to handle, and which billable products each shape touches. The SKU column is
**inferred** from each agent's tools/services (READMEs + code), not measured — it predicts the cost
surface to instrument. Baseline for every deployable agent = **Gemini tokens + Agent Runtime
(vCPU/mem) + Sessions**; the table highlights what each adds on top.

Architecture pattern vocabulary: Single-agent · Sequential workflow · Parallel workflow ·
Loop/iterative · Hierarchical (coordinator + sub-agents) · Multi-agent · RAG · Human-in-the-loop (HITL) ·
A2A · Live/bidi-streaming.

---

## Summary stats (n=74)

- **Complexity:** ~High 33, Medium 24, Low 17 — the corpus skews toward multi-stage/orchestrated agents.
- **Most common patterns:** Hierarchical (coordinator + sub-agents) and Sequential workflow dominate;
  Single-agent is common for Low-complexity samples; RAG, HITL, Parallel, Live/bidi appear as add-ons.
- **Beyond the token+runtime+sessions baseline, the frequent extra SKUs are:**
  - **Google Search grounding** — research/fact agents (deep-search, financial-advisor, fomc-research, llm-auditor, supply-chain…)
  - **BigQuery** — data/analytics agents (data-science, data-engineering, cyber-guardian, google-trends, fomc-research…)
  - **Vector Search / RAG Engine + embeddings** — RAG agents (RAG, multiformat-hybrid-rag, software-bug-assistant, personalized-shopping…)
  - **Imagen / Veo (genmedia)** — media generation (genmedia-for-commerce, on-brand-genmedia, image-scoring, short-movie-agents, product-catalog-ad-generation, marketing-agency…)
  - **Memory Bank** — cross-session memory (memory-bank, customer-service, travel-concierge, policy-as-code)
  - **Google Maps grounding** — location agents (travel-concierge, travel-planner-google-maps-mcp, retail-ai-location-strategy, gemma-food-tour-guide)
  - **Cloud Storage** — almost any agent producing artifacts (charts, images, documents)
  - **Live/bidi-streaming Gemini** — realtime voice/video (bidi-demo, realtime-conversational-agent, customer-service)

---

## Full table

| Agent | Use case | Complexity | Architecture pattern | Likely GCP/Agent Platform SKUs |
|---|---|---|---|---|
| RAG | Document Q&A over uploaded corpus | Medium | Single-agent + RAG | Gemini tokens, Vector Search/RAG Engine, embeddings, Agent Runtime, Sessions |
| academic-research | Academic literature analysis & discovery | Medium | Hierarchical | Gemini tokens, Google Search grounding, Agent Runtime, Sessions |
| adk-ae-oauth | OAuth Google Drive file reader | Low | Single-agent (HITL OAuth) | Gemini tokens, Agent Runtime, Sessions, Cloud Storage (Drive API) |
| agent-observability-bq | BigQuery data agent with logging | Medium | Single-agent + tools | Gemini tokens, BigQuery, Agent Runtime, Sessions |
| agent-skills-tutorial | Tutorial: ADK skills patterns | Low | Single-agent (skill toolset) | Gemini tokens, third-party model (API key) |
| ai-security-agent | LLM red-team safety testing | High | Multi-agent (red-team/target/evaluator) | Gemini tokens, Agent Runtime, Sessions |
| airflow_version_upgrade_agent | Airflow DAG migration assistant | High | Hierarchical + RAG | Gemini tokens, Vertex AI Search, BigQuery, Cloud Storage, Google Search grounding, Agent Runtime |
| ambient-expense-agent | Ambient expense report approval | High | Loop/iterative + HITL (graph) | Gemini tokens, Agent Runtime, Sessions, Cloud Storage (Pub/Sub, Cloud Run) |
| antom-payment | Conversational payments & refunds | Low | Single-agent (MCP tools) | Gemini tokens, Agent Runtime, Sessions, third-party MCP |
| auto-insurance-agent | Auto insurance virtual assistant | Medium | Hierarchical | Gemini tokens, Agent Runtime, Sessions (Apigee API hub tools) |
| bidi-demo | Real-time multimodal Live streaming | Medium | Live/bidi-streaming | Gemini tokens (Live), Google Search grounding, Agent Runtime, Sessions |
| blog-writer | Multi-agent technical blog authoring | High | Hierarchical + Sequential | Gemini tokens, Google Search grounding, Agent Runtime, Sessions |
| brand-aligned-presentations | Brand-compliant deck generation | High | Multi-agent + RAG + Parallel + HITL | Gemini tokens, Vertex AI Search, Google Search grounding, Imagen (genmedia), Cloud Storage, Agent Runtime, Sessions |
| brand-aligner | Brand-guideline media evaluation | High | Sequential (multi-agent) | Gemini tokens, Cloud Storage, Vertex AI Eval, embeddings, Agent Runtime, Sessions |
| brand-search-optimization | Retail product title SEO optimization | Medium | Hierarchical | Gemini tokens, BigQuery, Agent Runtime, Sessions (Selenium browsing) |
| camel | Prompt-injection-secure agent execution | High | Multi-agent + Loop (PLLM + quarantined LLM + interpreter) | Gemini tokens, Agent Runtime, Sessions |
| claim-adjudication-agent | Health insurance claim adjudication | High | Hierarchical (parallel + sequential) | Gemini tokens, Agent Runtime, Sessions, Cloud Storage |
| currency-agent | Currency conversion via MCP/A2A | Low | Single-agent + A2A (MCP tool) | Gemini tokens, Agent Runtime, Sessions |
| customer-service | Retail customer service assistant | Medium | Single-agent + Live/bidi-streaming | Gemini tokens, Agent Runtime, Sessions, Memory Bank |
| cyber-guardian-agent | SecOps incident triage/response | High | Hierarchical (orchestrator + 4 sub-agents) + RAG | Gemini tokens, Agent Runtime, Sessions, BigQuery |
| data-engineering | Dataform/BigQuery pipeline development | Medium | Single-agent + multi-tool | Gemini tokens, Agent Runtime, Sessions, BigQuery, Cloud Storage |
| data-science | Multi-source data analysis + BQML | High | Hierarchical (BQ/AlloyDB/BQML sub-agents) | Gemini tokens, Agent Runtime, Sessions, BigQuery, embeddings |
| deep-search | Fullstack deep research report agent | High | Sequential + Loop + HITL | Gemini tokens, Agent Runtime (Cloud Run), Sessions, Google Search grounding |
| earth-engine-geospatial | Geospatial land-cover change analysis | Low | Single-agent (Earth Engine tool) | Gemini tokens, Agent Runtime, Sessions |
| economic-research-agent | Regional economic/site-selection research | High | Multi-agent (consultant + auditor judge), Live-grounded | Gemini tokens, Agent Runtime, Sessions, Google Search grounding (Serper) |
| financial-advisor | Stock analysis & trading strategy advisor | Medium | Hierarchical (coordinator + 4 sub-agents) | Gemini tokens, Agent Runtime, Sessions, Google Search grounding |
| fomc-research | FOMC meeting financial analysis report | High | Hierarchical + Sequential (multimodal) | Gemini tokens, Agent Runtime, Sessions, Google Search grounding, BigQuery, Cloud Storage |
| fun-facts | Fun facts on any topic | Low | Single-agent (search grounding) | Gemini tokens, Agent Runtime, Sessions, Google Search grounding |
| gemini-fullstack | Redirect stub → deep-search | Low | (redirect, no code) | N/A |
| gemma-food-tour-guide | Personalized food tour planner | Medium | Single-agent + Maps grounding (Gemma/AI Studio) | third-party model (Gemma), Google Maps grounding, Agent Runtime, Sessions |
| genmedia-for-commerce | Retail media gen (VTO, 360° product video) | High | Hierarchical (router + sub-agents) + MCP | Gemini tokens, Imagen/Veo (genmedia), Agent Runtime, Sessions, Cloud Storage |
| global-kyc-agent | UK/US KYC & compliance checks | High | Hierarchical router + Sequential + Parallel | Gemini tokens, Agent Runtime, Sessions (Companies House/SEC APIs) |
| google-trends-agent | Surface real-time Google Trends | Medium | Sequential workflow | Gemini tokens, BigQuery, Agent Runtime, Sessions |
| hierarchical-workflow-automation | Cookie delivery order/scheduling automation | High | Hierarchical + Sequential + MCP | Gemini tokens, BigQuery, Agent Runtime, Sessions (Calendar/Gmail MCP) |
| high-volume-document-analyzer | Batch analysis of large document collections | Medium | Single-agent (stateful batched tool) | Gemini tokens (multimodal), Agent Runtime, Sessions, Cloud Storage |
| image-scoring | Generate & policy-validate images iteratively | Medium | Loop/iterative + Sequential | Gemini tokens, Imagen (genmedia), Agent Runtime, Sessions |
| incident-management | ServiceNow incident CRUD via connector | Low | Single-agent (Integration toolset) | Gemini tokens, Agent Runtime, Sessions (ServiceNow connector) |
| invoice-processing | Invoice extraction + learning engine | High | Single-agent (dual-mode) + HITL pipeline | Gemini tokens, Agent Runtime, Sessions, Cloud Storage |
| llm-auditor | Fact-check & rewrite LLM responses | Low | Sequential (critic + reviser) | Gemini tokens, Google Search grounding, Agent Runtime, Sessions |
| machine-learning-engineering | Autonomous ML model building (MLE-STAR) | High | Multi-agent (Sequential + Loop, code exec + retrieval) | Gemini tokens (Pro), Agent Runtime (vCPU/mem code exec), Sessions, Google Search grounding |
| marketing-agency | End-to-end website/branding launch suite | Medium | Hierarchical (AgentTools + sub-agents) | Gemini tokens, Imagen (genmedia), Google Search grounding, Agent Runtime, Sessions |
| medical-pre-authorization | Automate medical pre-auth decisioning | Medium | Hierarchical (AgentTool sub-agents) | Gemini tokens, Agent Runtime, Sessions, Cloud Storage |
| memory-bank | Cross-session memory chat agent | Low | Single-agent + Memory | Gemini tokens, Memory Bank, Agent Runtime, Sessions |
| multiformat-hybrid-rag | Multi-format document Q&A (hybrid RAG) | High | RAG (ingestion pipeline + agent/API/MCP) | Gemini tokens, Vector Search/RAG Engine, embeddings, BigQuery, Cloud Storage, Agent Runtime, Sessions |
| nexshift-agent | AI nurse rostering/scheduling optimizer | High | Hierarchical + Sequential + Parallel + HITL | Gemini tokens, Agent Runtime (vCPU/mem OR-Tools), Sessions |
| nurse-handover | Clinical shift handover ISBAR summaries | Medium | Single-agent (multi-stage summarization) | Gemini tokens, Agent Runtime, Sessions, Cloud Storage |
| on-brand-genmedia | Brand-compliant image gen + scoring | High | Loop/iterative + Hierarchical | Gemini tokens, Imagen/Veo (genmedia), Agent Runtime, Sessions, Cloud Storage |
| order-processing | Order intake with approval workflow | Low | Single-agent + HITL | Gemini tokens, Agent Runtime, Sessions, BigQuery (Application Integration) |
| parallel_task_decomposition_execution | Broadcast goal to Slack/email/calendar | Medium | Parallel + Sequential sub-agents | Gemini tokens, Agent Runtime, Sessions, Google Search grounding, third-party MCP |
| personalized-shopping | E-commerce product recommendations | Medium | Single-agent + RAG (catalog search) | Gemini tokens, Agent Runtime, Sessions, Vector Search/RAG Engine, Cloud Storage |
| plumber-data-engineering-assistant | Build/deploy data pipelines | High | Hierarchical (coordinator + 6 sub-agents) | Gemini tokens, Agent Runtime, Sessions, BigQuery, Cloud Storage, third-party (GitHub) |
| podcast_transcript_agent | Document-to-podcast transcript generation | Medium | Sequential (3 sub-agents) | Gemini tokens, Agent Runtime, Sessions, Cloud Storage |
| policy-as-code | NL data governance policy enforcement | High | Single-agent + RAG/Memory + MCP | Gemini tokens, Agent Runtime, Sessions, Memory Bank, BigQuery, Cloud Storage (Dataplex MCP) |
| product-catalog-ad-generation | Catalog-grounded short video ad generation | High | Hierarchical + HITL | Gemini tokens, Imagen/Veo (genmedia), Lyria audio, Agent Runtime, Sessions, BigQuery, Cloud Storage |
| realtime-conversational-agent | Real-time multimodal voice/video assistant | Medium | Single-agent + Live/bidi-streaming | Gemini tokens (Live native-audio), Agent Runtime, Sessions |
| retail-ai-location-strategy | Retail site-selection strategy pipeline | High | Sequential (7 sub-agents) | Gemini tokens, Imagen (genmedia), Agent Runtime, Sessions, Google Search grounding, Google Maps grounding, Cloud Storage |
| safety-plugins | Reusable safety guardrails (judge + Model Armor) | Medium | Multi-agent + plugins | Gemini tokens, Agent Runtime, Sessions, Model Armor |
| sdlc-task-planner | Break SDLC design into dev task plan | Low | Single-agent | Gemini tokens, Agent Runtime, Sessions, Cloud Storage |
| sdlc-technical-designer | Technical design / ADR generation | Medium | Single-agent + RAG (Spanner graph) | Gemini tokens, Agent Runtime, Sessions, Spanner, Cloud Storage |
| sdlc-user-story-refiner | Refine requirements into user stories | Low | Single-agent (+ optional Spanner) | Gemini tokens, Agent Runtime, Sessions, Spanner (optional), Cloud Storage |
| short-movie-agents | Text-to-video short film generation | High | Hierarchical + Sequential | Gemini tokens, Agent Runtime (vCPU/mem), Sessions, Imagen/Veo (genmedia), Cloud Storage |
| small-business-loan-agent | Automated loan underwriting and pricing | High | Hierarchical + Sequential + HITL | Gemini tokens, Agent Runtime (vCPU/mem), Sessions, Cloud Storage, Firestore |
| software-bug-assistant | IT/dev bug triage and resolution | High | Single-agent + RAG | Gemini tokens, Agent Runtime (vCPU/mem), Sessions, Vector Search/RAG Engine, embeddings, Google Search grounding, Cloud SQL, third-party MCP |
| story_teller | Multi-chapter collaborative story writing | Medium | Sequential + Parallel + Loop | Gemini tokens, Agent Runtime (vCPU/mem), Sessions |
| supply-chain | Energy supply-chain optimization analytics | High | Hierarchical + Multi-agent | Gemini tokens, Agent Runtime (vCPU/mem), Sessions, BigQuery, Google Search grounding, Cloud Storage |
| swe-benchmark-agent | Solving SWE-bench/TerminalBench tasks | Medium | Single-agent (orchestrator + shell tools) | Gemini tokens, Agent Runtime (vCPU/mem), Sessions |
| tau2-benchmark-agent | Customer-service benchmark evaluation | Medium | Single-agent | Gemini tokens, Agent Runtime (vCPU/mem), Sessions |
| travel-concierge | End-to-end travel planning concierge | High | Hierarchical + Multi-agent | Gemini tokens, Agent Runtime (vCPU/mem), Sessions, Memory Bank, Google Maps grounding, Google Search grounding, third-party MCP (Airbnb) |
| travel-planner-google-maps-mcp | Maps-grounded itinerary planning | Medium | Single-agent + MCP | Gemini tokens, Agent Runtime (vCPU/mem), Sessions, Google Maps grounding |
| workflow-concurrent_research_writer | Research + multi-platform blog publishing | High | Sequential + Parallel + conditional routing | Gemini tokens, Agent Runtime (vCPU/mem), Sessions, third-party publish APIs |
| workflow-morning_email_debrief | Scheduled email summary briefing | Low | Sequential (timed trigger) | Gemini tokens, Agent Runtime (vCPU/mem), Sessions, Cloud Scheduler, Gmail API |
| workflows-HITL_concierge | Interactive itinerary refinement | Low | HITL + Loop/iterative | Gemini tokens, Agent Runtime (vCPU/mem), Sessions |
| workflows-sequential | Demo city/time sequential chain | Low | Sequential workflow | Gemini tokens, Agent Runtime (vCPU/mem), Sessions |
| youtube-analyst | YouTube content/channel analytics | Medium | Hierarchical (root + visualization sub-agent) | Gemini tokens, Agent Runtime (vCPU/mem), Sessions, Cloud Storage, YouTube Data API |

---

## Notes & caveats
- **SKUs are inferred**, not measured — they predict the cost surface to instrument, not actual usage.
  Validate per agent with the harness (`usage_metadata` + Cloud Monitoring + Catalog).
- A few agents use stores outside the standard vocabulary: **Spanner** (sdlc-technical-designer/refiner),
  **Cloud SQL/Postgres** (software-bug-assistant), **Firestore** (small-business-loan-agent),
  **Lyria audio** (product-catalog-ad-generation), **Model Armor** (safety-plugins) — listed explicitly.
- `gemini-fullstack` is now a redirect to `deep-search` (no deployable code).
- Some samples run locally on non-GCP equivalents (e.g. local BM25 in personalized-shopping); the SKU
  column reflects the **managed-deploy** mapping (→ Vector Search/RAG Engine).
- **genmedia agents (Imagen/Veo/Lyria) are the priciest cost surface** — per-image/per-second media SKUs
  dwarf text tokens, analogous to how memory ops dominated our EXP-004.

## Source
- [google/adk-samples — python/agents](https://github.com/google/adk-samples/tree/main/python/agents)
