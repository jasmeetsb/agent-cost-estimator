import datetime
import uuid
from zoneinfo import ZoneInfo

from google.adk.agents import LoopAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext

from .checker_agent import checker_agent_instance
from .sub_agents.image import image_generation_agent
from .sub_agents.prompt import image_gen_prompt_generation_agent
from .sub_agents.scoring import scoring_agent


def set_session(callback_context: CallbackContext):
    """
    Sets a unique ID and timestamp in the callback context's state.
    This function is called before the main_loop_agent executes.
    """

    callback_context.state["unique_id"] = str(uuid.uuid4())
    callback_context.state["timestamp"] = datetime.datetime.now(
        ZoneInfo("UTC")
    ).isoformat()


# This agent is responsible for generating and scoring images based on input text.
# It uses a sequential process to:
# 1. Create an image generation prompt from the input text
# 2. Generate images using the prompt
# 3. Score the generated images
# The process continues until either:
# - The image score meets the quality threshold
# - The maximum number of iterations is reached

image_generation_and_scoring_agent = SequentialAgent(
    name="image_generation_and_scoring_agent",
    description=(
        """
        Analyzes a input text, creates an image generation prompt, generates the relevant images and scores the images.
        1. Invoke the image_gen_prompt_generation_agent agent to generate the prompt for generating images
        2. Invoke the image_generation_agent agent to generate the images
        3. Invoke the scoring_agent agent to score the images
        """
    ),
    sub_agents=[
        image_gen_prompt_generation_agent,
        image_generation_agent,
        scoring_agent,
    ],
)


# --- 5. Define the Loop Agent ---
# The LoopAgent will repeatedly execute its sub_agents in the order they are listed.
# It will continue looping until one of its sub_agents (specifically, the checker_agent's tool)
# sets tool_context.actions.escalate = True.
on_brand_genmedia = LoopAgent(
    name="on_brand_genmedia",
    description="Repeatedly runs a sequential process and checks a termination condition.",
    sub_agents=[
        image_generation_and_scoring_agent,  # First, run your sequential process [1]
        checker_agent_instance,  # Second, check the condition and potentially stop the loop [1]
    ],
    before_agent_callback=set_session,
)

# --- Coordinator wrapper: adds conversational SKUs (Memory Bank recall, Firestore notes, RAG
# brand guidelines) around the image-generation loop, which it invokes as an AgentTool. The loop
# (and its image model, used inside the generate_images tool) is unchanged. ---
from google.adk.agents import Agent  # noqa: E402
from google.adk.tools import load_memory, VertexAiSearchTool  # noqa: E402
from google.adk.tools.agent_tool import AgentTool  # noqa: E402

from .config import GENAI_MODEL  # noqa: E402
from .fs_state import save_note, load_note  # noqa: E402

_DATA_STORE = ("projects/jsb-genai-sa/locations/global/collections/"
               "default_collection/dataStores/agent-knowledge")
brand_rag = VertexAiSearchTool(data_store_id=_DATA_STORE, bypass_multi_tools_limit=True)
image_loop_tool = AgentTool(agent=on_brand_genmedia)

on_brand_coordinator = Agent(
    name="on_brand_coordinator",
    model=GENAI_MODEL,
    description="Brand-media coordinator: recalls brand prefs, retrieves brand guidelines, and "
                "runs the on-brand image-generation loop.",
    instruction=(
        "You create brand-compliant images. At the START, ALWAYS call load_memory to recall the "
        "user's brand preferences and load_note (topic = the brand or campaign) for prior assets; "
        "consult the brand-guideline corpus via the Vertex AI Search RAG tool. Then call the "
        "on_brand_genmedia tool (the image-generation loop) to generate the on-brand image for the "
        "user's request. After it returns, persist a short summary of the generated asset with "
        "save_note (topic = the brand or campaign), and report the result concisely."
    ),
    tools=[load_memory, save_note, load_note, brand_rag, image_loop_tool],
)

root_agent = on_brand_coordinator

# Two-model split when COST_TWO_MODEL=1; default deploy = single gemini-2.5-flash. The image
# model lives inside the generate_images tool (not an agent.model), so it is never switched.
import os as _os  # noqa: E402
from ._gmodel import apply_split, apply_uniform  # noqa: E402
if _os.environ.get("COST_TWO_MODEL") == "1":
    apply_split(root_agent)
else:
    apply_uniform(root_agent, "gemini-2.5-flash")
