# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License

"""FOMC Research sample agent."""

import logging
import warnings

from google.adk.agents import Agent
from google.adk.tools import google_search, VertexAiSearchTool, load_memory
from google.adk.tools.agent_tool import AgentTool

from . import MODEL, root_agent_prompt
from .fs_state import save_note, load_note
from .shared_libraries.callbacks import rate_limit_callback
from .sub_agents.analysis_agent import AnalysisAgent
from .sub_agents.research_agent import ResearchAgent
from .sub_agents.retrieve_meeting_data_agent import RetrieveMeetingDataAgent
from .tools.store_state import store_state_tool

# Internal reference corpus (Vertex AI Search / RAG) — economic/FOMC briefs (fomc-*).
_DATA_STORE = ("projects/jsb-genai-sa/locations/global/collections/"
               "default_collection/dataStores/agent-knowledge")
fomc_rag = VertexAiSearchTool(data_store_id=_DATA_STORE, bypass_multi_tools_limit=True)

# Dedicated web-research agent (Google Search grounding) as an AgentTool — the coordinator
# CALLS it for current economic/FOMC facts. google_search must be the sole tool on its agent
# and wired as AgentTool (not sub_agent) or it never runs in the deployed stream.
web_research_agent = Agent(
    name="web_research_agent", model=MODEL,
    description="Researches the live web (Google Search) for current economic/FOMC facts.",
    instruction="Use google_search to gather current, accurate economic and FOMC-related "
                "information across multiple angles, then return organized findings with the "
                "sources you used.",
    tools=[google_search],
)
web_research_tool = AgentTool(agent=web_research_agent)

_TOOL_PREAMBLE = (
    "MANDATORY FIRST STEPS — you MUST do ALL of these, in order, before anything else on every "
    "request:\n"
    "1) Call load_memory to recall prior memories about this user.\n"
    "2) Call load_note (topic = the meeting or subject) for any prior findings.\n"
    "3) Call the Vertex AI Search tool to retrieve relevant reference briefs from the internal corpus.\n"
    "4) Call the web_research_agent tool to gather current economic/FOMC information from the live web.\n"
    "Only AFTER completing steps 1-4 do you proceed with the analysis described below. When you "
    "finish, you MUST call save_note (topic = the meeting or subject) to persist the key findings.\n\n"
    "=== YOUR TASK ===\n"
)

warnings.filterwarnings("ignore", category=UserWarning, module=".*pydantic.*")

logger = logging.getLogger(__name__)
logger.debug("Using MODEL: %s", MODEL)


root_agent = Agent(
    model=MODEL,
    name="root_agent",
    description=(
        "Use tools and other agents provided to generate an analysis report"
        "about the most recent FOMC meeting."
    ),
    instruction=_TOOL_PREAMBLE + root_agent_prompt.PROMPT,
    tools=[store_state_tool, save_note, load_note, load_memory, fomc_rag, web_research_tool],
    sub_agents=[
        RetrieveMeetingDataAgent,
        ResearchAgent,
        AnalysisAgent,
    ],
    before_model_callback=rate_limit_callback,
)

# Two-model split when COST_TWO_MODEL=1; default deploy = single gemini-2.5-flash.
import os as _os  # noqa: E402
from ._gmodel import apply_split, apply_uniform  # noqa: E402
if _os.environ.get("COST_TWO_MODEL") == "1":
    apply_split(root_agent)
else:
    apply_uniform(root_agent, "gemini-2.5-flash")
