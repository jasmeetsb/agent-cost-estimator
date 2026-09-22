# agent-cost-estimator

Deploy an ADK agent to Vertex AI Agent Engine, run a workload against it, and measure
per-interaction usage and cost for every SKU it touches: model tokens, runtime
vCPU/memory, sessions, Memory Bank, Search grounding and image generation.

Unit prices come live from the Cloud Billing Catalog API. Token counts come from each
model call's `usage_metadata`, and runtime and Memory Bank usage from Cloud Monitoring.
Results are catalog list-price estimates, not billed spend.

## Results

13 agents measured on `gemini-2.5-flash`. Cost ranges from **$0.0011 to $0.0932 per
interaction**, driven mostly by architecture (sub-agent fan-out, analysis depth) rather
than by the prompt. See [docs/agent_summaries/MASTER_SUMMARY.md](docs/agent_summaries/MASTER_SUMMARY.md).

## Quick start

```bash
python -m venv .venv && . .venv/bin/activate
pip install "google-cloud-aiplatform[agent_engines,adk]"
gcloud auth application-default login

python src/agent_cost_estimator/pricing.py gemini-2.5-flash              # resolved unit prices
python scripts/harness.py --agent weather_agent --mode local --iters 5   # local, no deploy
python scripts/deploy.py  --agent weather_agent                          # deploy (~5-10 min)
python scripts/harness.py --agent weather_agent --mode remote --iters 5  # deployed engine
python scripts/exp_sample.py --package <pkg> --runs 40 --settle 300      # full SKU experiment
```

Generated reports, caches and deployment state go to `data/`, which is not committed.
Delete engines you no longer need, because an idle engine still accrues runtime cost.

## Layout

| Path | Contents |
|---|---|
| `src/agent_cost_estimator/` | Pricing (Billing Catalog), cost model, usage collectors, transcript parsing |
| `agents/` | Agents under test: in-house demos plus copies from [google/adk-samples](https://github.com/google/adk-samples) ([attribution](agents/ATTRIBUTION.md)) |
| `scripts/` | Deploy, harness, experiments, report and summary builders |
| `docs/` | Runbook, data-collection method, SKU reports, per-agent summaries, calculator reference |

## How a query is priced

- **Tokens:** summed over every model call in the query:
  `prompt × input_rate + (candidates + thinking) × output_rate`.
- **Runtime:** Agent Engine vCPU-seconds and GiB-seconds from Cloud Monitoring.
- **Sessions / Memory Bank / grounding / images:** counted per interaction and priced at the matching SKU.

Full method: [docs/COST_DATA_COLLECTION_PROCESS.md](docs/COST_DATA_COLLECTION_PROCESS.md).
Project history and experiment log: [docs/PROJECT_RUNBOOK.md](docs/PROJECT_RUNBOOK.md).
