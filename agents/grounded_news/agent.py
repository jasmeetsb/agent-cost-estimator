"""Minimal grounding-enabled agent — validates collect_grounding_usage.

Single tool: ADK's native google_search (Gemini grounded generation). Any query
about current/real-time info should force a grounded web-search request, which
the Monitoring `*web_search_requests_per_publisher` metric captures.
"""

from google.adk.agents import Agent
from google.adk.tools import google_search

root_agent = Agent(
    name="grounded_news",
    model="gemini-2.5-flash",
    description="Answers current-events questions using Google Search grounding.",
    instruction=(
        "You answer questions using fresh web information. ALWAYS use the "
        "google_search tool first, then summarize from the search results. "
        "Cite the sources you used."
    ),
    tools=[google_search],
)
