# agent-cost-estimator

Harness that deploys an ADK agent to GCP and estimates its average cost per query
from live SKU pricing + per-query token usage. Goal: feed it an agent architecture,
deploy it, run N iterations, get an average cost-per-query estimate.

## Environment
- GCP project: `jsb-genai-sa` (internal `@google.com` corp project)
- Region: `us-central1` | Staging bucket: `gs://jsb-genai-sa-staging` (us-central1)
- Always activate the venv first: `. .venv/bin/activate`
- ADK 1.34.1, `google-cloud-aiplatform[agent_engines,adk]`

## Commands
```bash
. .venv/bin/activate
python src/agent_cost_estimator/pricing.py gemini-2.5-flash   # inspect resolved prices
python scripts/harness.py --mode local  --iters 5             # no deploy needed
python scripts/deploy.py                                       # deploy to Agent Engine (~5-10 min)
python scripts/harness.py --mode remote --iters 5             # query deployed endpoint
```

## Architecture
- `src/agent_cost_estimator/pricing.py` — pulls per-token & runtime unit prices from the
  Cloud Billing **Catalog API** (`cloudbilling.googleapis.com/v1/services/{id}/skus`).
  Vertex AI service id = `C7E2-9256-1C43`. Caches the raw SKU pull to `data/sku_cache.json` (24h).
- `src/agent_cost_estimator/cost.py` — parses ADK `usage_metadata` into a per-query cost
  breakdown and aggregates averages over a run.
- `agents/weather_agent/` — the sample ADK agent (`root_agent`).
- `scripts/` — `deploy.py`, `harness.py`, `local_test.py`.
- `data/` — generated artifacts (reports, cache, deployment.json). Not source.

## Cost model (how a query is priced)
- **Token cost** = Σ over every model call in the query of
  `prompt_tokens × input_rate + (candidates + thoughts) × output_rate`.
- **Runtime cost** = prorated Agent Engine vCPU/memory-seconds over query latency
  (assumes 1 vCPU + 1 GiB; this is an upper bound, not actual billed instance-time).

## Gotchas (learned the hard way)
- **One query = multiple model calls.** A tool-using query emits 2+ events, each with its
  own `usage_metadata`. Sum them; don't read only the last event.
- **Thinking tokens** (`thoughts_token_count`) are separate from `candidates_token_count`
  and bill at the **output** rate. Include them.
- **Deploy serialization**: tool functions defined in a module serialize *by reference*, so
  the module must exist in the container. `deploy.py` `os.chdir`es into `agents/` and passes
  `extra_packages=["weather_agent"]` so it lands at `/code/weather_agent`. Without this the
  engine builds but fails to start with `ModuleNotFoundError: No module named 'weather_agent'`.
- **Pin `google-adk` to the local version on deploy.** The agent is cloudpickled with the local
  ADK; if the container's `[adk]` extra pulls a newer ADK, every query crashes at runtime
  (`AttributeError: 'LlmAgent' object has no attribute 'mode'`) and returns EMPTY event streams
  (0 tokens, no exception). `deploy.py` pins `google-adk==<local>`. Symptom of the mismatch:
  deploy succeeds + smoke test may pass once, but experiment runs return all-empty.
- **NEVER deploy engines concurrently.** `agent_engines.create()` stages to a fixed GCS path
  (`agent_engine/*`); parallel deploys race and cross-contaminate (one engine gets another's
  tarball → wrong-module errors). Deploy sequentially.
- **Agent Engine query quota = 90 req/min/project/region** ("Query Reasoning Engine requests"),
  shared across all engines. Over-limit `stream_query` sometimes 429s, sometimes returns an empty
  stream silently. `exp_sample.py` retries both (backoff) and paces with `--delay`.
- **REST auth uses ADC, not the gcloud CLI.** `pricing.py`/`usage.py` get tokens via `google.auth`
  default creds (robust to gcloud CLI credential expiry / Context Aware Access).
- **SKU name collisions**: "gemini 2.5 flash" substring-matches "flash lite"; preview vs **GA**
  SKUs have different prices. `pricing.py` filters lite and scores GA highest — keep that logic.
- **Costs are catalog-price estimates, not billed dollars.** True spend only comes from
  BigQuery billing export, which is NOT set up and is likely locked on this shared corp billing
  account. The standard Cloud Billing API returns no spend amounts.
- A deployed Agent Engine accrues idle runtime cost. Tear down unused engines (`engine.delete(force=True)`).
- **Firestore client needs the project ID, not the number.** Agent Engine sets `GOOGLE_CLOUD_PROJECT`
  to the project *number* (436848677253); `firestore.Client()` defaulting to that 404s ("database does
  not exist"). `fs_state.py` reads `FIRESTORE_PROJECT_ID` (the string id `jsb-genai-sa`). Symptom: writes
  silently fail in the container but `save_note`/`load_note` function_calls still appear in events (so the
  op *count* looks right while nothing lands). Verify by querying Firestore directly after a run, not by
  counting tool calls.
- **RAG ingestion: inline `raw_bytes` is rejected; use GCS + a JSONL manifest.** Importing unstructured
  docs into a GENERIC/CONTENT_REQUIRED Vertex AI Search datastore via `InlineSource(raw_bytes=...)` fails
  per-document ("document.data is a required field") and the LRO still reports success — datastore ends up
  empty. `setup_rag.py` uploads each doc as a `.txt` to GCS and imports a JSONL manifest with
  `content.uri` + `data_schema="document"`. It self-verifies (doc count + sample search).
- **RAG search 403 from the deployed agent.** The Reasoning Engine runtime SA
  (`service-436848677253@gcp-sa-aiplatform-re.iam.gserviceaccount.com`) needs `roles/discoveryengine.viewer`
  to call `discoveryengine.servingConfigs.search`. Datastore searchable via your ADC ≠ searchable by the
  agent. Same SA also holds `roles/datastore.user` (Firestore). Grant via REST setIamPolicy (gcloud CLI
  auth is often stale; ADC works).
- **Built-in tools (`google_search`) must be an `AgentTool`, not a `sub_agent`, to actually run.** A
  built-in tool can't be combined with function tools on one agent, so it lives on its own agent. If that
  agent is wired via `sub_agents` (LLM `transfer_to_agent`), the deployed `stream_query` hands off control
  and the built-in tool **never executes** (stream ends after the transfer; 0 grounding). Wrap it as
  `AgentTool(agent=...)` and put it in `tools=[...]` so the coordinator *calls* it and gets results back.
- **Native `google_search` grounding is not metered by `web_search_requests` Monitoring metric** (tracks a
  different "Web Grounding for Enterprise" path) and its `grounding_metadata` is encapsulated inside an
  AgentTool (not in the parent stream). Count the `web_researcher` AgentTool invocations from the transcript
  as the grounded-query-turn unit instead.
- **Redirected stdout is block-buffered.** A long `exp_sample.py` run writing to a file shows 0 bytes until
  it exits (flush on exit), so progress looks stuck. Run with `python -u` for live progress; to check a
  detached run is alive, watch `/proc/<pid>/stat` CPU ticks, not the log size.

## PROTECTED RESOURCES — DO NOT DELETE
- **`reasoningEngines/105003910208421888` ("Beads Issue Tracker")** belongs to separate work and
  happens to live in this same project (`jsb-genai-sa` / 436848677253). **NEVER delete it.**
- When tearing down experiment engines, delete ONLY by explicit ID allowlist
  (weather/research/memory_assistant from `data/deployment_*.json`). NEVER use a "list all and
  delete" pattern against this project — it would catch Beads.

## Conventions
- No co-authorship/AI attribution in commits.
- Don't commit `data/` artifacts or `.venv/`.
