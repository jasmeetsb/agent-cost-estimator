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
- **SKU name collisions**: "gemini 2.5 flash" substring-matches "flash lite"; preview vs **GA**
  SKUs have different prices. `pricing.py` filters lite and scores GA highest — keep that logic.
- **Costs are catalog-price estimates, not billed dollars.** True spend only comes from
  BigQuery billing export, which is NOT set up and is likely locked on this shared corp billing
  account. The standard Cloud Billing API returns no spend amounts.
- A deployed Agent Engine accrues idle runtime cost. Tear down unused engines (`engine.delete(force=True)`).

## PROTECTED RESOURCES — DO NOT DELETE
- **`reasoningEngines/105003910208421888` ("Beads Issue Tracker")** belongs to separate work and
  happens to live in this same project (`jsb-genai-sa` / 436848677253). **NEVER delete it.**
- When tearing down experiment engines, delete ONLY by explicit ID allowlist
  (weather/research/memory_assistant from `data/deployment_*.json`). NEVER use a "list all and
  delete" pattern against this project — it would catch Beads.

## Conventions
- No co-authorship/AI attribution in commits.
- Don't commit `data/` artifacts or `.venv/`.
