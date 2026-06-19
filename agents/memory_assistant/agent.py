"""EXP-004 agent: sub-agents + Agent Engine Memory Bank.

A personal assistant that (a) delegates to specialist sub-agents and (b) uses
the `preload_memory` tool so prior-session facts are recalled. When deployed to
Agent Engine (ADK >= 1.5.0), AdkApp auto-wires VertexAiMemoryBankService to the
engine's own Memory Bank, so cross-session recall + memory generation exercise
the `reasoning_engine/memory_bank/*` SKUs in addition to tokens and runtime.
"""

from google.adk.agents import Agent
from google.adk.tools import load_memory

from .fs_state import save_note, load_note

MODEL = "gemini-2.5-flash"


# ---- preferences specialist ----
def set_unit_preference(system: str) -> dict:
    """Record the user's preferred measurement system ('metric' or 'imperial')."""
    s = system.strip().lower()
    if s not in ("metric", "imperial"):
        return {"status": "error", "message": "system must be metric or imperial"}
    return {"status": "ok", "unit_system": s}


def convert_temp(celsius: float, to_imperial: bool) -> dict:
    """Convert a Celsius temperature to Fahrenheit if to_imperial is true."""
    if to_imperial:
        return {"value": celsius * 9 / 5 + 32, "unit": "F"}
    return {"value": celsius, "unit": "C"}


# ---- notes specialist ----
def make_checklist(items: list[str]) -> dict:
    """Format a list of items into a numbered checklist."""
    if not items:
        return {"status": "error", "message": "no items"}
    return {"checklist": [f"{i+1}. {it}" for i, it in enumerate(items)]}


prefs_agent = Agent(
    name="prefs_agent",
    model=MODEL,
    description="Handles unit-system preferences and temperature conversions.",
    instruction=(
        "You manage the user's measurement preferences. Use set_unit_preference "
        "to record their choice and convert_temp for conversions."
    ),
    tools=[set_unit_preference, convert_temp],
)

notes_agent = Agent(
    name="notes_agent",
    model=MODEL,
    description="Turns things the user wants to remember into checklists.",
    instruction="You help organize notes. Use make_checklist to format lists.",
    tools=[make_checklist],
)

root_agent = Agent(
    name="personal_assistant",
    model=MODEL,
    description="A personal assistant that remembers the user across sessions.",
    instruction=(
        "You are a personal assistant with long-term memory of the user. "
        "At the START of every conversation, ALWAYS call load_memory to recall prior "
        "memories about this user (and load_note, topic = their name or 'user', for stored "
        "notes), then personalize answers without re-asking. When the user shares a preference "
        "or detail about themselves, persist it with save_note (topic = their name or 'user'). "
        "Delegate preference/unit questions to prefs_agent and list/note formatting to "
        "notes_agent. Keep answers concise."
    ),
    tools=[load_memory, save_note, load_note],
    sub_agents=[prefs_agent, notes_agent],
)

# Two-model split: coordinator -> gemini-3.5-flash, all sub-agents/tools -> gemini-3.1-flash-lite
# (global Vertex endpoint) when COST_TWO_MODEL=1; default deploy = single gemini-2.5-flash.
import os as _os  # noqa: E402
from ._gmodel import apply_split, apply_uniform  # noqa: E402
if _os.environ.get("COST_TWO_MODEL") == "1":
    apply_split(root_agent)
else:
    apply_uniform(root_agent, "gemini-2.5-flash")
