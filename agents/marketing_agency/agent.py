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
# limitations under the License.

"""Marketing_coordinator Agent assists in creating effective online content."""

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import VertexAiSearchTool, google_search, load_memory

from . import prompt
from .fs_state import save_note, load_note
from .sub_agents.domain_create import domain_create_agent
from .sub_agents.logo_create import logo_create_agent
from .sub_agents.marketing_create import marketing_create_agent
from .sub_agents.website_create import website_create_agent

MODEL = "gemini-2.5-flash"

# Shared synthetic knowledge corpus (Vertex AI Search / RAG) — brand/marketing
# briefs (brand strategy, naming, channels, landing pages, SEO, social) were added
# to `agent-knowledge`.
_DATA_STORE = ("projects/jsb-genai-sa/locations/global/collections/"
               "default_collection/dataStores/agent-knowledge")
brand_rag = VertexAiSearchTool(data_store_id=_DATA_STORE, bypass_multi_tools_limit=True)

# Dedicated web-research agent (Google Search grounding) exposed as an AgentTool, so the
# coordinator CALLS it for live market/competitor/trend research and the grounding SKU is
# actually exercised + countable. (google_search must be the sole tool on its own agent.)
web_research_agent = LlmAgent(
    name="web_research_agent", model=MODEL,
    description="Researches the live web (Google Search) for market, competitor, and trend info.",
    instruction="Use google_search to gather current market/competitor/trend information for the "
                "brief, then return organized findings with the sources you used.",
    tools=[google_search],
)
web_research_tool = AgentTool(agent=web_research_agent)

# Addendum so the coordinator exercises the state + retrieval SKUs.
_SKU_ADDENDUM = (
    "\n\nAdditionally: at the start, ALWAYS call load_memory to recall prior work with this client and "
    "load_note (topic = the brand/project name) to recall prior "
    "work. ALWAYS call the web_research_agent tool to research the live market/competitors/trends for "
    "the brand. Use the Vertex AI Search tool to retrieve relevant brand/marketing best-practice briefs "
    "(brand strategy, naming, channels, landing pages, SEO, social) before advising. When done, "
    "persist a concise brand summary with save_note (topic = the brand/project name)."
)

marketing_coordinator = LlmAgent(
    name="marketing_coordinator",
    model=MODEL,
    description=(
        "Establish a powerful online presence and connect with your audience "
        "effectively. Guide you through defining your digital identity, from "
        "choosing the perfect domain name and crafting a professional "
        "website, to strategizing online marketing campaigns, "
        "designing a memorable logo, and creating engaging short videos"
    ),
    instruction=prompt.MARKETING_COORDINATOR_PROMPT + _SKU_ADDENDUM,
    tools=[
        AgentTool(agent=domain_create_agent),
        AgentTool(agent=website_create_agent),
        AgentTool(agent=marketing_create_agent),
        AgentTool(agent=logo_create_agent),
        save_note,
        load_note,
        load_memory,
        brand_rag,
        web_research_tool,
    ],
)

root_agent = marketing_coordinator
