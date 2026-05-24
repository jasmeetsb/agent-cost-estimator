"""EXP-004 agent: sub-agents + Agent Engine Memory Bank.

A personal assistant that (a) delegates to specialist sub-agents and (b) uses
the `preload_memory` tool so prior-session facts are recalled. When deployed to
Agent Engine (ADK >= 1.5.0), AdkApp auto-wires VertexAiMemoryBankService to the
engine's own Memory Bank, so cross-session recall + memory generation exercise
the `reasoning_engine/memory_bank/*` SKUs in addition to tokens and runtime.
"""

from google.adk.agents import Agent
from google.adk.tools import preload_memory

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
        "Recalled facts about the user appear in context — use them to "
        "personalize answers without re-asking. Delegate preference/unit "
        "questions to prefs_agent and list/note formatting to notes_agent. "
        "Keep answers concise."
    ),
    tools=[preload_memory],
    sub_agents=[prefs_agent, notes_agent],
)
