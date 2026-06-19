"""Deploy an ADK agent to Vertex AI Agent Engine and record its resource name.

Usage:
  python scripts/deploy.py --agent weather_agent
  python scripts/deploy.py --agent research_agent --display-name research_cost_demo

The agent must live at agents/<agent>/agent.py exposing `root_agent`. We run from
agents/ so the package ships as `<agent>` and its serialized module reference
(<agent>.agent) resolves inside the container.
"""

import argparse
import importlib
import json
import os
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AGENTS_DIR = REPO / "agents"
os.chdir(AGENTS_DIR)
sys.path.insert(0, str(AGENTS_DIR))

# adk-sample agents carry their own third-party deps (e.g. fomc needs diff-match-patch +
# pdfplumber; plumber needs apache-beam + GitPython; on_brand needs scikit-learn). These live
# in the ORIGINAL sample's pyproject.toml. We ship our modified package from agents/ but pull
# the sample's runtime deps so the container can import + start. Without them the engine builds
# but crashes on startup (ModuleNotFoundError → "failed to start and cannot serve traffic").
_SAMPLES = Path("/home/jasmeetbhatia/github/adk-samples/python/agents")
_SAMPLE_DIR = {
    "fomc_research": "fomc-research",
    "plumber_agent": "plumber-data-engineering-assistant",
    "on_brand_genmedia": "on-brand-genmedia",
}
_DEV = ("pytest", "ruff", "mypy", "codespell", "types-", "agent-starter-pack", "black",
        "isort", "pre-commit", "ipykernel", "jupyter", "pylint", "locust", "streamlit")
# deploy.py already provides these (pinned) — don't let the sample's versions conflict.
_BASE_PROVIDED = ("google-adk", "google-cloud-aiplatform", "google-genai")


def extra_sample_reqs(agent: str) -> list:
    sd = _SAMPLE_DIR.get(agent)
    if not sd:
        return []
    pp = _SAMPLES / sd / "pyproject.toml"
    if not pp.exists():
        return []
    with pp.open("rb") as f:
        data = tomllib.load(f)
    out = []
    for q in (data.get("project", {}) or {}).get("dependencies", []) or []:
        ql = q.lower()
        if any(d in ql for d in _DEV):
            continue
        if any(ql.startswith(b) for b in _BASE_PROVIDED):
            continue
        out.append(q)
    return out

import vertexai
from vertexai import agent_engines

PROJECT = "jsb-genai-sa"
LOCATION = "us-central1"
STAGING = "gs://jsb-genai-sa-staging"
DATA = REPO / "data"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True, help="package name under agents/")
    ap.add_argument("--display-name", default=None)
    args = ap.parse_args()

    root_agent = importlib.import_module(f"{args.agent}.agent").root_agent
    display = args.display_name or f"{args.agent}_cost_demo"

    # Pin google-adk to the LOCAL version: the agent is cloudpickled with the
    # local ADK, and the container must run the same version or it crashes at
    # query time (e.g. AttributeError: 'LlmAgent' object has no attribute 'mode'
    # when the container's newer ADK reads a field the pickled object lacks).
    import importlib.metadata as _md
    adk_ver = _md.version("google-adk")
    reqs = ["google-cloud-aiplatform[agent_engines,adk]", f"google-adk=={adk_ver}",
            "google-cloud-firestore"]  # archetype agents persist state to Firestore
    reqs += extra_sample_reqs(args.agent)  # sample-specific runtime deps (fomc/plumber/on_brand)

    vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=STAGING)
    print(f"Deploying '{args.agent}' to Agent Engine (builds a container, ~5-10 min)... "
          f"pinning google-adk=={adk_ver}")
    remote = agent_engines.create(
        agent_engines.AdkApp(agent=root_agent, enable_tracing=True),
        display_name=display,
        requirements=reqs,
        extra_packages=[args.agent],
    )
    name = remote.resource_name
    print("DEPLOYED:", name)
    out = DATA / f"deployment_{args.agent}.json"
    out.write_text(json.dumps({"agent": args.agent, "resource_name": name}, indent=2))
    print("Saved to", out)


if __name__ == "__main__":
    main()
