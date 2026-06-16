"""Multi-Agent Orchestrator archetype — Moderate complexity.

A coordinator that decomposes a request and delegates to specialist sub-agents,
each with its own tool surface — the highest fan-out archetype (agent calls +
many tool calls per turn). Matches the calculator's Multi-Agent Orchestrator /
Moderate column: ~7 turns/query, 60% turns with tools, ~35 tools/turn,
Memory Bank, BigQuery, RAG.

Intended model tier: Gemini 3.0 Flash. Deployed on gemini-2.5-flash.
3 specialist sub-agents (data / analysis / action), each a real ADK sub_agent so
the orchestration exercises agent-call fan-out. Tools are local stand-ins for
BigQuery / RAG / action APIs (those SKUs would bill in production).
"""

from google.adk.agents import Agent
from google.adk.tools import VertexAiSearchTool, load_memory

from .fs_state import save_note, load_note

MODEL = "gemini-2.5-flash"

# Shared synthetic knowledge corpus (Vertex AI Search / RAG).
_DATA_STORE = ("projects/jsb-genai-sa/locations/global/collections/"
               "default_collection/dataStores/agent-knowledge")
corpus_rag = VertexAiSearchTool(data_store_id=_DATA_STORE, bypass_multi_tools_limit=True)


# ---- data specialist tools (would hit BigQuery / RAG) ----
def query_metrics(metric: str, window_days: int) -> dict:
    """Query a business metric over a time window."""
    return {"status": "ok", "metric": metric, "window_days": window_days,
            "values": [100, 112, 98, 130, 145], "trend": "up"}


def fetch_records(entity: str, limit: int) -> dict:
    """Fetch records for an entity (customers, orders, tickets, ...)."""
    return {"status": "ok", "entity": entity, "count": min(limit, 25),
            "sample": [f"{entity}-{i}" for i in range(1, min(limit, 5) + 1)]}


def corpus_search(query: str) -> dict:
    """Search the internal knowledge corpus (RAG)."""
    return {"status": "ok", "query": query,
            "passages": [f"Relevant passage about '{query}' (doc {i})." for i in range(1, 4)]}


# ---- analysis specialist tools ----
def compute_stats(numbers: list[float]) -> dict:
    """Compute summary statistics for a list of numbers."""
    if not numbers:
        return {"status": "error", "message": "empty"}
    n = len(numbers)
    mean = sum(numbers) / n
    return {"status": "ok", "n": n, "mean": mean, "min": min(numbers), "max": max(numbers)}


def detect_trends(series: list[float]) -> dict:
    """Detect the direction of a numeric series."""
    if len(series) < 2:
        return {"status": "ok", "trend": "flat"}
    return {"status": "ok", "trend": "up" if series[-1] > series[0] else "down",
            "change_pct": round(100 * (series[-1] - series[0]) / max(series[0], 1), 1)}


# ---- action specialist tools ----
def draft_summary(topic: str, findings: str) -> dict:
    """Draft an executive summary from findings."""
    return {"status": "ok", "summary": f"Executive summary on {topic}: {findings[:120]}"}


def create_ticket(title: str, priority: str) -> dict:
    """Create a follow-up work ticket."""
    return {"status": "ok", "ticket_id": "TCK-4242", "title": title, "priority": priority}


def send_update(channel: str, message: str) -> dict:
    """Send a status update to a channel."""
    return {"status": "ok", "channel": channel, "sent": True}


data_specialist = Agent(
    name="data_specialist", model=MODEL,
    description="Gathers data: business metrics, records, and internal corpus passages.",
    instruction="You gather data. Use query_metrics and fetch_records for metrics/records, and the "
                "Vertex AI Search RAG tool to retrieve relevant internal corpus passages. Return "
                "the raw findings clearly.",
    tools=[query_metrics, fetch_records, corpus_rag],
)

analysis_specialist = Agent(
    name="analysis_specialist", model=MODEL,
    description="Analyzes gathered data: statistics and trends.",
    instruction="You analyze data. Use compute_stats and detect_trends, then summarize what the "
                "numbers mean.",
    tools=[compute_stats, detect_trends],
)

action_specialist = Agent(
    name="action_specialist", model=MODEL,
    description="Takes actions: drafts summaries, creates tickets, sends updates.",
    instruction="You take actions on analysis results. Use draft_summary, create_ticket, and "
                "send_update as appropriate.",
    tools=[draft_summary, create_ticket, send_update],
)

# NOTE on Agent Sandbox (Code Execution): ADK exposes AgentEngineSandboxCodeExecutor,
# which would exercise the "Agent Sandbox: Code Execution" SKU. We deferred it because
# (a) it has NO per-agent Cloud Monitoring metric (the SKU can't be measured the way we
# measure runtime/memory/grounding), and (b) with no resource name it auto-provisions a
# *separate* Agent Engine at runtime (extra cost + reliability risk). Revisit if/when a
# sandbox allocation metric is exposed. See PROJECT_RUNBOOK.

root_agent = Agent(
    name="multi_agent_orchestrator",
    model=MODEL,
    description="Orchestrator that decomposes a request and routes to data, analysis, and action specialists.",
    instruction=(
        "You are an orchestrator coordinating three specialists. For a request: delegate data "
        "gathering to data_specialist, analysis to analysis_specialist, and any follow-up actions "
        "(summary, ticket, notification) to action_specialist. Sequence them sensibly, pass results "
        "between them, and return one consolidated answer with the findings, the analysis, and the "
        "actions taken. At the start, ALWAYS call load_memory to recall prior memories and use "
        "load_note to recall prior runs on the same subject. Persist the final analysis with "
        "save_note (topic = the subject)."
    ),
    tools=[save_note, load_note, load_memory],
    sub_agents=[data_specialist, analysis_specialist, action_specialist],
)
