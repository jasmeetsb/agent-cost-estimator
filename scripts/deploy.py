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
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AGENTS_DIR = REPO / "agents"
os.chdir(AGENTS_DIR)
sys.path.insert(0, str(AGENTS_DIR))

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

    vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=STAGING)
    print(f"Deploying '{args.agent}' to Agent Engine (builds a container, ~5-10 min)...")
    remote = agent_engines.create(
        agent_engines.AdkApp(agent=root_agent, enable_tracing=True),
        display_name=display,
        requirements=["google-cloud-aiplatform[agent_engines,adk]"],
        extra_packages=[args.agent],
    )
    name = remote.resource_name
    print("DEPLOYED:", name)
    out = DATA / f"deployment_{args.agent}.json"
    out.write_text(json.dumps({"agent": args.agent, "resource_name": name}, indent=2))
    print("Saved to", out)


if __name__ == "__main__":
    main()
