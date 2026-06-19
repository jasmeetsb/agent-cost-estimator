"""Two-model split helper (copied into each agent package as `_gmodel.py`).

Coordinator runs `gemini-3.5-flash`; all sub-agents / tool-call / auxiliary agents run
`gemini-3.1-flash-lite`. Both are GLOBAL-only models, so we pin each model's google.genai
Client to location="global" while the Agent Engine itself stays in us-central1. Cloud
Monitoring `token_count` (labeled by `model_user_id`) then cleanly separates MASTER vs
SUB-agent tokens. Image-generation models are NEVER switched (guarded).
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


def _model_id(m):
    if m is None:
        return ""
    if isinstance(m, str):
        return m
    return str(getattr(m, "model", "") or "")


def _is_image_model(m):
    mid = _model_id(m).lower()
    return "image" in mid or "imagen" in mid


def apply_split(root):
    """Set the root/coordinator agent to MASTER_MODEL and every descendant (sub_agents +
    AgentTool-wrapped agents, recursively) to SUB_MODEL. Image-generation models are left
    untouched. Returns root."""
    seen = set()

    def walk(agent, is_root):
        if agent is None or id(agent) in seen:
            return
        seen.add(id(agent))
        # Only LlmAgents carry a `model`; workflow agents (Loop/Sequential/Parallel) don't.
        if "model" in getattr(type(agent), "model_fields", {}):
            if not _is_image_model(agent.model):   # never switch image-gen models
                agent.model = master_model() if is_root else sub_model()
        for sa in (getattr(agent, "sub_agents", None) or []):
            walk(sa, False)
        for tool in (getattr(agent, "tools", None) or []):
            walk(getattr(tool, "agent", None), False)

    walk(root, True)
    return root


def apply_uniform(root, model="gemini-2.5-flash"):
    """Set every text LlmAgent in the tree to a single model (image-gen models untouched).
    Used for the canonical single-model deploy so heterogeneous sample sub-agents (e.g. plumber's
    2.0-flash / 2.5-pro specialists) are measured + priced on one basis. Returns root."""
    seen = set()

    def walk(a):
        if a is None or id(a) in seen:
            return
        seen.add(id(a))
        if "model" in getattr(type(a), "model_fields", {}) and not _is_image_model(a.model):
            a.model = model
        for sa in (getattr(a, "sub_agents", None) or []):
            walk(sa)
        for t in (getattr(a, "tools", None) or []):
            walk(getattr(t, "agent", None))

    walk(root)
    return root
