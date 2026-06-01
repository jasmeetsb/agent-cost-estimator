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
