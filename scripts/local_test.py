"""Run the agent locally once and dump the usage_metadata structure."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agents"))

import vertexai
from vertexai.preview import reasoning_engines

from weather_agent.agent import root_agent

PROJECT = "jsb-genai-sa"
LOCATION = "us-central1"


def main():
    vertexai.init(project=PROJECT, location=LOCATION,
                  staging_bucket="gs://jsb-genai-sa-staging")
    app = reasoning_engines.AdkApp(agent=root_agent)
    for event in app.stream_query(
        user_id="local-test",
        message="What's the weather in Tokyo?",
    ):
        print("EVENT:", event)


if __name__ == "__main__":
    main()
