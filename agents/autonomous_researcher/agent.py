"""Autonomous Researcher archetype — Moderate complexity.

Deep-research agent: plans, searches the web via Google Search grounding, and
synthesizes a long report. Matches the calculator's Autonomous Researcher /
Moderate column: low query volume, long outputs (~5000 tok), Search grounding,
premium model.

Intended model tier: Gemini 3.1 Pro (≤200k). Deployed on gemini-2.5-flash for
parity. NOTE: uses ADK's built-in google_search tool, which (for Gemini models)
must be the agent's sole tool — so internal-corpus RAG (Vertex AI Search) is
deferred to the High variant where a datastore is provisioned; here the agent
grounds on public web search only.
"""

from google.adk.agents import Agent
from google.adk.tools import google_search

MODEL = "gemini-2.5-flash"

root_agent = Agent(
    name="autonomous_researcher",
    model=MODEL,
    description="Autonomous research agent that web-searches and synthesizes long, cited reports.",
    instruction=(
        "You are an autonomous research analyst. For any question: (1) briefly plan the angles to "
        "investigate, (2) ALWAYS use the google_search tool to gather current information across "
        "multiple angles, (3) synthesize a thorough, well-structured report with sections and a "
        "short executive summary, and (4) cite the sources you used. Be comprehensive and detailed "
        "— depth is expected."
    ),
    tools=[google_search],
)
