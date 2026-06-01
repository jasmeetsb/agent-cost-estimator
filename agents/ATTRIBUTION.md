# Agent source attribution

The agents under this directory fall into two groups:

## In-house demo agents (built for this project)
- `weather_agent` — minimal 2-tool agent (EXP-001 baseline)
- `research_agent` — coordinator + 2 sub-agent specialists (EXP-002)
- `memory_assistant` — coordinator + Memory Bank + sub-agents (EXP-004/5)
- `grounded_news` — minimal `google_search` agent (grounding collector validation)

## Copied from [google/adk-samples](https://github.com/google/adk-samples) (Apache-2.0)
Each is a verbatim copy of the matching package under
`python/agents/<sample>/<package>/` from upstream; only deployment + experiment
glue is local to this repo.

| Local dir | Upstream sample |
|-----------|-----------------|
| `financial_advisor` | `financial-advisor` |
| `academic_research` | `academic-research` |
| `blogger_agent` | `blog-writer` |
| `marketing_agency` | `marketing-agency` |
| `fomc_research` | `fomc-research` |
| `nexshift_agent` | `nexshift-agent` |
| `on_brand_genmedia` | `on-brand-genmedia` |
| `plumber_agent` | `plumber-data-engineering-assistant` |

Upstream sources retain their original `LICENSE`/`README.md` files where copied.

## Security note on upstream sample code

The copied agents are **verbatim sample/template code**; they have not been
hardened for adversarial inputs. An automated review flagged genuine issues
upstream — SSRF in `fomc_research/tools/fetch_page.py` and `fetch_transcript.py`
(unvalidated URLs), arbitrary GCS overwrite via user-controlled paths in
`plumber_agent/sub_agents/dbt_agent/tools/dbt_model_sql_generator.py`, and git
argument injection / path traversal in
`plumber_agent/sub_agents/github_agent/tools/git_ops.py`.

These findings are real but are **NOT patched here** by design:
- The purpose of including upstream agents is to characterize their actual
  SKU/cost surface; modifying them would diverge from upstream and defeat that.
- The agents are deployed as private Vertex AI Agent Engines in the project's
  internal account, invoked only by this repo's harness with my own test
  prompts — no untrusted callers and no broad IAM write grants.
- The right fix is upstream in `google/adk-samples`, not in this fork.

If any of these agents is ever taken beyond a contained cost-experiment
deployment, the listed files MUST be reviewed and hardened before use.
