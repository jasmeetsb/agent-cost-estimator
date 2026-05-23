"""A minimal ADK agent: answers weather/time questions via two tools.

Deliberately simple and deterministic so cost-per-query is dominated by the
Gemini model call (token usage), which is what the harness measures.
"""

from google.adk.agents import Agent

MODEL = "gemini-2.5-flash"

_WEATHER = {
    "new york": "sunny, 22°C (72°F)",
    "london": "overcast, 14°C (57°F)",
    "tokyo": "light rain, 18°C (64°F)",
    "san francisco": "foggy, 16°C (61°F)",
}

_TZ = {
    "new york": "America/New_York (UTC-5)",
    "london": "Europe/London (UTC+0)",
    "tokyo": "Asia/Tokyo (UTC+9)",
    "san francisco": "America/Los_Angeles (UTC-8)",
}


def get_weather(city: str) -> dict:
    """Return the current weather for a city.

    Args:
        city: Name of the city, e.g. "New York".
    """
    key = city.strip().lower()
    if key in _WEATHER:
        return {"status": "ok", "city": city, "report": _WEATHER[key]}
    return {"status": "error", "message": f"No weather data for '{city}'."}


def get_timezone(city: str) -> dict:
    """Return the timezone for a city.

    Args:
        city: Name of the city, e.g. "Tokyo".
    """
    key = city.strip().lower()
    if key in _TZ:
        return {"status": "ok", "city": city, "timezone": _TZ[key]}
    return {"status": "error", "message": f"No timezone data for '{city}'."}


root_agent = Agent(
    name="weather_agent",
    model=MODEL,
    description="Answers weather and timezone questions for major cities.",
    instruction=(
        "You are a concise weather assistant. Use get_weather for weather "
        "questions and get_timezone for timezone questions. Answer in one "
        "short sentence. If a tool returns an error, say you don't have data "
        "for that city."
    ),
    tools=[get_weather, get_timezone],
)
