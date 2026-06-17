"""Two-model split helper (copied verbatim into each agent package as `_gmodel.py`).

Coordinator runs `gemini-3.5-flash`; all sub-agents / tool-call / auxiliary agents run
`gemini-3.1-flash-lite`. Both are GLOBAL-only models, so we pin each model's google.genai
Client to location="global" (ADK's documented override) while the Agent Engine itself stays
in us-central1. Cloud Monitoring `token_count` (labeled by `model_user_id`) then cleanly
separates MASTER vs SUB-agent tokens — and captures sub-agent tokens that the deployed
`stream_query` misses for AgentTool-encapsulated sub-agents.
"""
from functools import cached_property

from google.adk.models import Gemini
from google.genai import Client

MASTER_MODEL = "gemini-3.5-flash"        # coordinator / master agent
SUB_MODEL = "gemini-3.1-flash-lite"      # sub-agents, tool-call agents, auxiliary


class GlobalGemini(Gemini):
    @cached_property
    def api_client(self) -> Client:
        return Client(vertexai=True, location="global")


def master_model():
    return GlobalGemini(model=MASTER_MODEL)


def sub_model():
    return GlobalGemini(model=SUB_MODEL)


def apply_split(root):
    """Set the root/coordinator agent to MASTER_MODEL and every descendant (sub_agents +
    AgentTool-wrapped agents, recursively) to SUB_MODEL. Called once after the root agent is
    built, so the deployed (cloudpickled) tree carries the two-model split. Returns root."""
    seen = set()

    def walk(agent, is_root):
        if agent is None or id(agent) in seen:
            return
        seen.add(id(agent))
        # Only LlmAgents carry a `model`; workflow agents (Loop/Sequential/Parallel) don't —
        # skip setting on those, but still recurse into their children.
        if "model" in getattr(type(agent), "model_fields", {}):
            agent.model = master_model() if is_root else sub_model()
        for sa in (getattr(agent, "sub_agents", None) or []):
            walk(sa, False)
        for tool in (getattr(agent, "tools", None) or []):
            walk(getattr(tool, "agent", None), False)

    walk(root, True)
    return root
