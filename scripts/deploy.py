"""Deploy the weather agent to Vertex AI Agent Engine and save its resource name."""

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AGENTS_DIR = REPO / "agents"
# Run from the agents/ dir so the agent ships as the `weather_agent` package and
# its serialized module reference (weather_agent.agent) resolves in the container.
os.chdir(AGENTS_DIR)
sys.path.insert(0, str(AGENTS_DIR))

import vertexai
from vertexai import agent_engines

from weather_agent.agent import root_agent

PROJECT = "jsb-genai-sa"
LOCATION = "us-central1"
STAGING = "gs://jsb-genai-sa-staging"
OUT = REPO / "data" / "deployment.json"


def main():
    vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=STAGING)
    print("Deploying to Agent Engine (this builds a container, ~5-10 min)...")
    remote = agent_engines.create(
        agent_engines.AdkApp(agent=root_agent, enable_tracing=True),
        display_name="weather_agent_cost_demo",
        requirements=["google-cloud-aiplatform[agent_engines,adk]"],
        extra_packages=["weather_agent"],
    )
    name = remote.resource_name
    print("DEPLOYED:", name)
    OUT.write_text(json.dumps({"resource_name": name}, indent=2))
    print("Saved to", OUT)


if __name__ == "__main__":
    main()
