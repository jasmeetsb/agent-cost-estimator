"""Firestore-backed persistent state tools for archetype agents.

Real reads/writes to Firestore (native mode) so the **Firestore SKU** is actually
exercised and measurable. Each `save_note` = 1 document write, each `load_note` =
1 document read; the harness counts these ops per interaction from the event
stream (function_call names) and prices them.

SECURITY: notes are namespaced by the **authenticated principal** the ADK runtime
supplies (`tool_context.user_id`) — NOT by the LLM-chosen `topic`. This prevents
one caller from reading/writing another caller's state via a chosen topic (IDOR)
and prevents prompt-injected cross-namespace writes. The topic is hashed for the
document id (collision-safe) and stored as a field for readability.

This file is copied verbatim into each archetype agent package (deploy ships only
the agent's own package, so a shared sibling module wouldn't be included).
"""

import hashlib
import os

from google.cloud import firestore
from google.adk.tools import ToolContext

# Use the project ID, NOT GOOGLE_CLOUD_PROJECT — Agent Engine sets that env var to
# the project NUMBER, and Firestore's database lookup rejects the number with a
# 404 "database does not exist" (it requires the project ID). Verified: id→OK,
# number→404. Multi-region (nam5) named DB targeted explicitly.
_PROJECT = os.environ.get("FIRESTORE_PROJECT_ID", "jsb-genai-sa")
_DATABASE = os.environ.get("FIRESTORE_DATABASE", "agentstate")
_CLIENT = None


def _db():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = firestore.Client(project=_PROJECT, database=_DATABASE)
    return _CLIENT


def _principal(tool_context) -> str:
    """Authenticated principal from the runtime (not the LLM). Reject if absent."""
    uid = getattr(tool_context, "user_id", None) if tool_context is not None else None
    if not uid:
        return ""
    return "".join(c for c in str(uid) if c.isalnum() or c in "-_")[:128]


def _doc_id(topic: str) -> str:
    return hashlib.sha256((topic or "default").strip().lower().encode()).hexdigest()[:40]


def _notes(uid: str):
    return _db().collection("agent_state").document(uid).collection("notes")


def save_note(topic: str, content: str, tool_context: ToolContext) -> dict:
    """Persist a note/fact to durable storage under a topic, for later recall.

    Notes are private to the current user; the topic is just a label.

    Args:
        topic: short label for the note (e.g. a subject, order id).
        content: the text to remember.
    """
    uid = _principal(tool_context)
    if not uid:
        return {"status": "error", "message": "no authenticated principal"}
    _notes(uid).document(_doc_id(topic)).set({"topic": topic, "content": content}, merge=True)
    return {"status": "ok", "saved_topic": topic}


def load_note(topic: str, tool_context: ToolContext) -> dict:
    """Load a previously saved note/fact by topic from durable storage.

    Only the current user's own notes are accessible.

    Args:
        topic: the label the note was filed under.
    """
    uid = _principal(tool_context)
    if not uid:
        return {"status": "error", "message": "no authenticated principal"}
    snap = _notes(uid).document(_doc_id(topic)).get()
    return {"status": "ok", "found": snap.exists, "data": snap.to_dict() or {}}
