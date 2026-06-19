"""Core agent module for orchestrating sub-agents."""

from google.adk.agents import Agent
from google.adk.tools import google_search, VertexAiSearchTool, load_memory
from google.adk.tools.agent_tool import AgentTool
from google.genai import types

from .constants import MODEL
from .fs_state import save_note, load_note
from .prompts import AGENT_INSTRUCTIONS

# Internal reference corpus (Vertex AI Search / RAG) — data-engineering briefs (de-*).
_DATA_STORE = ("projects/jsb-genai-sa/locations/global/collections/"
               "default_collection/dataStores/agent-knowledge")
plumber_rag = VertexAiSearchTool(data_store_id=_DATA_STORE, bypass_multi_tools_limit=True)

# Dedicated web-research agent (Google Search grounding) as an AgentTool (sole tool =
# google_search; wired as AgentTool, not sub_agent, so it actually runs in the deployed stream).
web_research_agent = Agent(
    name="web_research_agent", model=MODEL,
    description="Researches the live web (Google Search) for current data-engineering facts.",
    instruction="Use google_search to gather current, accurate data-engineering and GCP "
                "information, then return organized findings with the sources you used.",
    tools=[google_search],
)
web_research_tool = AgentTool(agent=web_research_agent)

_TOOL_PREAMBLE = (
    "MANDATORY FIRST STEPS — you MUST do ALL of these, in order, BEFORE routing to any sub-agent "
    "or answering, on every request:\n"
    "1) Call load_memory to recall prior memories about this user.\n"
    "2) Call load_note (topic = the pipeline or project) for any prior designs.\n"
    "3) Call the Vertex AI Search tool to retrieve relevant data-engineering reference material.\n"
    "4) Call the web_research_agent tool for current best practices from the live web.\n"
    "Only AFTER completing steps 1-4 do you route to a sub-agent / answer as described below. When "
    "you finish, you MUST call save_note (topic = the pipeline or project) to persist the key design.\n\n"
    "=== YOUR TASK ===\n"
)

# Import root_agents from each subagent.
from .sub_agents.dataflow_agent.agent import root_agent as dataflow_agent
from .sub_agents.dataproc_agent.agent import root_agent as dataproc_agent
from .sub_agents.dataproc_template_agent.agent import (
    root_agent as dataproc_template_agent,
)
from .sub_agents.dbt_agent.agent import root_agent as dbt_agent
from .sub_agents.github_agent.agent import root_agent as github_agent
from .sub_agents.monitoring_agent.agent import root_agent as monitoring_agent

root_agent = Agent(
    name="plumber_agent",
    model=MODEL,
    description=(
        "A main orchestrator that intelligently routes user requests to "
        "specialized sub-agents. It delegates tasks across key domains: data "
        "processing (Dataflow, Dataproc clusters & templates), data "
        "transformation (**dbt**), code & file management "
        "(GitHub, GCS), and cloud observability (Monitoring logs & metrics)."
    ),
    instruction=_TOOL_PREAMBLE + AGENT_INSTRUCTIONS,
    tools=[save_note, load_note, load_memory, plumber_rag, web_research_tool],
    sub_agents=[
        dataflow_agent,
        dataproc_agent,
        dataproc_template_agent,
        dbt_agent,
        github_agent,
        monitoring_agent,
    ],
    generate_content_config=types.GenerateContentConfig(
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
        ]
    ),
)

# Two-model split when COST_TWO_MODEL=1; default deploy = single gemini-2.5-flash.
import os as _os  # noqa: E402
from ._gmodel import apply_split, apply_uniform  # noqa: E402
if _os.environ.get("COST_TWO_MODEL") == "1":
    apply_split(root_agent)
else:
    apply_uniform(root_agent, "gemini-2.5-flash")
