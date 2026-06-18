"""Conversational Chatbot archetype — Moderate complexity.

Single user-facing support agent. Light tool use (FAQ + KB lookup), Memory Bank
for returning-user personalization. Matches the calculator's Conversational
Chatbot / Moderate column: ~3 turns/query, 20% turns with tools, cheap model.

Intended model tier: Gemini 3.1 Flash-Lite (volume-driven). Deployed on
gemini-2.5-flash for measurement parity with prior experiments.
"""

from google.adk.agents import Agent
from google.adk.tools import load_memory, VertexAiSearchTool

from .fs_state import save_note, load_note

MODEL = "gemini-2.5-flash"

# Customer-safe knowledge corpus (Vertex AI Search / RAG). The chatbot is
# customer-facing, so it uses a datastore with ONLY support/product docs — NOT
# the internal ops/policy/research corpus that researcher/orchestrator use
# (avoids cross-trust-boundary exposure of internal docs to end users).
_DATA_STORE = ("projects/jsb-genai-sa/locations/global/collections/"
               "default_collection/dataStores/agent-knowledge-public")
kb_rag = VertexAiSearchTool(data_store_id=_DATA_STORE, bypass_multi_tools_limit=True)

# Canned support knowledge — stands in for a BigQuery/KB lookup (the real SKU
# would be BigQuery; mocked here so the agent is deployable without a dataset).
_FAQ = {
    "reset password": "Go to Settings → Security → Reset Password; you'll get an email link.",
    "business hours": "Support is available 9am–6pm local time, Monday–Friday.",
    "refund": "Refunds are processed within 5–7 business days to the original payment method.",
    "shipping": "Standard shipping takes 3–5 business days; express is 1–2.",
    "cancel": "You can cancel any time from Account → Subscriptions → Cancel.",
}

_KB = {
    "integration": "We support REST and webhook integrations; see docs.example.com/integrations.",
    "pricing tiers": "Starter ($0), Pro ($29/mo), Enterprise (contact sales).",
    "data export": "Export your data as CSV or JSON from Account → Data → Export.",
    "sso": "SSO (SAML/OIDC) is available on Enterprise; contact your account manager.",
}


def faq_lookup(topic: str) -> dict:
    """Look up an answer to a common support question by topic."""
    key = topic.strip().lower()
    for k, v in _FAQ.items():
        if k in key or key in k:
            return {"status": "ok", "topic": k, "answer": v}
    return {"status": "not_found", "message": f"No FAQ entry for '{topic}'."}


def kb_search(query: str) -> dict:
    """Search the product knowledge base for a topic."""
    key = query.strip().lower()
    hits = [{"topic": k, "answer": v} for k, v in _KB.items() if any(w in k for w in key.split())]
    if hits:
        return {"status": "ok", "results": hits[:3]}
    return {"status": "not_found", "message": f"No KB articles for '{query}'."}


root_agent = Agent(
    name="conversational_chatbot",
    model=MODEL,
    description="Customer-support chatbot that answers questions using FAQ + KB lookup, with memory of the user.",
    instruction=(
        "You are a friendly customer-support assistant. Answer concisely. "
        "Use faq_lookup for common questions (passwords, refunds, shipping, hours, cancellation) "
        "For product/technical/policy questions, use the Vertex AI Search RAG tool to retrieve "
        "grounded answers from the knowledge base (kb_search is a fallback). "
        "When the user shares a preference or detail about themselves, persist it with save_note "
        "(topic = their name or 'user'); at the start of a conversation, ALWAYS call load_memory "
        "to recall prior memories about this user (and load_note for stored notes), then personalize "
        "your answers. If a lookup returns nothing, answer from general knowledge and offer to escalate."
    ),
    tools=[faq_lookup, kb_search, load_memory, save_note, load_note, kb_rag],
)

# Two-model split: coordinator -> gemini-3.5-flash, all sub-agents/tools -> gemini-3.1-flash-lite
# (both via the global Vertex endpoint). Lets Cloud Monitoring token_count split master vs sub.
import os as _os  # noqa: E402
if _os.environ.get("COST_TWO_MODEL") == "1":  # canonical default = single gemini-2.5-flash
    from ._gmodel import apply_split  # noqa: E402
    apply_split(root_agent)
