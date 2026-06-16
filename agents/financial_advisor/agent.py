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

"""Financial coordinator: provide reasonable investment strategies."""

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import VertexAiSearchTool, load_memory

from . import prompt
from .fs_state import save_note, load_note
from .sub_agents.data_analyst import data_analyst_agent
from .sub_agents.execution_analyst import execution_analyst_agent
from .sub_agents.risk_analyst import risk_analyst_agent
from .sub_agents.trading_analyst import trading_analyst_agent

MODEL = "gemini-2.5-flash"

# Shared synthetic knowledge corpus (Vertex AI Search / RAG) — finance briefs
# (valuation, risk, strategies, macro, sectors) were added to `agent-knowledge`.
_DATA_STORE = ("projects/jsb-genai-sa/locations/global/collections/"
               "default_collection/dataStores/agent-knowledge")
market_rag = VertexAiSearchTool(data_store_id=_DATA_STORE, bypass_multi_tools_limit=True)

# Addendum so the coordinator exercises the state + retrieval SKUs.
_SKU_ADDENDUM = (
    "\n\nAdditionally: at the start, ALWAYS call load_memory to recall prior conversations with this "
    "investor and load_note (topic = the ticker symbol) to recall any "
    "prior analysis. Use the Vertex AI Search tool to retrieve relevant background market/finance "
    "knowledge (valuation, risk, strategy, macro, sector briefs) before advising. When the analysis "
    "is complete, persist a concise summary with save_note (topic = the ticker symbol)."
)


financial_coordinator = LlmAgent(
    name="financial_coordinator",
    model=MODEL,
    description=(
        "guide users through a structured process to receive financial "
        "advice by orchestrating a series of expert subagents. help them "
        "analyze a market ticker, develop trading strategies, define "
        "execution plans, and evaluate the overall risk."
    ),
    instruction=prompt.FINANCIAL_COORDINATOR_PROMPT + _SKU_ADDENDUM,
    output_key="financial_coordinator_output",
    tools=[
        AgentTool(agent=data_analyst_agent),
        AgentTool(agent=trading_analyst_agent),
        AgentTool(agent=execution_analyst_agent),
        AgentTool(agent=risk_analyst_agent),
        save_note,
        load_note,
        load_memory,
        market_rag,
    ],
)

root_agent = financial_coordinator
