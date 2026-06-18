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

"""Academic_Research: Research advice, related literature finding, research area proposals, web knowledge access."""

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import VertexAiSearchTool, load_memory

from . import prompt
from .fs_state import save_note, load_note
from .sub_agents.academic_newresearch import academic_newresearch_agent
from .sub_agents.academic_websearch import academic_websearch_agent

MODEL = "gemini-2.5-flash"

# Shared synthetic knowledge corpus (Vertex AI Search / RAG) — the research/tech
# briefs (transformers, RAG, vector DBs, batteries, etc.) live in `agent-knowledge`.
_DATA_STORE = ("projects/jsb-genai-sa/locations/global/collections/"
               "default_collection/dataStores/agent-knowledge")
corpus_rag = VertexAiSearchTool(data_store_id=_DATA_STORE, bypass_multi_tools_limit=True)

# Addendum so the coordinator exercises the state + retrieval SKUs (web search via
# the academic_websearch AgentTool already grounds on Google Search).
_SKU_ADDENDUM = (
    "\n\nAdditionally: at the start, ALWAYS call load_memory to recall prior research sessions and "
    "load_note (topic = the paper/research subject) to recall prior work. Consult the internal "
    "corpus via the Vertex AI Search tool for relevant reference "
    "briefs, and use the academic_websearch tool for current papers. When done, persist the key "
    "findings with save_note (topic = the subject)."
)


academic_coordinator = LlmAgent(
    name="academic_coordinator",
    model=MODEL,
    description=(
        "analyzing seminal papers provided by the users, "
        "providing research advice, locating current papers "
        "relevant to the seminal paper, generating suggestions "
        "for new research directions, and accessing web resources "
        "to acquire knowledge"
    ),
    instruction=prompt.ACADEMIC_COORDINATOR_PROMPT + _SKU_ADDENDUM,
    output_key="seminal_paper",
    tools=[
        AgentTool(agent=academic_websearch_agent),
        AgentTool(agent=academic_newresearch_agent),
        save_note,
        load_note,
        load_memory,
        corpus_rag,
    ],
)

root_agent = academic_coordinator

# Two-model split: coordinator -> gemini-3.5-flash, all sub-agents/tools -> gemini-3.1-flash-lite
# (both via the global Vertex endpoint). Lets Cloud Monitoring token_count split master vs sub.
import os as _os  # noqa: E402
if _os.environ.get("COST_TWO_MODEL") == "1":  # canonical default = single gemini-2.5-flash
    from ._gmodel import apply_split  # noqa: E402
    apply_split(root_agent)
