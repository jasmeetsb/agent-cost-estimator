"""Extract full conversation content from ADK events for persistence.

The cost path only needs token counts, but for reproducibility, debugging, and
content-based analysis (e.g. LLM-as-judge) we also persist the actual inputs,
outputs, tool calls/responses, and per-step usage. `build_turn` turns one query's
events into a structured, JSON-serializable record; `write_transcript` appends
records to a JSONL file (one line per turn).
"""

from __future__ import annotations

import json
from pathlib import Path


def _parts(event: dict) -> list:
    return ((event.get("content") or {}).get("parts")) or []


def build_turn(message: str, events: list, *, author: str = "user",
               session_id: str | None = None) -> dict:
    """Structure one query (input + all resulting events) into a transcript record.

    Captures: the user input, each model text chunk, every function_call (tool +
    args) and function_response (tool result), the agent/author per step, and the
    per-step usage_metadata. `output_text` is the concatenation of model text.
    """
    steps = []
    output_chunks = []
    tot = {"prompt": 0, "output": 0, "thoughts": 0, "cached": 0, "calls": 0}

    for ev in events:
        ev = ev if isinstance(ev, dict) else {}
        ev_author = ev.get("author")
        um = ev.get("usage_metadata") or {}
        if um:
            tot["prompt"] += int(um.get("prompt_token_count") or 0)
            tot["output"] += int(um.get("candidates_token_count") or 0) + int(um.get("thoughts_token_count") or 0)
            tot["thoughts"] += int(um.get("thoughts_token_count") or 0)
            tot["cached"] += int(um.get("cached_content_token_count") or 0)
            tot["calls"] += 1
        for p in _parts(ev):
            if p.get("text"):
                steps.append({"type": "model_text", "author": ev_author, "text": p["text"]})
                output_chunks.append(p["text"])
            elif p.get("function_call"):
                fc = p["function_call"]
                steps.append({"type": "tool_call", "author": ev_author,
                              "tool": fc.get("name"), "args": fc.get("args")})
            elif p.get("function_response"):
                fr = p["function_response"]
                steps.append({"type": "tool_response", "tool": fr.get("name"),
                              "response": fr.get("response")})

    return {
        "session_id": session_id,
        "input": message,
        "output_text": "\n".join(output_chunks).strip(),
        "steps": steps,
        "usage": tot,
    }


def write_transcript(path: str | Path, records: list[dict], append: bool = False) -> None:
    """Write transcript records as JSONL (one JSON object per line).

    append=True adds to an existing transcript (accumulate batches) instead of
    overwriting."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with path.open(mode) as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
