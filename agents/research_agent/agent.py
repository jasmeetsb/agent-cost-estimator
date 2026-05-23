"""A 'slightly more complex' ADK agent for EXP-002.

A coordinator that delegates to two specialist sub-agents:
  - calc_agent: arithmetic/statistics tools
  - facts_agent: a small knowledge-lookup tool

Multi-agent delegation means a single user query fans out into several model
calls (coordinator routing + specialist reasoning + tool synthesis), giving a
materially higher and different cost profile than the single-agent weather demo.
"""

from google.adk.agents import Agent

MODEL = "gemini-2.5-flash"


# ---- calc tools ----
def add(a: float, b: float) -> dict:
    """Add two numbers."""
    return {"result": a + b}


def multiply(a: float, b: float) -> dict:
    """Multiply two numbers."""
    return {"result": a * b}


def mean(numbers: list[float]) -> dict:
    """Return the arithmetic mean of a list of numbers."""
    if not numbers:
        return {"status": "error", "message": "empty list"}
    return {"result": sum(numbers) / len(numbers)}


# ---- facts tool ----
_FACTS = {
    "speed of light": "299,792,458 m/s",
    "earth radius": "6,371 km (mean)",
    "avogadro number": "6.02214076e23 /mol",
    "pi": "3.14159265358979",
}


def lookup_fact(topic: str) -> dict:
    """Look up a scientific constant or fact by topic."""
    key = topic.strip().lower()
    for k, v in _FACTS.items():
        if k in key or key in k:
            return {"status": "ok", "topic": k, "value": v}
    return {"status": "error", "message": f"No fact for '{topic}'."}


calc_agent = Agent(
    name="calc_agent",
    model=MODEL,
    description="Performs arithmetic and simple statistics using tools.",
    instruction=(
        "You handle math. Use add, multiply, and mean tools to compute exact "
        "answers. Show the final number clearly."
    ),
    tools=[add, multiply, mean],
)

facts_agent = Agent(
    name="facts_agent",
    model=MODEL,
    description="Looks up scientific constants and facts.",
    instruction=(
        "You answer factual lookups. Use lookup_fact for any constant or fact. "
        "If no data, say so."
    ),
    tools=[lookup_fact],
)

root_agent = Agent(
    name="research_coordinator",
    model=MODEL,
    description="Coordinates math and fact-lookup specialists to answer questions.",
    instruction=(
        "You are a coordinator. Delegate math/statistics questions to "
        "calc_agent and factual/constant lookups to facts_agent. For multi-part "
        "questions, use both, then combine their results into one concise answer."
    ),
    sub_agents=[calc_agent, facts_agent],
)
