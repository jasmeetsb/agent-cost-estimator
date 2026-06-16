"""Firestore-backed persistent state tools for archetype agents.

Real reads/writes to Firestore (native mode, `agent_state` collection) so the
**Firestore SKU** is actually exercised and measurable. Each `save_note` = 1
document write, each `load_note` = 1 document read; the harness counts these
ops per interaction from the event stream (function_call names) and prices them.

This file is copied verbatim into each archetype agent package (deploy ships
only the agent's own package, so a shared sibling module wouldn't be included).
"""

import os
import re

from google.cloud import firestore

_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "jsb-genai-sa")
_CLIENT = None


def _db():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = firestore.Client(project=_PROJECT)
    return _CLIENT


def _doc_id(topic: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", (topic or "default").strip().lower())
    return s[:128] or "default"


def save_note(topic: str, content: str) -> dict:
    """Persist a note/fact to durable storage under a topic, for later recall.

    Args:
        topic: short key to file the note under (e.g. a user name, order id, subject).
        content: the text to remember.
    """
    _db().collection("agent_state").document(_doc_id(topic)).set(
        {"topic": topic, "content": content}, merge=True)
    return {"status": "ok", "saved_topic": topic}


def load_note(topic: str) -> dict:
    """Load a previously saved note/fact by topic from durable storage.

    Args:
        topic: the key the note was filed under.
    """
    snap = _db().collection("agent_state").document(_doc_id(topic)).get()
    return {"status": "ok", "found": snap.exists, "data": snap.to_dict() or {}}
