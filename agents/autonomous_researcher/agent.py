"""Autonomous Researcher archetype — Moderate complexity.

Deep-research agent: plans, web-searches (Google Search grounding), persists
findings to Firestore, and synthesizes a long report. Matches the calculator's
Autonomous Researcher / Moderate column: low query volume, long outputs
(~5000 tok), Search grounding, premium model.

Restructured as a coordinator + a `web_researcher` sub-agent so the agent can
use BOTH Google Search grounding (which, as a built-in tool, must be the sole
tool on its agent) AND Firestore function tools (on the coordinator). Intended
model tier: Gemini 3.1 Pro (≤200k). Deployed on gemini-2.5-flash for parity.
"""

from google.adk.agents import Agent
from google.adk.tools import google_search, VertexAiSearchTool
from google.adk.tools.agent_tool import AgentTool

from .fs_state import save_note, load_note

MODEL = "gemini-2.5-flash"

# Shared synthetic knowledge corpus (Vertex AI Search / RAG) — internal references
# to complement live web search.
_DATA_STORE = ("projects/jsb-genai-sa/locations/global/collections/"
               "default_collection/dataStores/agent-knowledge")
corpus_rag = VertexAiSearchTool(data_store_id=_DATA_STORE, bypass_multi_tools_limit=True)

# Search grounding lives on its own agent (built-in google_search can't be
# combined with function tools on the same agent). It is exposed to the
# coordinator as an AgentTool — NOT a sub_agent — so the coordinator CALLS it
# and gets the web findings back inline, then synthesizes. (With sub_agents/
# transfer, the coordinator hands off control and google_search never actually
# runs in the deployed stream_query, so web-search grounding is never exercised.)
web_researcher = Agent(
    name="web_researcher",
    model=MODEL,
    description="Searches the web with Google Search grounding and returns cited findings.",
    instruction=(
        "You are a web research specialist. ALWAYS use the google_search tool to gather current "
        "information across multiple angles of the question, then return well-organized findings "
        "with the sources you used."
    ),
    tools=[google_search],
)
web_research_tool = AgentTool(agent=web_researcher)

root_agent = Agent(
    name="autonomous_researcher",
    model=MODEL,
    description="Autonomous research analyst that web-searches and synthesizes long, cited reports.",
    instruction=(
        "You are an autonomous research analyst. For any question: (1) briefly plan the angles to "
        "investigate, (2) use load_note (topic = the subject) to recall prior research and consult "
        "the internal corpus via the Vertex AI Search RAG tool for reference briefs, "
        "(3) call the web_researcher tool to gather current information from the web (always do this "
        "for current/recent questions), (4) synthesize a thorough, well-structured report with "
        "sections, an executive summary, and cited sources, and (5) persist the key findings with "
        "save_note (topic = the subject). Be comprehensive and detailed — depth is expected."
    ),
    tools=[save_note, load_note, corpus_rag, web_research_tool],
)
