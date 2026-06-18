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

import datetime

from google.adk.agents import Agent
from google.adk.tools import FunctionTool, VertexAiSearchTool, google_search, load_memory
from google.adk.tools.agent_tool import AgentTool

from .config import config
from .fs_state import save_note, load_note
from .sub_agents import (
    blog_editor,
    robust_blog_planner,
    robust_blog_writer,
    social_media_writer,
)
from .tools import analyze_codebase, save_blog_post_to_file

# Shared synthetic knowledge corpus (Vertex AI Search / RAG) — the tech briefs
# (RAG, vector DBs, transformers, etc.) in `agent-knowledge` are relevant source
# material for technical blog posts.
_DATA_STORE = ("projects/jsb-genai-sa/locations/global/collections/"
               "default_collection/dataStores/agent-knowledge")
blog_rag = VertexAiSearchTool(data_store_id=_DATA_STORE, bypass_multi_tools_limit=True)

# Dedicated web-research agent (Google Search grounding) as an AgentTool, so the blogger
# CALLS it to research the topic on the live web before planning/writing — exercising the
# grounding SKU countably. (blog_writer/blog_planner also have google_search but are wired
# as sub_agents/transfer, which doesn't reliably execute it.)
web_research_agent = Agent(
    name="web_research_agent", model=config.worker_model,
    description="Researches the live web (Google Search) for current facts on the blog topic.",
    instruction="Use google_search to gather current, accurate information on the topic, then "
                "return organized findings with the sources you used.",
    tools=[google_search],
)
web_research_tool = AgentTool(agent=web_research_agent)

# --- AGENT DEFINITIONS ---

interactive_blogger_agent = Agent(
    name="interactive_blogger_agent",
    model=config.worker_model,
    description="The primary technical blogging assistant. It collaborates with the user to create a blog post.",
    instruction=f"""
    You are a technical blogging assistant. Your primary function is to help users create technical blog posts.

    Your workflow is as follows:
    1.  **Analyze Codebase (Optional):** If the user provides a directory, you will analyze the codebase to understand its structure and content. To do this, use the `analyze_codebase` tool.
    2.  **Plan:** You will generate a blog post outline and present it to the user. To do this, use the `robust_blog_planner` tool.
    3.  **Refine:** The user can provide feedback to refine the outline. You will continue to refine the outline until it is approved by the user.
    4.  **Visuals:** You will ask the user to choose their preferred method for including visual content. You have two options for including visual content in your blog post:

    1.  **Upload:** I will add placeholders in the blog post for you to upload your own images and videos.
    2.  **None:** I will not include any images or videos in the blog post.

    Please respond with "1" or "2" to indicate your choice.
    5.  **Write:** Once the user approves the outline, you will write the blog post. To do this, use the `robust_blog_writer` tool. Be then open for feedback.
    6.  **Edit:** After the first draft is written, you will present it to the user and ask for feedback. You will then revise the blog post based on the feedback. This process will be repeated until the user is satisfied with the result.
    7.  **Social Media:** After the user approves the blog post, you will ask if they want to generate social media posts to promote the article. If the user agrees to create a social media post, use the `social_media_writer` tool.
    8.  **Export:** When the user approves the final version, you will ask for a filename and save the blog post as a markdown file. If the user agrees, use the `save_blog_post_to_file` tool to save the blog post.

    Before planning, ALWAYS call `load_memory` to recall prior sessions and `load_note` (topic = the
    blog title or subject) to recall any prior draft, call the `web_research_agent` tool to research
    the topic on the live web, and use the Vertex AI Search tool to retrieve relevant technical
    reference material from the internal corpus. After the final version is approved, persist a short
    summary with `save_note` (topic = the blog title).

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    """,
    sub_agents=[
        robust_blog_writer,
        robust_blog_planner,
        blog_editor,
        social_media_writer,
    ],
    tools=[
        FunctionTool(save_blog_post_to_file),
        FunctionTool(analyze_codebase),
        load_note,
        save_note,
        load_memory,
        blog_rag,
        web_research_tool,
    ],
    output_key="blog_outline",
)


root_agent = interactive_blogger_agent

# Two-model split: coordinator -> gemini-3.5-flash, all sub-agents/tools -> gemini-3.1-flash-lite
# (both via the global Vertex endpoint). Lets Cloud Monitoring token_count split master vs sub.
import os as _os  # noqa: E402
if _os.environ.get("COST_TWO_MODEL") == "1":  # canonical default = single gemini-2.5-flash
    from ._gmodel import apply_split  # noqa: E402
    apply_split(root_agent)
